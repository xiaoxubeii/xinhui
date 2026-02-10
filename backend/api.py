# -*- coding: utf-8 -*-
"""
CPET 临床辅助系统 API v2

提供实时 AT 预测、VO2 Peak 预测、运动处方生成等功能。
"""

from __future__ import annotations

from datetime import datetime
import json
import os
import re
from urllib.parse import urlparse
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from pathlib import Path
from typing import List, Optional, Dict, Any

import httpx

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import settings
from .app_db import init_app_db
from .auth.api import router as auth_router
from .auth.security import get_current_user_from_request
from .artifacts.api import router as artifacts_router
from .api_keys.api import router as api_keys_router
from .chat.api import router as chat_router
from .chat.opencode import create_session as opencode_create_session
from .chat.opencode import send_message as opencode_send_message
from .plans.api import router as plans_router
from .realtime.websocket import realtime_manager, websocket_endpoint, SessionConfig
from .inference.at_predictor import CPETDataPoint
from .inference.vo2_predictor import VO2PeakPredictor, WeberClass
from .prescription.generator import PrescriptionGenerator
from .prescription.risk_stratification import (
    RiskStratifier, RiskLevel,
    ExerciseTestResults, NonExerciseTestResults, PatientInfo
)
from .prescription.aerobic import CPETResults
from .reports.pdf_generator import PDFReportGenerator, CPETReport, CPETTestResults

