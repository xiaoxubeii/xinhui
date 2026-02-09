# -*- coding: utf-8 -*-
"""
CPET 工具 API 端点

将专业计算工具暴露为 REST API，供 Agent 调用。
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .calculator import (
    calculate_weber_class,
    calculate_bmi,
    calculate_predicted_hr_max,
    calculate_target_hr_zone,
    calculate_hrr_target,
    calculate_mets,
    calculate_vo2_from_mets,
    calculate_predicted_vo2max,
    calculate_oxygen_pulse,
    calculate_breathing_reserve,
    calculate_anaerobic_threshold_ratio,
)
from .risk import (
    assess_exercise_risk,
    get_monitoring_recommendation,
    check_contraindications,
    RiskLevel,
)
from .prescription import (
    generate_hr_prescription,
    generate_exercise_intensity,
    generate_weekly_schedule,
)

router = APIRouter(prefix="/api/tools", tags=["Tools"])


# ==================== 请求模型 ====================

class WeberRequest(BaseModel):
    vo2_peak: float = Field(..., description="峰值摄氧量 (ml/kg/min)")


class BMIRequest(BaseModel):
    weight_kg: float = Field(..., description="体重 (kg)")
    height_cm: float = Field(..., description="身高 (cm)")


class PredictedHRMaxRequest(BaseModel):
    age: int = Field(..., description="年龄")
    method: str = Field("tanaka", description="计算方法: traditional, tanaka, gellish")


class TargetHRZoneRequest(BaseModel):
    hr_max: int = Field(..., description="最大心率")
    hr_rest: int = Field(..., description="静息心率")
    intensity_low: float = Field(0.5, description="强度下限 (0-1)")
    intensity_high: float = Field(0.7, description="强度上限 (0-1)")
    method: str = Field("karvonen", description="计算方法: karvonen, percentage")


class HRRTargetRequest(BaseModel):
    hr_max: int = Field(..., description="最大心率")
    hr_rest: int = Field(..., description="静息心率")
    intensity: float = Field(..., description="目标强度 (0-1)")


class METsRequest(BaseModel):
    vo2: float = Field(..., description="摄氧量")
    weight_kg: Optional[float] = Field(None, description="体重 (kg)，如提供则 vo2 为绝对值 ml/min")


class VO2FromMETsRequest(BaseModel):
    mets: float = Field(..., description="代谢当量")


class PredictedVO2MaxRequest(BaseModel):
    age: int = Field(..., description="年龄")
    sex: str = Field(..., description="性别: male, female")
    weight_kg: Optional[float] = Field(None, description="体重 (kg)")
    height_cm: Optional[float] = Field(None, description="身高 (cm)")
    method: str = Field("wasserman", description="计算方法: wasserman, jones")


class OxygenPulseRequest(BaseModel):
    vo2: float = Field(..., description="摄氧量 (ml/min)")
    hr: int = Field(..., description="心率 (bpm)")


class BreathingReserveRequest(BaseModel):
    ve_max: float = Field(..., description="最大分钟通气量 (L/min)")
    mvv: float = Field(..., description="最大自主通气量 (L/min)")


class ATRatioRequest(BaseModel):
    at_vo2: float = Field(..., description="无氧阈 VO2 (ml/kg/min)")
    vo2_peak: float = Field(..., description="峰值 VO2 (ml/kg/min)")


class RiskAssessmentRequest(BaseModel):
    max_mets: Optional[float] = None
    has_ischemia: bool = False
    st_depression_mm: float = 0
    has_angina: bool = False
    has_arrhythmia: bool = False
    arrhythmia_type: str = "none"
    has_abnormal_bp: bool = False
    bp_response: str = "normal"
    lvef: Optional[float] = None
    has_heart_failure: bool = False
    nyha_class: Optional[int] = None
    has_cardiac_arrest_history: bool = False
    has_mi_history: bool = False
    mi_weeks_ago: Optional[int] = None
    has_cabg_history: bool = False
    cabg_weeks_ago: Optional[int] = None
    has_pci_history: bool = False
    has_diabetes: bool = False
    has_renal_disease: bool = False
    age: Optional[int] = None


class ContraindicationsRequest(BaseModel):
    has_unstable_angina: bool = False
    has_acute_mi: bool = False
    acute_mi_days: Optional[int] = None
    has_uncontrolled_arrhythmia: bool = False
    has_severe_aortic_stenosis: bool = False
    has_acute_heart_failure: bool = False
    has_acute_pe: bool = False
    has_acute_myocarditis: bool = False
    has_acute_pericarditis: bool = False
    has_aortic_dissection: bool = False
    has_uncontrolled_hypertension: bool = False
    sbp: Optional[int] = None
    dbp: Optional[int] = None
    has_moderate_valve_disease: bool = False
    has_electrolyte_abnormality: bool = False
    has_hypertrophic_cardiomyopathy: bool = False
    has_high_degree_av_block: bool = False
    has_mental_impairment: bool = False
    has_orthopedic_limitation: bool = False


class HRPrescriptionRequest(BaseModel):
    hr_max: int = Field(..., description="最大心率")
    hr_rest: int = Field(..., description="静息心率")
    hr_at: Optional[int] = Field(None, description="无氧阈心率")
    risk_level: str = Field("low", description="风险等级: low, moderate, high")
    use_at_based: bool = Field(True, description="是否使用 AT 心率")


class ExerciseIntensityRequest(BaseModel):
    vo2_peak: float = Field(..., description="峰值摄氧量")
    hr_max: int = Field(..., description="最大心率")
    hr_rest: int = Field(..., description="静息心率")
    hr_at: Optional[int] = Field(None, description="无氧阈心率")
    vo2_at: Optional[float] = Field(None, description="无氧阈 VO2")
    risk_level: str = Field("low", description="风险等级")


class WeeklyScheduleRequest(BaseModel):
    risk_level: str = Field("low", description="风险等级")
    hr_max: int = Field(150, description="最大心率")
    hr_rest: int = Field(70, description="静息心率")
    hr_at: Optional[int] = Field(None, description="无氧阈心率")
    include_resistance: bool = Field(True, description="包含抗阻训练")
    include_flexibility: bool = Field(True, description="包含柔韧性训练")
    phase: str = Field("maintenance", description="康复阶段: initial, improvement, maintenance")


# ==================== 计算器端点 ====================

@router.post("/weber-class", summary="Weber 心功能分级")
def api_weber_class(request: WeberRequest):
    """根据 VO2peak 计算 Weber 心功能分级"""
    result = calculate_weber_class(request.vo2_peak)
    return {
        "grade": result.grade.value,
        "vo2_peak": result.vo2_peak,
        "description": result.description,
        "prognosis": result.prognosis,
    }


@router.post("/bmi", summary="计算 BMI")
def api_bmi(request: BMIRequest):
    """计算体质指数"""
    return calculate_bmi(request.weight_kg, request.height_cm)


@router.post("/predicted-hr-max", summary="预测最大心率")
def api_predicted_hr_max(request: PredictedHRMaxRequest):
    """计算预测最大心率"""
    return calculate_predicted_hr_max(request.age, request.method)


@router.post("/target-hr-zone", summary="目标心率区间")
def api_target_hr_zone(request: TargetHRZoneRequest):
    """计算目标心率区间"""
    return calculate_target_hr_zone(
        request.hr_max,
        request.hr_rest,
        request.intensity_low,
        request.intensity_high,
        request.method,
    )


@router.post("/hrr-target", summary="心率储备目标")
def api_hrr_target(request: HRRTargetRequest):
    """使用心率储备法计算目标心率"""
    return calculate_hrr_target(request.hr_max, request.hr_rest, request.intensity)


@router.post("/mets", summary="计算 METs")
def api_mets(request: METsRequest):
    """计算代谢当量"""
    return calculate_mets(request.vo2, request.weight_kg)


@router.post("/vo2-from-mets", summary="METs 转 VO2")
def api_vo2_from_mets(request: VO2FromMETsRequest):
    """从 METs 计算 VO2"""
    return calculate_vo2_from_mets(request.mets)


@router.post("/predicted-vo2max", summary="预测 VO2max")
def api_predicted_vo2max(request: PredictedVO2MaxRequest):
    """计算预测 VO2max"""
    return calculate_predicted_vo2max(
        request.age,
        request.sex,
        request.weight_kg,
        request.height_cm,
        request.method,
    )


@router.post("/oxygen-pulse", summary="计算氧脉搏")
def api_oxygen_pulse(request: OxygenPulseRequest):
    """计算氧脉搏"""
    return calculate_oxygen_pulse(request.vo2, request.hr)


@router.post("/breathing-reserve", summary="计算呼吸储备")
def api_breathing_reserve(request: BreathingReserveRequest):
    """计算呼吸储备"""
    return calculate_breathing_reserve(request.ve_max, request.mvv)


@router.post("/at-ratio", summary="AT/VO2peak 比值")
def api_at_ratio(request: ATRatioRequest):
    """计算无氧阈占峰值摄氧量比例"""
    return calculate_anaerobic_threshold_ratio(request.at_vo2, request.vo2_peak)


# ==================== 风险评估端点 ====================

@router.post("/risk-assessment", summary="运动风险评估")
def api_risk_assessment(request: RiskAssessmentRequest):
    """评估运动风险等级"""
    result = assess_exercise_risk(
        max_mets=request.max_mets,
        has_ischemia=request.has_ischemia,
        st_depression_mm=request.st_depression_mm,
        has_angina=request.has_angina,
        has_arrhythmia=request.has_arrhythmia,
        arrhythmia_type=request.arrhythmia_type,
        has_abnormal_bp=request.has_abnormal_bp,
        bp_response=request.bp_response,
        lvef=request.lvef,
        has_heart_failure=request.has_heart_failure,
        nyha_class=request.nyha_class,
        has_cardiac_arrest_history=request.has_cardiac_arrest_history,
        has_mi_history=request.has_mi_history,
        mi_weeks_ago=request.mi_weeks_ago,
        has_cabg_history=request.has_cabg_history,
        cabg_weeks_ago=request.cabg_weeks_ago,
        has_pci_history=request.has_pci_history,
        has_diabetes=request.has_diabetes,
        has_renal_disease=request.has_renal_disease,
        age=request.age,
    )
    return {
        "level": result.level.value,
        "score": result.score,
        "summary": result.summary,
        "factors": [
            {
                "name": f.name,
                "present": f.present,
                "severity": f.severity,
                "description": f.description,
            }
            for f in result.factors
        ],
        "recommendations": result.recommendations,
    }


@router.get("/monitoring/{risk_level}", summary="监护建议")
def api_monitoring(risk_level: str):
    """根据风险等级获取监护建议"""
    try:
        level = RiskLevel(risk_level)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid risk level: {risk_level}")
    return get_monitoring_recommendation(level)


@router.post("/contraindications", summary="禁忌症检查")
def api_contraindications(request: ContraindicationsRequest):
    """检查运动禁忌症"""
    return check_contraindications(
        has_unstable_angina=request.has_unstable_angina,
        has_acute_mi=request.has_acute_mi,
        acute_mi_days=request.acute_mi_days,
        has_uncontrolled_arrhythmia=request.has_uncontrolled_arrhythmia,
        has_severe_aortic_stenosis=request.has_severe_aortic_stenosis,
        has_acute_heart_failure=request.has_acute_heart_failure,
        has_acute_pe=request.has_acute_pe,
        has_acute_myocarditis=request.has_acute_myocarditis,
        has_acute_pericarditis=request.has_acute_pericarditis,
        has_aortic_dissection=request.has_aortic_dissection,
        has_uncontrolled_hypertension=request.has_uncontrolled_hypertension,
        sbp=request.sbp,
        dbp=request.dbp,
        has_moderate_valve_disease=request.has_moderate_valve_disease,
        has_electrolyte_abnormality=request.has_electrolyte_abnormality,
        has_hypertrophic_cardiomyopathy=request.has_hypertrophic_cardiomyopathy,
        has_high_degree_av_block=request.has_high_degree_av_block,
        has_mental_impairment=request.has_mental_impairment,
        has_orthopedic_limitation=request.has_orthopedic_limitation,
    )


# ==================== 处方生成端点 ====================

@router.post("/hr-prescription", summary="心率处方")
def api_hr_prescription(request: HRPrescriptionRequest):
    """生成基于心率的运动处方"""
    return generate_hr_prescription(
        hr_max=request.hr_max,
        hr_rest=request.hr_rest,
        hr_at=request.hr_at,
        risk_level=request.risk_level,
        use_at_based=request.use_at_based,
    )


@router.post("/exercise-intensity", summary="运动强度处方")
def api_exercise_intensity(request: ExerciseIntensityRequest):
    """生成多维度运动强度处方"""
    return generate_exercise_intensity(
        vo2_peak=request.vo2_peak,
        hr_max=request.hr_max,
        hr_rest=request.hr_rest,
        hr_at=request.hr_at,
        vo2_at=request.vo2_at,
        risk_level=request.risk_level,
    )


@router.post("/weekly-schedule", summary="每周运动计划")
def api_weekly_schedule(request: WeeklyScheduleRequest):
    """生成每周运动计划"""
    return generate_weekly_schedule(
        risk_level=request.risk_level,
        hr_max=request.hr_max,
        hr_rest=request.hr_rest,
        hr_at=request.hr_at,
        include_resistance=request.include_resistance,
        include_flexibility=request.include_flexibility,
        phase=request.phase,
    )


# ==================== 工具列表 ====================

@router.get("/", summary="工具列表")
def list_tools():
    """列出所有可用工具"""
    return {
        "calculator": [
            {"name": "weber-class", "description": "Weber 心功能分级", "method": "POST"},
            {"name": "bmi", "description": "计算 BMI", "method": "POST"},
            {"name": "predicted-hr-max", "description": "预测最大心率", "method": "POST"},
            {"name": "target-hr-zone", "description": "目标心率区间", "method": "POST"},
            {"name": "hrr-target", "description": "心率储备目标", "method": "POST"},
            {"name": "mets", "description": "计算 METs", "method": "POST"},
            {"name": "vo2-from-mets", "description": "METs 转 VO2", "method": "POST"},
            {"name": "predicted-vo2max", "description": "预测 VO2max", "method": "POST"},
            {"name": "oxygen-pulse", "description": "计算氧脉搏", "method": "POST"},
            {"name": "breathing-reserve", "description": "计算呼吸储备", "method": "POST"},
            {"name": "at-ratio", "description": "AT/VO2peak 比值", "method": "POST"},
        ],
        "risk": [
            {"name": "risk-assessment", "description": "运动风险评估", "method": "POST"},
            {"name": "monitoring/{risk_level}", "description": "监护建议", "method": "GET"},
            {"name": "contraindications", "description": "禁忌症检查", "method": "POST"},
        ],
        "prescription": [
            {"name": "hr-prescription", "description": "心率处方", "method": "POST"},
            {"name": "exercise-intensity", "description": "运动强度处方", "method": "POST"},
            {"name": "weekly-schedule", "description": "每周运动计划", "method": "POST"},
        ],
    }
