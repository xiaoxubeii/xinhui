# -*- coding: utf-8 -*-
"""
实时 WebSocket 模块

处理 CPET 实时数据流和推送预测结果。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Any
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect

from ..config import settings
from ..data_loader import CPETStudyData
from ..inference.at_predictor import ATPredictor, ATOnlineSession, ATOnlineResult, CPETDataPoint
from ..inference.vo2_predictor import VO2PeakPredictor
from .simulator import CPETSimulator

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """会话状态"""
    session_id: str
    patient_id: Optional[str]
    started_at: datetime
    at_session: ATOnlineSession
    data_count: int = 0
    at_triggered: bool = False
    trigger_time: Optional[float] = None
    mode: str = "device"
    static_features: Optional[Dict[str, Any]] = None
    exam_id: Optional[str] = None


@dataclass
class SessionConfig:
    session_id: str
    patient_id: Optional[str] = None
    threshold: float = 0.7
    persistence: int = 3
    mode: str = "device"
    sim_speed: float = 1.0
    sim_smooth: str = "none"
    sim_start: Optional[float] = None
    sim_end: Optional[float] = None


class RealtimeManager:
    """实时会话管理器"""
    
    def __init__(
        self,
        at_predictor: Optional[ATPredictor] = None,
        vo2_predictor: Optional[VO2PeakPredictor] = None,
    ):
        self.at_predictor = at_predictor or ATPredictor()
        self.vo2_predictor = vo2_predictor or VO2PeakPredictor()
        self.study_data = CPETStudyData(settings.data_file)
        self.simulator = CPETSimulator(self.study_data)
        
        # 活跃连接
        self.active_connections: Dict[str, WebSocket] = {}
        # 会话状态
        self.sessions: Dict[str, SessionState] = {}
        # 待连接会话参数
        self.pending_configs: Dict[str, SessionConfig] = {}
        # 仿真任务
        self.sim_tasks: Dict[str, asyncio.Task] = {}

    def register_session(self, config: SessionConfig) -> None:
        self.pending_configs[config.session_id] = config
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        threshold: float = 0.7,
        persistence: int = 3,
    ) -> str:
        """
        建立 WebSocket 连接
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID（可选，不提供则自动生成）
            patient_id: 患者 ID
            threshold: AT 触发阈值
            persistence: 连续超过阈值次数
            
        Returns:
            str: 会话 ID
        """
        await websocket.accept()
        
        if not session_id:
            session_id = str(uuid4())
        
        self.active_connections[session_id] = websocket

        config = self.pending_configs.pop(session_id, None)
        if config is not None:
            threshold = config.threshold
            persistence = config.persistence
            patient_id = config.patient_id
        
        # 创建会话状态
        at_session = self.at_predictor.create_session(
            threshold=threshold,
            persistence=persistence,
        )
        
        self.sessions[session_id] = SessionState(
            session_id=session_id,
            patient_id=patient_id,
            started_at=datetime.now(),
            at_session=at_session,
            mode=config.mode if config is not None else "device",
        )
        
        logger.info(f"WebSocket connected: {session_id}")
        
        # 发送连接确认
        await self._send_message(session_id, {
            "type": "connected",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        })

        if config is not None and config.mode == "sim":
            self._start_simulation(session_id, config)
        
        return session_id
    
    def disconnect(self, session_id: str) -> None:
        """断开连接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.sessions:
            del self.sessions[session_id]
        task = self.sim_tasks.pop(session_id, None)
        if task is not None:
            task.cancel()
        logger.info(f"WebSocket disconnected: {session_id}")
    
    async def process_data(
        self,
        session_id: str,
        data: dict,
    ) -> dict:
        """
        处理接收到的数据
        
        Args:
            session_id: 会话 ID
            data: 数据字典
            
        Returns:
            dict: 处理结果
        """
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        session = self.sessions[session_id]
        
        # 解析数据点
        try:
            extras = {
                str(k).lower(): v
                for k, v in data.items()
                if k
                not in {
                    "timestamp",
                    "vo2",
                    "vco2",
                    "ve",
                    "hr",
                    "rr",
                    "rer",
                    "work_rate",
                    "spo2",
                    "sbp",
                    "dbp",
                }
            }
            point = CPETDataPoint(
                timestamp=data.get("timestamp", 0),
                vo2=data.get("vo2", 0),
                vco2=data.get("vco2", 0),
                ve=data.get("ve", 0),
                hr=data.get("hr", 0),
                rr=data.get("rr", 0),
                rer=data.get("rer", 0),
                work_rate=data.get("work_rate", data.get("power_load", data.get("power", 0))),
                spo2=data.get("spo2"),
                sbp=data.get("sbp"),
                dbp=data.get("dbp"),
                extras=extras,
            )
        except Exception as e:
            return {"error": f"Invalid data format: {e}"}
        
        # 添加到会话
        session.at_session.add_data_point(point)
        session.data_count += 1
        
        power_load = point.work_rate

        # 热身阶段不进行模型预测（power_load <= 0 且尚未进入运动期）
        if power_load <= 0 and not session.at_session.has_exercise_started:
            result = ATOnlineResult(
                timestamp=point.timestamp,
                at_probability=0.0,
                at_triggered=session.at_triggered,
                predicted_at_time=None,
                confidence=0.0,
                intensity_zone="warmup",
                alerts=[],
            )
            outputs = {}
        else:
            # 预测 AT 概率
            outputs = self.at_predictor.predict_outputs(
                session.at_session.data_buffer,
                static_features=session.static_features,
            )
            probs = outputs.get("probs", [])
            current_prob = probs[-1] if probs else 0.0

            # 更新会话状态
            result = session.at_session.update_probability(
                current_prob,
                predicted_at_time=outputs.get("time_pred"),
                power_load=power_load,
            )
        
        # 更新会话状态
        if result.at_triggered and not session.at_triggered:
            session.at_triggered = True
            session.trigger_time = result.timestamp
        
        # 构建响应
        response = {
            "type": "prediction",
            "timestamp": point.timestamp,
            "at_probability": round(result.at_probability, 3),
            "at_triggered": result.at_triggered,
            "predicted_at_time": result.predicted_at_time,
            "confidence": round(result.confidence, 2),
            "intensity_zone": result.intensity_zone,
            "alerts": result.alerts,
            "data_count": session.data_count,
            "exam_id": session.exam_id,
        }
        response["sample"] = data
        
        # 如果 AT 已触发，预测 VO2 Peak
        if outputs.get("vo2_pred") is not None:
            response["vo2_peak_prediction"] = self._build_vo2_from_model(
                float(outputs["vo2_pred"])
            )
        elif result.at_triggered and session.trigger_time:
            vo2_pred = self._predict_vo2_peak(session, point)
            if vo2_pred:
                response["vo2_peak_prediction"] = vo2_pred
        
        return response
    
    def _predict_vo2_peak(
        self,
        session: SessionState,
        current_point: CPETDataPoint,
    ) -> Optional[dict]:
        """预测 VO2 Peak"""
        try:
            # 获取 AT 时刻的数据
            # 这里简化处理，使用当前数据
            prediction = self.vo2_predictor.predict(
                vo2_at=current_point.vo2,
                hr_at=current_point.hr,
                work_rate_at=current_point.work_rate,
                age=50,  # 需要从患者信息获取
                sex="male",
                weight_kg=70,
                height_cm=170,
            )
            
            return {
                "predicted_vo2_peak": prediction.predicted_vo2_peak,
                "confidence_interval": prediction.confidence_interval,
                "weber_class": prediction.weber_class.value,
                "weber_description": prediction.weber_description,
            }
        except Exception as e:
            logger.error(f"VO2 Peak prediction error: {e}")
            return None

    def _build_vo2_from_model(self, predicted_vo2_peak: float) -> Optional[dict]:
        try:
            weber_class = self.vo2_predictor._classify_weber(predicted_vo2_peak)
            return {
                "predicted_vo2_peak": round(predicted_vo2_peak, 1),
                "confidence_interval": None,
                "weber_class": weber_class.value,
                "weber_description": self.vo2_predictor.WEBER_DESCRIPTIONS[weber_class],
            }
        except Exception as exc:
            logger.error("VO2 model prediction formatting error: %s", exc)
            return None

    def _start_simulation(self, session_id: str, config: SessionConfig) -> None:
        task = asyncio.create_task(self._run_simulation(session_id, config))
        self.sim_tasks[session_id] = task

    async def _run_simulation(self, session_id: str, config: SessionConfig) -> None:
        try:
            exam_id = self.simulator.sample_exam_id()
            df = self.simulator.load_exam(
                exam_id,
                smooth=config.sim_smooth,
                start=config.sim_start,
                end=config.sim_end,
            )
            metadata = self.study_data.load_exam_metadata(exam_id)

            session = self.sessions.get(session_id)
            if session is None:
                return
            session.exam_id = exam_id
            session.static_features = metadata

            for sample, point, sleep_sec in self.simulator.iter_samples(
                df,
                speed=config.sim_speed,
                default_step=settings.delta_sec,
            ):
                if session_id not in self.active_connections:
                    break
                result = await self.process_data(session_id, sample)
                result["type"] = "prediction"
                result["sample"] = sample
                result["exam_id"] = exam_id
                await self._send_message(session_id, result)
                if sleep_sec > 0:
                    await asyncio.sleep(sleep_sec)
        except asyncio.CancelledError:
            logger.info("Simulation cancelled: %s", session_id)
        except Exception as exc:
            logger.error("Simulation error: %s", exc)
            await self._send_message(session_id, {"type": "error", "message": str(exc)})
    
    async def _send_message(self, session_id: str, message: dict) -> None:
        """发送消息"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)
    
    async def broadcast(self, message: dict) -> None:
        """广播消息到所有连接"""
        for session_id in self.active_connections:
            await self._send_message(session_id, message)
    
    def get_session_summary(self, session_id: str) -> Optional[dict]:
        """获取会话摘要"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        return {
            "session_id": session.session_id,
            "patient_id": session.patient_id,
            "started_at": session.started_at.isoformat(),
            "data_count": session.data_count,
            "at_triggered": session.at_triggered,
            "trigger_time": session.trigger_time,
            "duration_seconds": (datetime.now() - session.started_at).total_seconds(),
            "mode": session.mode,
            "exam_id": session.exam_id,
        }


# 全局管理器实例
try:
    _at_predictor = ATPredictor(
        model_path=str(settings.pace_former_checkpoint),
        config_path=str(settings.pace_former_config),
        device=settings.pace_former_device,
    )
except Exception as exc:
    logger.warning("Failed to load PaceFormer, fallback to rule-based: %s", exc)
    _at_predictor = ATPredictor()

_at_predictor.normalization = settings.pace_former_norm
_at_predictor.norm_min_points = settings.pace_former_norm_min_points
_at_predictor.min_points_for_model = settings.pace_former_min_points

realtime_manager = RealtimeManager(at_predictor=_at_predictor)


async def websocket_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = None,
):
    """WebSocket 端点处理函数"""
    sid = await realtime_manager.connect(websocket, session_id)
    
    try:
        while True:
            # 接收数据
            data = await websocket.receive_json()
            
            # 处理数据
            result = await realtime_manager.process_data(sid, data)
            
            # 发送结果
            await websocket.send_json(result)
            
    except WebSocketDisconnect:
        realtime_manager.disconnect(sid)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        realtime_manager.disconnect(sid)