# 创建应用
app = FastAPI(
    title="CPET 临床辅助系统",
    description="实时 AT 预测、VO2 Peak 预测、运动处方生成",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup_init_db() -> None:
    # Auth/chat/artifacts DB
    init_app_db(settings.app_db_path)


# Ensure the app DB exists even when lifespan events are not triggered (e.g. some test clients).
init_app_db(settings.app_db_path)


_AUTH_EXEMPT_PREFIXES = (
    "/api/auth/login",
    "/api/auth/register",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
    "/api/mcp",
)


@app.middleware("http")
async def _auth_gate(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api") and path != "/api/health" and not any(path.startswith(p) for p in _AUTH_EXEMPT_PREFIXES):
        try:
            user = get_current_user_from_request(request)
            request.state.user = user
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


# Auth / Artifacts / Chat
app.include_router(auth_router)
app.include_router(api_keys_router)
app.include_router(artifacts_router)
app.include_router(chat_router)
app.include_router(plans_router)

# 注册 RAG API 路由
try:
    from .rag.api import router as rag_router
    app.include_router(rag_router)
except ImportError:
    pass  # RAG module not available

# 注册 MCP Server 路由
try:
    from .tools.mcp_server import router as mcp_router
    app.include_router(mcp_router)
except ImportError:
    pass  # MCP module not available

# 注册 HealthKit 数据同步路由
try:
    from .healthkit.api import router as healthkit_router
    app.include_router(healthkit_router)
except ImportError:
    pass  # HealthKit module not available

# 注册 Diet 识别与饮食记录路由
try:
    from .diet.api import router as diet_router
    app.include_router(diet_router)
except ImportError:
    pass  # Diet module not available

# 注册 Clinical 临床记录路由
try:
    from .clinical.api import router as clinical_router
    app.include_router(clinical_router)
except ImportError:
    pass  # Clinical module not available

# 注册 Lifestyle 生活数据聚合路由
try:
    from .lifestyle.api import router as lifestyle_router
    app.include_router(lifestyle_router)
except ImportError:
    pass  # Lifestyle module not available

# 注册 Health 健康域路由
try:
    from .health.api import router as health_router
    app.include_router(health_router)
except ImportError:
    pass  # Health module not available

# 注册 Exercise 运动域路由
try:
    from .exercise.api import router as exercise_router
    app.include_router(exercise_router)
except ImportError:
    pass  # Exercise module not available

# 注册 Nutrition 饮食域路由（对齐数据域命名）
try:
    from .nutrition.api import router as nutrition_router
    app.include_router(nutrition_router)
except ImportError:
    pass  # Nutrition module not available

# 初始化服务
at_predictor = realtime_manager.at_predictor
vo2_predictor = VO2PeakPredictor()
prescription_generator = PrescriptionGenerator()
pdf_generator = None  # 延迟初始化

# ==================== 数据模型 ====================

class PatientInfoRequest(BaseModel):
    name: str
    patient_id: str
    age: int
    sex: str = Field(..., pattern="^(male|female)$")
    height_cm: float
    weight_kg: float
    diagnosis: List[str] = []
    has_hypertension: bool = False
    has_diabetes: bool = False
    has_pacemaker: bool = False
    has_orthopedic_issues: bool = False


class CPETDataRequest(BaseModel):
    timestamp: float
    vo2: float
    vco2: float
    ve: float
    hr: float
    rr: float = 0
    rer: float = 0
    work_rate: float = 0
    spo2: Optional[float] = None
    sbp: Optional[float] = None
    dbp: Optional[float] = None
    vt: Optional[float] = None
    peto2: Optional[float] = None
    petco2: Optional[float] = None
    ve_vo2: Optional[float] = None
    ve_vco2: Optional[float] = None
    vo2_hr: Optional[float] = None
    bf: Optional[float] = None


class CPETResultsRequest(BaseModel):
    vo2_peak: float
    hr_max: float
    hr_rest: float
    max_workload: float
    max_mets: float
    vt1_vo2: Optional[float] = None
    vt1_hr: Optional[float] = None
    vt1_workload: Optional[float] = None
    vt2_vo2: Optional[float] = None
    vt2_hr: Optional[float] = None
    vt2_workload: Optional[float] = None
    ischemia_hr: Optional[float] = None
    arrhythmia_hr: Optional[float] = None


class ExerciseTestRequest(BaseModel):
    max_mets: Optional[float] = None
    has_complex_arrhythmia: bool = False
    has_angina: bool = False
    has_dyspnea: bool = False
    has_dizziness: bool = False
    symptom_onset_mets: Optional[float] = None
    st_depression_mm: float = 0.0
    has_abnormal_hr_response: bool = False
    has_abnormal_bp_response: bool = False


class NonExerciseTestRequest(BaseModel):
    lvef: Optional[float] = None
    has_cardiac_arrest_history: bool = False
    has_chf: bool = False
    has_ischemia_symptoms: bool = False
    has_resting_arrhythmia: bool = False
    has_clinical_depression: bool = False


class PrescriptionRequest(BaseModel):
    patient: PatientInfoRequest
    cpet_results: CPETResultsRequest
    exercise_test: ExerciseTestRequest
    non_exercise_test: NonExerciseTestRequest
    has_cardiac_surgery: bool = False
    surgery_weeks_ago: Optional[int] = None
    has_balance_issues: bool = False
    has_fall_history: bool = False
    physician_name: Optional[str] = None


def _build_prescription_inputs(request: PrescriptionRequest):
    patient = PatientInfo(
        age=request.patient.age,
        sex=request.patient.sex,
        height_cm=request.patient.height_cm,
        weight_kg=request.patient.weight_kg,
        diagnosis=request.patient.diagnosis,
        has_hypertension=request.patient.has_hypertension,
        has_diabetes=request.patient.has_diabetes,
        has_pacemaker=request.patient.has_pacemaker,
        has_orthopedic_issues=request.patient.has_orthopedic_issues,
    )

    cpet = CPETResults(
        vo2_peak=request.cpet_results.vo2_peak,
        hr_max=request.cpet_results.hr_max,
        hr_rest=request.cpet_results.hr_rest,
        max_workload=request.cpet_results.max_workload,
        max_mets=request.cpet_results.max_mets,
        vt1_vo2=request.cpet_results.vt1_vo2,
        vt1_hr=request.cpet_results.vt1_hr,
        vt1_workload=request.cpet_results.vt1_workload,
        vt2_vo2=request.cpet_results.vt2_vo2,
        vt2_hr=request.cpet_results.vt2_hr,
        vt2_workload=request.cpet_results.vt2_workload,
        ischemia_hr=request.cpet_results.ischemia_hr,
        arrhythmia_hr=request.cpet_results.arrhythmia_hr,
    )

    ex_results = ExerciseTestResults(
        max_mets=request.exercise_test.max_mets,
        has_complex_arrhythmia=request.exercise_test.has_complex_arrhythmia,
        has_angina=request.exercise_test.has_angina,
        has_dyspnea=request.exercise_test.has_dyspnea,
        has_dizziness=request.exercise_test.has_dizziness,
        symptom_onset_mets=request.exercise_test.symptom_onset_mets,
        st_depression_mm=request.exercise_test.st_depression_mm,
        has_abnormal_hr_response=request.exercise_test.has_abnormal_hr_response,
        has_abnormal_bp_response=request.exercise_test.has_abnormal_bp_response,
    )

    non_ex_results = NonExerciseTestResults(
        lvef=request.non_exercise_test.lvef,
        has_cardiac_arrest_history=request.non_exercise_test.has_cardiac_arrest_history,
        has_chf=request.non_exercise_test.has_chf,
        has_ischemia_symptoms=request.non_exercise_test.has_ischemia_symptoms,
        has_resting_arrhythmia=request.non_exercise_test.has_resting_arrhythmia,
        has_clinical_depression=request.non_exercise_test.has_clinical_depression,
    )

    return patient, cpet, ex_results, non_ex_results


class VO2PredictionRequest(BaseModel):
    vo2_at: float
    hr_at: float
    work_rate_at: float
    age: int
    sex: str
    weight_kg: float
    height_cm: float


class SessionCreateRequest(BaseModel):
    patient_id: Optional[str] = None
    threshold: float = 0.7
    persistence: int = 3
    mode: str = Field("sim", pattern="^(sim|device)$")
    sim_speed: Optional[float] = None
    sim_smooth: Optional[str] = None
    sim_start: Optional[float] = None
    sim_end: Optional[float] = None


class InferSequenceRequest(BaseModel):
    data_points: List[CPETDataRequest]
    static_features: Optional[Dict[str, Any]] = None


class InferExamRequest(BaseModel):
    exam_id: str
    smooth: str = "none"


class AgentMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class AgentAskRequest(BaseModel):
    question: str
    page: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    history: List[AgentMessage] = Field(default_factory=list)


class AgentAskResponse(BaseModel):
    answer: str
    model: str
    start: Optional[float] = None
    end: Optional[float] = None


# ==================== API 端点 ====================

@app.get("/api/health")
def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
    }


# ---------- 实时预测 ----------

@app.websocket("/api/ws/realtime/{session_id}")
async def realtime_websocket(websocket: WebSocket, session_id: str):
    """实时预测 WebSocket 端点"""
    await websocket_endpoint(websocket, session_id)


@app.post("/api/sessions")
async def create_session(request: SessionCreateRequest):
    """创建实时预测会话"""
    from uuid import uuid4
    session_id = str(uuid4())

    config = SessionConfig(
        session_id=session_id,
        patient_id=request.patient_id,
        threshold=request.threshold,
        persistence=request.persistence,
        mode=request.mode,
        sim_speed=request.sim_speed or settings.sim_default_speed,
        sim_smooth=request.sim_smooth or settings.sim_default_smooth,
        sim_start=request.sim_start,
        sim_end=request.sim_end,
    )
    realtime_manager.register_session(config)

    # 创建会话（实际连接在 WebSocket 时建立）
    return {
        "session_id": session_id,
        "websocket_url": f"/api/ws/realtime/{session_id}",
        "threshold": request.threshold,
        "persistence": request.persistence,
        "mode": request.mode,
    }


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    """获取会话状态"""
    summary = realtime_manager.get_session_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found")
    return summary


@app.post("/api/predict/at")
def predict_at_batch(data_points: List[CPETDataRequest]):
    """批量 AT 预测"""
    if not data_points:
        raise HTTPException(status_code=400, detail="No data points provided")
    
    points = [
        CPETDataPoint(
            timestamp=p.timestamp,
            vo2=p.vo2,
            vco2=p.vco2,
            ve=p.ve,
            hr=p.hr,
            rr=p.rr,
            rer=p.rer,
            work_rate=p.work_rate,
            spo2=p.spo2,
            sbp=p.sbp,
            dbp=p.dbp,
            extras={
                "vt": p.vt,
                "peto2": p.peto2,
                "petco2": p.petco2,
                "ve_vo2": p.ve_vo2,
                "ve_vco2": p.ve_vco2,
                "vo2_hr": p.vo2_hr,
                "bf": p.bf,
            },
        )
        for p in data_points
    ]
    
    outputs = at_predictor.predict_outputs(points)
    probs = outputs.get("probs", [])
    
    return {
        "probabilities": probs,
        "timestamps": [p.timestamp for p in data_points],
        "count": len(probs),
        "predicted_at_time": outputs.get("time_pred"),
        "vo2_peak_prediction": outputs.get("vo2_pred"),
    }


@app.post("/api/infer/sequence")
def infer_sequence(request: InferSequenceRequest):
    """按序列推理 PaceFormer 输出"""
    if not request.data_points:
        raise HTTPException(status_code=400, detail="No data points provided")

    points = [
        CPETDataPoint(
            timestamp=p.timestamp,
            vo2=p.vo2,
            vco2=p.vco2,
            ve=p.ve,
            hr=p.hr,
            rr=p.rr,
            rer=p.rer,
            work_rate=p.work_rate,
            spo2=p.spo2,
            sbp=p.sbp,
            dbp=p.dbp,
            extras={
                "vt": p.vt,
                "peto2": p.peto2,
                "petco2": p.petco2,
                "ve_vo2": p.ve_vo2,
                "ve_vco2": p.ve_vco2,
                "vo2_hr": p.vo2_hr,
                "bf": p.bf,
            },
        )
        for p in request.data_points
    ]
    outputs = at_predictor.predict_outputs(points, static_features=request.static_features)
    return {
        "probabilities": outputs.get("probs", []),
        "timestamps": [p.timestamp for p in request.data_points],
        "predicted_at_time": outputs.get("time_pred"),
        "vo2_peak_prediction": outputs.get("vo2_pred"),
    }


@app.post("/api/infer/exam")
def infer_exam(request: InferExamRequest):
    """从 H5 读取 exam 并推理"""
    try:
        df = realtime_manager.study_data.load_exam_dataframe(
            request.exam_id,
            smooth=request.smooth,
            start=request.start,
            end=request.end,
        )
        metadata = realtime_manager.study_data.load_exam_metadata(request.exam_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    points: List[CPETDataPoint] = []
    timestamps: List[float] = []
    for sample, point, _ in realtime_manager.simulator.iter_samples(
        df,
        speed=1.0,
        default_step=settings.delta_sec,
    ):
        points.append(point)
        timestamps.append(sample.get("timestamp", 0.0))

    outputs = at_predictor.predict_outputs(points, static_features=metadata)
    return {
        "exam_id": request.exam_id,
        "count": len(points),
        "timestamps": timestamps,
        "probabilities": outputs.get("probs", []),
        "predicted_at_time": outputs.get("time_pred"),
        "vo2_peak_prediction": outputs.get("vo2_pred"),
    }


# ---------- VO2 Peak 预测 ----------

@app.post("/api/predict/vo2peak")
def predict_vo2_peak(request: VO2PredictionRequest):
    """预测 VO2 Peak"""
    prediction = vo2_predictor.predict(
        vo2_at=request.vo2_at,
        hr_at=request.hr_at,
        work_rate_at=request.work_rate_at,
        age=request.age,
        sex=request.sex,
        weight_kg=request.weight_kg,
        height_cm=request.height_cm,
    )
    
    interpretation = vo2_predictor.get_clinical_interpretation(
        prediction, request.age
    )
    
    return {
        "predicted_vo2_peak": prediction.predicted_vo2_peak,
        "confidence_interval": prediction.confidence_interval,
        "weber_class": prediction.weber_class.value,
        "weber_description": prediction.weber_description,
        "percentile": prediction.percentile,
        "prediction_confidence": prediction.prediction_confidence,
        "clinical_interpretation": interpretation,
    }


# ---------- 风险分层 ----------

@app.post("/api/risk/stratify")
def stratify_risk(
    exercise_test: ExerciseTestRequest,
    non_exercise_test: NonExerciseTestRequest,
):
    """风险分层"""
    stratifier = RiskStratifier()
    
    ex_results = ExerciseTestResults(
        max_mets=exercise_test.max_mets,
        has_complex_arrhythmia=exercise_test.has_complex_arrhythmia,
        has_angina=exercise_test.has_angina,
        has_dyspnea=exercise_test.has_dyspnea,
        has_dizziness=exercise_test.has_dizziness,
        symptom_onset_mets=exercise_test.symptom_onset_mets,
        st_depression_mm=exercise_test.st_depression_mm,
        has_abnormal_hr_response=exercise_test.has_abnormal_hr_response,
        has_abnormal_bp_response=exercise_test.has_abnormal_bp_response,
    )
    
    non_ex_results = NonExerciseTestResults(
        lvef=non_exercise_test.lvef,
        has_cardiac_arrest_history=non_exercise_test.has_cardiac_arrest_history,
        has_chf=non_exercise_test.has_chf,
        has_ischemia_symptoms=non_exercise_test.has_ischemia_symptoms,
        has_resting_arrhythmia=non_exercise_test.has_resting_arrhythmia,
        has_clinical_depression=non_exercise_test.has_clinical_depression,
    )
    
    risk_level = stratifier.stratify(ex_results, non_ex_results)
    monitoring = stratifier.get_monitoring_recommendation(risk_level)
    
    return {
        "risk_level": risk_level.value,
        "monitoring_recommendation": monitoring,
    }


# ---------- 运动处方 ----------

@app.post("/api/prescription/generate")
def generate_prescription(request: PrescriptionRequest):
    """生成运动处方"""
    patient, cpet, ex_results, non_ex_results = _build_prescription_inputs(request)
    
    # 生成处方
    prescription = prescription_generator.generate(
        patient_info=patient,
        cpet_results=cpet,
        exercise_test_results=ex_results,
        non_exercise_results=non_ex_results,
        has_cardiac_surgery=request.has_cardiac_surgery,
        surgery_weeks_ago=request.surgery_weeks_ago,
        has_balance_issues=request.has_balance_issues,
        has_fall_history=request.has_fall_history,
        prescribing_physician=request.physician_name,
    )
    prescription.patient_id = request.patient.patient_id
    prescription.patient_name = request.patient.name
    
    # 生成摘要文本
    summary = prescription_generator.generate_summary_text(prescription)
    
    return {
        "risk_level": prescription.risk_level.value,
        "risk_description": prescription.risk_description,
        "monitoring_recommendation": prescription.monitoring_recommendation,
        "aerobic": {
            "frequency": prescription.aerobic.frequency_description,
            "intensity": prescription.aerobic.intensity_description,
            "time": prescription.aerobic.time_description,
            "type": prescription.aerobic.type_description,
            "target_hr_range": prescription.aerobic.target_hr_range,
            "rpe_range": prescription.aerobic.rpe_range,
            "progression": prescription.aerobic.progression_description,
            "precautions": prescription.aerobic.precautions,
        },
        "resistance": {
            "frequency": prescription.resistance.frequency_description,
            "intensity": prescription.resistance.intensity_description,
            "exercises": [
                {
                    "name": ex.name,
                    "sets": ex.sets,
                    "repetitions": ex.repetitions,
                    "description": ex.description,
                }
                for ex in prescription.resistance.exercises
            ],
            "precautions": prescription.resistance.precautions,
        },
        "flexibility": {
            "frequency": prescription.flexibility.frequency_description,
            "timing": prescription.flexibility.timing_description,
            "exercises": [
                {
                    "name": ex.name,
                    "hold_seconds": ex.hold_seconds,
                    "repetitions": ex.repetitions,
                    "description": ex.description,
                }
                for ex in prescription.flexibility.exercises
            ],
        },
        "neuromuscular": {
            "frequency": prescription.neuromuscular.frequency_description,
            "recommended_activities": prescription.neuromuscular.recommended_activities,
        },
        "weekly_schedule": prescription.weekly_schedule,
        "general_precautions": prescription.general_precautions,
        "emergency_instructions": prescription.emergency_instructions,
        "follow_up": prescription.follow_up_recommendation,
        "valid_until": prescription.valid_until.isoformat(),
        "summary_text": summary,
    }


# ---------- 报告生成 ----------

@app.post("/api/reports/generate")
def generate_report(request: PrescriptionRequest):
    """生成 PDF 报告"""
    global pdf_generator
    
    try:
        if pdf_generator is None:
            pdf_generator = PDFReportGenerator()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generator initialization failed: {e}"
        )
    
    patient, cpet, ex_results, non_ex_results = _build_prescription_inputs(request)

    prescription = prescription_generator.generate(
        patient_info=patient,
        cpet_results=cpet,
        exercise_test_results=ex_results,
        non_exercise_results=non_ex_results,
        has_cardiac_surgery=request.has_cardiac_surgery,
        surgery_weeks_ago=request.surgery_weeks_ago,
        has_balance_issues=request.has_balance_issues,
        has_fall_history=request.has_fall_history,
        prescribing_physician=request.physician_name,
    )
    prescription.patient_id = request.patient.patient_id
    prescription.patient_name = request.patient.name
    
    # 构建报告数据（简化版）
    from .reports.pdf_generator import PatientInfo as ReportPatientInfo
    
    patient = ReportPatientInfo(
        name=request.patient.name,
        patient_id=request.patient.patient_id,
        age=request.patient.age,
        sex=request.patient.sex,
        height_cm=request.patient.height_cm,
        weight_kg=request.patient.weight_kg,
        diagnosis=request.patient.diagnosis,
    )
    
    test_results = CPETTestResults(
        test_date=datetime.now(),
        test_duration_seconds=600,
        protocol="递增功率方案",
        termination_reason="达到目标心率",
        vo2_peak=request.cpet_results.vo2_peak,
        vo2_peak_predicted_percent=85,
        hr_max=request.cpet_results.hr_max,
        hr_max_predicted_percent=90,
        max_workload=request.cpet_results.max_workload,
        max_mets=request.cpet_results.max_mets,
        max_rer=1.1,
        at_time_seconds=480,
        at_vo2=request.cpet_results.vt1_vo2 or request.cpet_results.vo2_peak * 0.55,
        at_hr=request.cpet_results.vt1_hr or request.cpet_results.hr_max * 0.75,
        at_workload=request.cpet_results.vt1_workload or request.cpet_results.max_workload * 0.6,
    )
    
    report = CPETReport(
        patient=patient,
        test_results=test_results,
        physician_name=request.physician_name,
        prescription=prescription,
    )
    
    # 生成 PDF
    pdf_content = pdf_generator.generate_report(report)
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=cpet_report_{request.patient.patient_id}.pdf"
        }
    )


