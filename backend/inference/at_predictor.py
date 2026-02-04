# -*- coding: utf-8 -*-
"""
AT 实时预测器

基于 PaceFormer 模型进行 AT 在线预测。
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

logger = logging.getLogger(__name__)


def _ensure_vox_cpet_on_path() -> None:
    project_root = Path(__file__).resolve().parents[3]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


@dataclass
class CPETDataPoint:
    """CPET 数据点"""
    timestamp: float      # 时间戳 (秒)
    vo2: float           # 摄氧量 (ml/kg/min)
    vco2: float          # 二氧化碳排出量 (ml/kg/min)
    ve: float            # 通气量 (L/min)
    hr: float            # 心率 (bpm)
    rr: float            # 呼吸频率 (breaths/min)
    rer: float           # 呼吸交换率
    work_rate: float     # 功率 (W)
    spo2: Optional[float] = None  # 血氧饱和度
    sbp: Optional[float] = None   # 收缩压
    dbp: Optional[float] = None   # 舒张压
    extras: Dict[str, Optional[float]] = field(default_factory=dict)
    
    def to_feature_vector(self, feature_names: List[str]) -> np.ndarray:
        """转换为特征向量"""
        return np.array([self.get_feature(f) for f in feature_names], dtype=np.float32)

    def get_feature(self, name: str) -> float:
        key = str(name).strip()
        lower = key.lower()

        direct_map = {
            "timestamp": self.timestamp,
            "time": self.timestamp,
            "vo2": self.vo2,
            "vco2": self.vco2,
            "ve": self.ve,
            "hr": self.hr,
            "rr": self.rr,
            "rer": self.rer,
            "work_rate": self.work_rate,
            "power_load": self.work_rate,
            "power": self.work_rate,
            "spo2": self.spo2,
            "sbp": self.sbp,
            "dbp": self.dbp,
            "bf": self.rr,
        }

        extras_val = self.extras.get(lower)
        if extras_val is not None:
            return float(extras_val)

        if lower in direct_map and direct_map[lower] is not None:
            return float(direct_map[lower])

        if lower == "ve_vo2":
            return float(self.ve / self.vo2) if self.vo2 else 0.0
        if lower == "ve_vco2":
            return float(self.ve / self.vco2) if self.vco2 else 0.0
        if lower == "vo2_hr":
            return float(self.vo2 / self.hr) if self.hr else 0.0

        return 0.0


@dataclass
class ATOnlineResult:
    """AT 在线预测结果"""
    timestamp: float
    at_probability: float
    at_triggered: bool
    predicted_at_time: Optional[float]
    confidence: float
    intensity_zone: str  # 'warmup', 'aerobic', 'threshold', 'anaerobic', 'recovery'
    alerts: List[str] = field(default_factory=list)


class ATOnlineSession:
    """AT 在线预测会话"""
    
    def __init__(
        self,
        threshold: float = 0.7,
        persistence: int = 3,
        window_size: int = 60,
    ):
        """
        初始化会话
        
        Args:
            threshold: AT 触发阈值
            persistence: 连续超过阈值的次数才触发
            window_size: 滑动窗口大小（数据点数）
        """
        self.threshold = threshold
        self.persistence = persistence
        self.window_size = window_size
        
        # 数据缓存
        self.data_buffer: List[CPETDataPoint] = []
        self.prob_history: List[float] = []
        self.timestamps: List[float] = []
        
        # 状态
        self.at_triggered = False
        self.trigger_time: Optional[float] = None
        self.consecutive_above_threshold = 0
        self.has_exercise_started = False
        self.vt1_trigger_time: Optional[float] = None
        self.vt1_transition_seconds = 30
    
    def add_data_point(self, point: CPETDataPoint) -> None:
        """添加数据点"""
        self.data_buffer.append(point)
        self.timestamps.append(point.timestamp)
        
        # 保持窗口大小
        if len(self.data_buffer) > self.window_size * 2:
            self.data_buffer = self.data_buffer[-self.window_size * 2:]
            self.timestamps = self.timestamps[-self.window_size * 2:]
    
    def update_probability(
        self,
        prob: float,
        predicted_at_time: Optional[float] = None,
        power_load: Optional[float] = None,
    ) -> ATOnlineResult:
        """
        更新 AT 概率并检查是否触发
        
        Args:
            prob: 当前时刻的 AT 概率
            power_load: 当前功率负荷 (W)
            
        Returns:
            ATOnlineResult: 预测结果
        """
        self.prob_history.append(prob)
        
        # 检查是否触发
        alerts = []
        if not self.at_triggered:
            if prob >= self.threshold:
                self.consecutive_above_threshold += 1
                if self.consecutive_above_threshold >= self.persistence:
                    self.at_triggered = True
                    self.trigger_time = self.timestamps[-1] if self.timestamps else 0
                    alerts.append("AT 已到达！建议可以停止测试")
            else:
                self.consecutive_above_threshold = 0
        
        # 预测 AT 时间
        predicted_at = predicted_at_time if predicted_at_time is not None else self._estimate_at_time()
        
        # 判断强度区间
        current_time = self.timestamps[-1] if self.timestamps else 0
        intensity_zone = self._determine_intensity_zone(power_load, current_time)
        
        # 生成提示
        if not self.at_triggered:
            if prob >= 0.5:
                alerts.append("接近 AT，请注意观察")
            elif prob >= 0.3:
                alerts.append("进入有氧区")
        
        # 计算置信度
        confidence = self._calculate_confidence()
        
        return ATOnlineResult(
            timestamp=self.timestamps[-1] if self.timestamps else 0,
            at_probability=prob,
            at_triggered=self.at_triggered,
            predicted_at_time=predicted_at,
            confidence=confidence,
            intensity_zone=intensity_zone,
            alerts=alerts,
        )
    
    def _estimate_at_time(self) -> Optional[float]:
        """估计 AT 时间"""
        if self.at_triggered:
            return self.trigger_time
        
        if len(self.prob_history) < 10:
            return None
        
        # 简单线性外推
        recent_probs = self.prob_history[-10:]
        recent_times = self.timestamps[-10:] if len(self.timestamps) >= 10 else None
        
        if recent_times is None:
            return None
        
        # 计算概率增长率
        prob_diff = recent_probs[-1] - recent_probs[0]
        time_diff = recent_times[-1] - recent_times[0]
        
        if time_diff <= 0 or prob_diff <= 0:
            return None
        
        rate = prob_diff / time_diff
        remaining = self.threshold - recent_probs[-1]
        
        if remaining <= 0:
            return recent_times[-1]
        
        estimated_time = recent_times[-1] + remaining / rate
        return estimated_time
    
    def _determine_intensity_zone(self, power_load: Optional[float], current_time: float) -> str:
        """判断强度区间"""
        if power_load is None:
            return "warmup"
        if power_load <= 0:
            return "recovery" if self.has_exercise_started else "warmup"
        self.has_exercise_started = True
        if not self.at_triggered:
            return "aerobic"
        if self.vt1_trigger_time is None:
            self.vt1_trigger_time = current_time
        if current_time - (self.vt1_trigger_time or 0) <= self.vt1_transition_seconds:
            return "threshold"
        return "anaerobic"
    
    def _calculate_confidence(self) -> float:
        """计算预测置信度"""
        if len(self.prob_history) < 5:
            return 0.5
        
        # 基于概率稳定性计算置信度
        recent = self.prob_history[-5:]
        std = np.std(recent)
        
        # 标准差越小，置信度越高
        confidence = max(0.5, 1.0 - std * 2)
        return min(1.0, confidence)
    
    def reset(self) -> None:
        """重置会话"""
        self.data_buffer.clear()
        self.prob_history.clear()
        self.timestamps.clear()
        self.at_triggered = False
        self.trigger_time = None
        self.consecutive_above_threshold = 0
        self.has_exercise_started = False
        self.vt1_trigger_time = None


class ATPredictor:
    """AT 预测器"""
    
    # 默认特征列表
    DEFAULT_FEATURES = [
        'vo2', 'vco2', 've', 'hr', 'rr', 'rer', 'work_rate'
    ]
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        config_path: Optional[str] = None,
        device: str = "cpu",
    ):
        """
        初始化预测器
        
        Args:
            model_path: 模型权重路径
            config_path: 模型配置路径
            device: 推理设备
        """
        self.model_path = model_path
        self.config_path = config_path
        self.device = device
        self.model = None
        self.config = None
        self.feature_names = self.DEFAULT_FEATURES
        self.scaler_params = None
        self.static_feature_columns: List[str] = []
        self.eval_mode: str = "online"
        self.normalization: str = "per_exam"
        self.norm_min_points: int = 12
        self.min_points_for_model: int = 8
        
        if model_path:
            self.load_model(model_path, config_path)
    
    def load_model(
        self,
        model_path: str,
        config_path: Optional[str] = None,
    ) -> None:
        """加载模型"""
        if not HAS_TORCH:
            raise RuntimeError("PyTorch not installed")

        model_path = Path(model_path).expanduser()
        if not model_path.exists():
            raise FileNotFoundError(f"Model checkpoint not found: {model_path}")

        if not config_path:
            raise ValueError("PaceFormer config_path is required for model loading.")

        config_path = str(Path(config_path).expanduser())
        config = self._load_config(config_path)
        self.config = config
        self.feature_names = self._resolve_feature_columns(config)
        self.static_feature_columns = self._resolve_static_columns(config)
        self.eval_mode = str(config.get("eval_mode", "online")).lower() or "online"
        self.normalization = str(
            config.get("infer_normalization", self.normalization)
        ).lower() or self.normalization

        _ensure_vox_cpet_on_path()
        from vox_cpet.models.v4 import PaceFormer

        model_cfg = PaceFormer.config_parser(config)
        model = PaceFormer(model_cfg)
        checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
        state = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
        model.load_state_dict(state, strict=False)
        model.eval()
        model.to(self.device)
        self.model = model

        logger.info(
            "Loaded PaceFormer from %s (features=%d, static=%d, mode=%s)",
            model_path,
            len(self.feature_names),
            len(self.static_feature_columns),
            self.eval_mode,
        )

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        _ensure_vox_cpet_on_path()
        from vox_cpet.training.config_manager import ConfigManager

        cfg_path = Path(config_path).expanduser().resolve()
        configs_root = cfg_path.parents[3] if len(cfg_path.parents) >= 4 else cfg_path.parent
        manager = ConfigManager(str(cfg_path), variables={"CONFIGS_DIR": str(configs_root)})
        return manager.config

    def _resolve_feature_columns(self, config: Dict[str, Any]) -> List[str]:
        dataset_cfg = config.get("dataset", config)
        columns = dataset_cfg.get("feature_columns") or config.get("feature_columns")
        if not columns:
            return list(self.DEFAULT_FEATURES)
        if isinstance(columns, str):
            return [c.strip() for c in columns.split(",") if c.strip()]
        return list(columns)

    def _resolve_static_columns(self, config: Dict[str, Any]) -> List[str]:
        dataset_cfg = config.get("dataset", config)
        columns = dataset_cfg.get("static_feature_columns") or config.get("static_feature_columns")
        if not columns:
            return []
        if isinstance(columns, str):
            return [c.strip() for c in columns.split(",") if c.strip()]
        return list(columns)

    def build_static_feature_vector(self, metadata: Optional[Dict[str, Any]]) -> Optional[List[float]]:
        if not self.static_feature_columns:
            return None
        values: List[float] = []
        meta = metadata or {}
        for col in self.static_feature_columns:
            key = str(col)
            candidates = {
                key,
                key.lower(),
                key.upper(),
            }
            value = None
            for c in candidates:
                if c in meta:
                    value = meta[c]
                    break
            if value is None and key.lower() == "gender" and "sex" in meta:
                value = meta.get("sex")
            if isinstance(value, str):
                if value.lower() in {"male", "m"}:
                    value = 1
                elif value.lower() in {"female", "f"}:
                    value = 0
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                values.append(0.0)
        return values

    def predict_outputs(
        self,
        data_points: List[CPETDataPoint],
        *,
        static_features: Optional[Dict[str, Any]] = None,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not data_points:
            return {
                "probs": [],
                "time_pred": None,
                "time_pred_index": None,
                "vo2_pred": None,
            }

        if self.model is None or not HAS_TORCH or len(data_points) < self.min_points_for_model:
            probs = self._rule_based_prediction(data_points)
            return {
                "probs": probs,
                "time_pred": None,
                "time_pred_index": None,
                "vo2_pred": None,
            }

        features = np.array(
            [p.to_feature_vector(self.feature_names) for p in data_points],
            dtype=np.float32,
        )
        if self.normalization == "per_exam" and features.shape[0] >= self.norm_min_points:
            mean = np.nanmean(features, axis=0)
            std = np.nanstd(features, axis=0)
            std = np.where(std == 0, 1.0, std)
            features = (features - mean) / std
        x = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)
        key_padding_mask = torch.zeros((1, features.shape[0]), dtype=torch.bool, device=self.device)

        static_vec = self.build_static_feature_vector(static_features)
        static_tensor = None
        if static_vec is not None:
            static_tensor = torch.tensor([static_vec], dtype=torch.float32, device=self.device)

        with torch.no_grad():
            outputs = self.model(
                x,
                key_padding_mask=key_padding_mask,
                static_features=static_tensor,
                mode=mode or self.eval_mode,
            )

        logits = outputs.get("logits")
        probs_tensor = torch.sigmoid(logits) if logits is not None else None
        probs = probs_tensor.squeeze(0).detach().cpu().numpy().tolist() if probs_tensor is not None else []

        time_pred_idx = outputs.get("time_pred")
        time_pred_index = None
        if time_pred_idx is not None:
            time_pred_index = float(time_pred_idx.squeeze().detach().cpu().item())

        vo2_pred = outputs.get("vo2_pred")
        vo2_pred_val = None
        if vo2_pred is not None:
            vo2_seq = vo2_pred.squeeze(0).detach().cpu().numpy().tolist()
            if vo2_seq:
                if time_pred_index is not None:
                    idx = int(round(max(0.0, min(time_pred_index, len(vo2_seq) - 1))))
                    vo2_pred_val = float(vo2_seq[idx])
                else:
                    vo2_pred_val = float(vo2_seq[-1])

        return {
            "probs": probs,
            "time_pred": self.decode_time_pred(time_pred_index, [p.timestamp for p in data_points]),
            "time_pred_index": time_pred_index,
            "vo2_pred": vo2_pred_val,
        }

    @staticmethod
    def decode_time_pred(time_pred_index: Optional[float], times: List[float]) -> Optional[float]:
        if time_pred_index is None or not times:
            return None
        max_idx = max(len(times) - 1, 0)
        clamped = min(max(time_pred_index, 0.0), float(max_idx))
        lower = int(np.floor(clamped))
        upper = min(lower + 1, max_idx)
        frac = clamped - lower
        if lower == upper:
            return float(times[lower])
        return float(times[lower] + frac * (times[upper] - times[lower]))
    
    def predict_sequence(
        self,
        data_points: List[CPETDataPoint],
    ) -> List[float]:
        """
        预测序列的 AT 概率
        
        Args:
            data_points: CPET 数据点序列
            
        Returns:
            List[float]: 每个时刻的 AT 概率
        """
        outputs = self.predict_outputs(data_points)
        return outputs.get("probs", [])
    
    def _rule_based_prediction(
        self,
        data_points: List[CPETDataPoint],
    ) -> List[float]:
        """
        基于规则的简单预测（用于演示或模型不可用时）
        
        使用 V-slope 方法的简化版本
        """
        probs = []
        
        for i, point in enumerate(data_points):
            # 基于 RER 的简单估计
            # RER > 1.0 通常表示已过 AT
            if point.rer >= 1.1:
                prob = 0.9
            elif point.rer >= 1.0:
                prob = 0.7
            elif point.rer >= 0.95:
                prob = 0.5
            elif point.rer >= 0.85:
                prob = 0.3
            else:
                prob = 0.1
            
            # 考虑 VE/VO2 斜率变化
            if i >= 10:
                recent_ve = [p.ve for p in data_points[i-10:i+1]]
                recent_vo2 = [p.vo2 for p in data_points[i-10:i+1]]
                
                # 计算斜率
                if len(set(recent_vo2)) > 1:
                    slope = (recent_ve[-1] - recent_ve[0]) / (recent_vo2[-1] - recent_vo2[0] + 1e-6)
                    # VE/VO2 斜率增加表示接近 AT
                    if slope > 30:
                        prob = min(1.0, prob + 0.2)
            
            probs.append(prob)
        
        return probs
    
    def create_session(
        self,
        threshold: float = 0.7,
        persistence: int = 3,
    ) -> ATOnlineSession:
        """创建在线预测会话"""
        return ATOnlineSession(
            threshold=threshold,
            persistence=persistence,
        )