@app.post("/api/prescription/pdf")
def generate_prescription_pdf(request: PrescriptionRequest):
    """生成运动处方 PDF"""
    global pdf_generator

    try:
        if pdf_generator is None:
            pdf_generator = PDFReportGenerator()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generator initialization failed: {e}"
        )

    patient, cpet, ex_results, non_ex_results = _build_prescription_inputs(request)
    prescription = prescription_generator.generate(
        patient_info=patient,
        cpet_results=cpet,
        exercise_test_results=ex_results,
        non_exercise_results=non_ex_results,
        has_cardiac_surgery=request.has_cardiac_surgery,
        surgery_weeks_ago=request.surgery_weeks_ago,
        has_balance_issues=request.has_balance_issues,
        has_fall_history=request.has_fall_history,
        prescribing_physician=request.physician_name,
    )
    prescription.patient_id = request.patient.patient_id
    prescription.patient_name = request.patient.name

    from .reports.pdf_generator import PatientInfo as ReportPatientInfo
    report_patient = ReportPatientInfo(
        name=request.patient.name,
        patient_id=request.patient.patient_id,
        age=request.patient.age,
        sex=request.patient.sex,
        height_cm=request.patient.height_cm,
        weight_kg=request.patient.weight_kg,
        diagnosis=request.patient.diagnosis,
    )

    pdf_content = pdf_generator.generate_prescription_pdf(
        report_patient,
        prescription,
        physician_name=request.physician_name,
    )

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=exercise_prescription_{request.patient.patient_id}.pdf"
        }
    )


# ---------- AI Agent (OpenCode config) ----------

_agent_config_cache: Dict[str, Any] = {"mtime": None, "config": None}


def _strip_jsonc(text: str) -> str:
    result: List[str] = []
    in_str = False
    escape = False
    in_line = False
    in_block = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_line:
            if ch == "\n":
                in_line = False
                result.append(ch)
            i += 1
            continue
        if in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "\"":
                in_str = False
            i += 1
            continue
        if ch == "\"":
            in_str = True
            result.append(ch)
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block = True
            i += 2
            continue
        result.append(ch)
        i += 1
    return "".join(result)


def _replace_vars(text: str, base_dir: Path) -> str:
    def repl_env(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return os.environ.get(key, "")

    def repl_file(match: re.Match[str]) -> str:
        raw_path = match.group(1).strip()
        file_path = Path(raw_path)
        if not file_path.is_absolute():
            file_path = base_dir / file_path
        try:
            return file_path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    text = re.sub(r"\{env:([^}]+)\}", repl_env, text)
    text = re.sub(r"\{file:([^}]+)\}", repl_file, text)
    return text


def _substitute_vars(value: Any, base_dir: Path) -> Any:
    if isinstance(value, str):
        return _replace_vars(value, base_dir)
    if isinstance(value, list):
        return [_substitute_vars(v, base_dir) for v in value]
    if isinstance(value, dict):
        return {k: _substitute_vars(v, base_dir) for k, v in value.items()}
    return value


def _load_agent_config() -> Optional[Dict[str, Any]]:
    config_path = settings.agent_config_path
    if not config_path or not config_path.exists():
        return None
    mtime = config_path.stat().st_mtime
    if _agent_config_cache["config"] is not None and _agent_config_cache["mtime"] == mtime:
        return _agent_config_cache["config"]
    raw = config_path.read_text(encoding="utf-8")
    parsed = json.loads(_strip_jsonc(raw))
    parsed = _substitute_vars(parsed, config_path.parent)
    _agent_config_cache["mtime"] = mtime
    _agent_config_cache["config"] = parsed
    return parsed


def _resolve_agent_settings() -> Dict[str, Any]:
    config = _load_agent_config()
    if config:
        model_full = config.get("model") or config.get("agent", {}).get("model")
        if not model_full:
            raise HTTPException(status_code=500, detail="Agent model missing in config.")
        provider_map = config.get("provider") or config.get("providers") or {}
        if "/" in model_full:
            provider_id, model_name = model_full.split("/", 1)
        else:
            fallback_provider = (
                config.get("default_provider")
                or config.get("provider_id")
                or (list(provider_map.keys())[0] if len(provider_map) == 1 else None)
            )
            provider_id, model_name = fallback_provider, model_full
        if not provider_id:
            raise HTTPException(status_code=500, detail="Agent provider missing in config.")
        provider_conf = provider_map.get(provider_id, {})
        options = provider_conf.get("options", {}) if isinstance(provider_conf, dict) else {}
        base_url = options.get("baseURL") or options.get("baseUrl") or options.get("endpoint")
        api_key = options.get("apiKey") or options.get("api_key") or options.get("apikey")
        timeout = options.get("timeout") or settings.qwen_timeout
        temperature = config.get("agent", {}).get("temperature", settings.qwen_temperature)
        max_tokens = config.get("agent", {}).get("max_tokens", settings.qwen_max_tokens)
        system_prompt = config.get("agent", {}).get("system_prompt")

        if not base_url:
            raise HTTPException(status_code=500, detail="Agent baseURL missing in config.")
        if not api_key:
            raise HTTPException(status_code=500, detail="Agent apiKey missing in config.")

        return {
            "provider": provider_id,
            "model": model_name,
            "base_url": base_url,
            "api_key": api_key,
            "timeout": float(timeout),
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "system_prompt": system_prompt,
        }

    # Fallback to legacy Qwen env settings
    if not settings.qwen_api_key:
        raise HTTPException(status_code=500, detail="QWEN_API_KEY not set")
    return {
        "provider": "qwen",
        "model": settings.qwen_model,
        "base_url": settings.qwen_base_url,
        "api_key": settings.qwen_api_key,
        "timeout": settings.qwen_timeout,
        "temperature": settings.qwen_temperature,
        "max_tokens": settings.qwen_max_tokens,
        "system_prompt": None,
    }


def _call_agent(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    cfg = _resolve_agent_settings()
    base_url = cfg["base_url"].rstrip("/")
    if base_url.endswith("/chat/completions"):
        url = base_url
    else:
        url = f"{base_url}/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=cfg["timeout"]) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Agent API error: {exc}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Agent API unreachable: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent API failure: {exc}") from exc


# ---------- RAG 知识库 ----------

_retriever_instance = None


def _get_retriever():
    """Get or create knowledge retriever instance."""
    global _retriever_instance
    if _retriever_instance is None:
        try:
            from .rag import KnowledgeRetriever
            db_path = Path(__file__).resolve().parent.parent / "data" / "vector_db"
            if db_path.exists():
                _retriever_instance = KnowledgeRetriever(db_path)
        except ImportError:
            pass
    return _retriever_instance


def _retrieve_context(question: str, top_k: int = 3) -> str:
    """Retrieve relevant knowledge for a question."""
    retriever = _get_retriever()
    if retriever and retriever.is_ready():
        return retriever.retrieve_with_context(question, top_k=top_k, max_context_length=1500)
    return ""


def _extract_opencode_answer(payload: Any) -> str:
    if isinstance(payload, dict):
        if isinstance(payload.get("answer"), str):
            return payload["answer"]
        parts = payload.get("parts")
        if isinstance(parts, list):
            return "".join(
                p.get("text", "")
                for p in parts
                if isinstance(p, dict) and p.get("type") == "text"
            )
        msg = payload.get("message")
        if isinstance(msg, dict) and isinstance(msg.get("parts"), list):
            return "".join(
                p.get("text", "")
                for p in msg["parts"]
                if isinstance(p, dict) and p.get("type") == "text"
            )
        data = payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("parts"), list):
            return "".join(
                p.get("text", "")
                for p in data["parts"]
                if isinstance(p, dict) and p.get("type") == "text"
            )
    return ""


def _extract_opencode_error(payload: Any) -> str:
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict):
            msg = err.get("message") or err.get("detail") or err.get("error")
            if isinstance(msg, str):
                return msg
        info = payload.get("info")
        if isinstance(info, dict):
            err = info.get("error")
            if isinstance(err, dict):
                data = err.get("data")
                if isinstance(data, dict):
                    msg = data.get("message")
                    if isinstance(msg, str):
                        return msg
                msg = err.get("message")
                if isinstance(msg, str):
                    return msg
    return ""


@app.post("/api/agent/ask", response_model=AgentAskResponse)
async def agent_ask(request: AgentAskRequest):
    system_prompt = (
        "You are a clinical CPET assistant. Answer strictly based on the provided JSON context. "
        "If the answer is not in the context, say you do not know. "
        "Be concise, professional, and avoid making definitive diagnoses."
    )

    history_lines: list[str] = []
    for msg in (request.history or [])[-6:]:
        if msg.role in {"user", "assistant"} and isinstance(msg.content, str):
            history_lines.append(f"{msg.role}: {msg.content}")
    history_block = "\n".join(history_lines)

    ctx = request.context or {}
    context_str = json.dumps(ctx, ensure_ascii=False)
    prompt_parts = [system_prompt, f"Context (JSON):\n{context_str}"]
    if history_block:
        prompt_parts.append(f"History:\n{history_block}")
    prompt_parts.append(f"Question:\n{request.question}")
    full_prompt = "\n\n".join(prompt_parts)

    try:
        opencode_id = await opencode_create_session(title=request.page or "iOS Agent")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenCode session unavailable: {exc}") from exc

    try:
        client, resp = await opencode_send_message(
            session_id=opencode_id,
            agent="clinical",
            content=full_prompt,
            stream=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenCode send failed: {exc}") from exc

    try:
        payload = resp.json()
    except Exception:
        payload = {}

    await resp.aclose()
    await client.aclose()

    if resp.status_code >= 400:
        err = _extract_opencode_error(payload) or f"OpenCode error: {resp.status_code}"
        raise HTTPException(status_code=502, detail=err)

    answer = _extract_opencode_answer(payload).strip()
    if not answer:
        answer = "暂无可用回答。"

    return AgentAskResponse(answer=answer, model="opencode", start=None, end=None)


# ---------- OpenCode 代理 ----------

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
}


def _filter_upstream_headers(headers: httpx.Headers) -> Dict[str, str]:
    filtered: Dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in HOP_BY_HOP_HEADERS:
            continue
        filtered[key] = value
    return filtered


@app.api_route(
    "/api/assistant-api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def opencode_proxy(path: str, request: Request):
    base = settings.opencode_base_url.rstrip("/")
    target = f"{base}/{path}"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    headers["x-opencode-directory"] = str(settings.opencode_directory)

    body = await request.body()
    client = httpx.AsyncClient(timeout=None, follow_redirects=True)
    try:
        req = client.build_request(request.method, target, headers=headers, content=body)
        resp = await client.send(req, stream=True)

        accept = request.headers.get("accept", "")
        content_type = resp.headers.get("content-type", "")
        parsed = urlparse(base)
        if (
            "application/json" in accept
            and "text/html" in content_type
            and parsed.path not in ("", "/")
        ):
            await resp.aclose()
            root = f"{parsed.scheme}://{parsed.netloc}"
            fallback = f"{root}/{path}"
            if request.url.query:
                fallback = f"{fallback}?{request.url.query}"
            req = client.build_request(request.method, fallback, headers=headers, content=body)
            resp = await client.send(req, stream=True)
    except httpx.RequestError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"OpenCode proxy error: {exc}") from exc

    accept = request.headers.get("accept", "")
    content_type = resp.headers.get("content-type", "")
    if "application/json" in accept and "text/html" in content_type:
        raw = await resp.aread()
        await resp.aclose()
        await client.aclose()
        preview = raw[:200].decode("utf-8", errors="ignore").replace("\n", " ")
        return JSONResponse(
            status_code=502,
            content={
                "detail": "OpenCode API returned HTML. Check OPENCODE_BASE_URL or ensure CPET API is enabled.",
                "preview": preview,
                "target": target,
                "base_url": settings.opencode_base_url,
            },
        )

    async def stream_body():
        try:
            async for chunk in resp.aiter_raw():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_body(),
        status_code=resp.status_code,
        headers=_filter_upstream_headers(resp.headers),
    )


# ---------- 静态文件 ----------

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
frontend_dist_dir = frontend_dir / "dist"
tools_dir = Path(__file__).resolve().parent.parent / "tools"
dev_server = os.environ.get("FRONTEND_DEV_SERVER")
dev_root = os.environ.get("FRONTEND_DEV_ROOT", "").lower() in {"1", "true", "yes"}

# 挂载工具页面 (AT 标注/回放)
if tools_dir.exists():
    app.mount("/tools", StaticFiles(directory=tools_dir, html=True), name="tools")

# 挂载前端 dist
if frontend_dist_dir.exists() and not dev_server:
    app.mount("/app", StaticFiles(directory=frontend_dist_dir, html=True), name="app")

async def _proxy_to_dev(path: str, request: Request) -> StreamingResponse:
    base = dev_server.rstrip("/")
    target = f"{base}/{path}" if path else f"{base}/"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    body = await request.body()
    client = httpx.AsyncClient(timeout=None, follow_redirects=True)
    try:
        req = client.build_request(request.method, target, headers=headers, content=body)
        resp = await client.send(req, stream=True)
    except httpx.RequestError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Frontend dev proxy error: {exc}") from exc

    async def stream_body():
        try:
            async for chunk in resp.aiter_raw():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_body(),
        status_code=resp.status_code,
        headers=_filter_upstream_headers(resp.headers),
    )


if dev_server:
    @app.api_route(
        "/app/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    async def frontend_dev_proxy(path: str, request: Request):
        return await _proxy_to_dev(path, request)


@app.get("/", include_in_schema=False)
async def root(request: Request):
    """根路径重定向到前端"""
    if dev_server and dev_root:
        return await _proxy_to_dev("", request)
    if frontend_dist_dir.exists():
        return RedirectResponse(url="/app/")
    return {"message": "Xinhui API", "docs": "/api/docs"}


if dev_server:
    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        include_in_schema=False,
    )
    async def frontend_dev_fallback(path: str, request: Request):
        if path.startswith(("api", "tools", "app")):
            raise HTTPException(status_code=404, detail="Not found")
        return await _proxy_to_dev(path, request)


def run() -> None:
    """Console entry point (used by pyproject [project.scripts])."""
    import uvicorn

    host = os.environ.get("XINHUI_HOST") or os.environ.get("HOST") or "127.0.0.1"
    port_raw = os.environ.get("XINHUI_PORT") or os.environ.get("PORT") or "8000"
    try:
        port = int(port_raw)
    except Exception:
        port = 8000

    uvicorn.run("backend.api:app", host=host, port=port, reload=False)
