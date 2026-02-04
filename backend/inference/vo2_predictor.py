# -*- coding: utf-8 -*-
"""
VO2 Peak 预测器

在 AT 时刻预测患者的 VO2 Peak。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple
import numpy as np

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class WeberClass(Enum):
    """Weber 心功能分级"""
    A = "A"  # VO2 peak > 20 ml/kg/min, 轻度或无心功能受损
    B = "B"  # VO2 peak 16-20 ml/kg/min, 轻至中度心功能受损
    C = "C"  # VO2 peak 10-16 ml/kg/min, 中至重度心功能受损
    D = "D"  # VO2 peak < 10 ml/kg/min, 重度心功能受损


@dataclass
class VO2PeakPrediction:
    """VO2 Peak 预测结果"""
    predicted_vo2_peak: float           # 预测值 (ml/kg/min)
    confidence_interval: Tuple[float, float]  # 95% CI
    weber_class: WeberClass             # Weber 分级
    weber_description: str              # 分级描述
    percentile: Optional[float] = None  # 同龄同性别百分位
    prediction_confidence: float = 0.8  # 预测置信度


class VO2PeakPredictor:
    """VO2 Peak 预测器"""
    
    # Weber 分级标准
    WEBER_THRESHOLDS = {
        WeberClass.A: (20, float('inf')),
        WeberClass.B: (16, 20),
        WeberClass.C: (10, 16),
        WeberClass.D: (0, 10),
    }
    
    WEBER_DESCRIPTIONS = {
        WeberClass.A: "轻度或无心功能受损，运动耐量正常或接近正常",
        WeberClass.B: "轻至中度心功能受损，运动耐量轻度下降",
        WeberClass.C: "中至重度心功能受损，运动耐量明显下降",
        WeberClass.D: "重度心功能受损，运动耐量严重下降",
    }
    
    # 正常人群 VO2 peak 参考值 (ml/kg/min)
    # 按年龄和性别分层
    REFERENCE_VALUES = {
        "male": {
            (20, 30): {"mean": 45, "std": 8},
            (30, 40): {"mean": 42, "std": 8},
            (40, 50): {"mean": 38, "std": 7},
            (50, 60): {"mean": 34, "std": 7},
            (60, 70): {"mean": 30, "std": 6},
            (70, 80): {"mean": 26, "std": 5},
            (80, 100): {"mean": 22, "std": 5},
        },
        "female": {
            (20, 30): {"mean": 38, "std": 7},
            (30, 40): {"mean": 35, "std": 7},
            (40, 50): {"mean": 32, "std": 6},
            (50, 60): {"mean": 28, "std": 6},
            (60, 70): {"mean": 25, "std": 5},
            (70, 80): {"mean": 22, "std": 5},
            (80, 100): {"mean": 19, "std": 4},
        },
    }
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
    ):
        """
        初始化预测器
        
        Args:
            model_path: 模型权重路径
            device: 推理设备
        """
        self.model_path = model_path
        self.device = device
        self.model = None
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str) -> None:
        """加载模型"""
        if not HAS_TORCH:
            raise RuntimeError("PyTorch not installed")
        # 实际模型加载逻辑
        pass
    
    def predict(
        self,
        vo2_at: float,
        hr_at: float,
        work_rate_at: float,
        age: int,
        sex: str,
        weight_kg: float,
        height_cm: float,
        vo2_sequence: Optional[List[float]] = None,
        hr_sequence: Optional[List[float]] = None,
    ) -> VO2PeakPrediction:
        """
        预测 VO2 Peak
        
        Args:
            vo2_at: AT 时刻的 VO2 (ml/kg/min)
            hr_at: AT 时刻的心率
            work_rate_at: AT 时刻的功率
            age: 年龄
            sex: 性别 ("male" or "female")
            weight_kg: 体重 (kg)
            height_cm: 身高 (cm)
            vo2_sequence: VO2 时间序列（可选，用于更精确预测）
            hr_sequence: 心率时间序列（可选）
            
        Returns:
            VO2PeakPrediction: 预测结果
        """
        # 如果有模型，使用模型预测
        if self.model is not None:
            predicted = self._model_predict(
                vo2_at, hr_at, work_rate_at, age, sex, weight_kg, height_cm,
                vo2_sequence, hr_sequence
            )
        else:
            # 使用经验公式预测
            predicted = self._empirical_predict(
                vo2_at, hr_at, work_rate_at, age, sex
            )
        
        # 计算置信区间
        ci = self._calculate_confidence_interval(predicted, vo2_at)
        
        # 确定 Weber 分级
        weber_class = self._classify_weber(predicted)
        
        # 计算百分位
        percentile = self._calculate_percentile(predicted, age, sex)
        
        # 计算预测置信度
        confidence = self._calculate_prediction_confidence(
            vo2_at, hr_at, vo2_sequence
        )
        
        return VO2PeakPrediction(
            predicted_vo2_peak=round(predicted, 1),
            confidence_interval=(round(ci[0], 1), round(ci[1], 1)),
            weber_class=weber_class,
            weber_description=self.WEBER_DESCRIPTIONS[weber_class],
            percentile=percentile,
            prediction_confidence=confidence,
        )
    
    def _model_predict(
        self,
        vo2_at: float,
        hr_at: float,
        work_rate_at: float,
        age: int,
        sex: str,
        weight_kg: float,
        height_cm: float,
        vo2_sequence: Optional[List[float]],
        hr_sequence: Optional[List[float]],
    ) -> float:
        """使用模型预测"""
        # 实际模型推理逻辑
        # 这里返回经验预测作为占位
        return self._empirical_predict(vo2_at, hr_at, work_rate_at, age, sex)
    
    def _empirical_predict(
        self,
        vo2_at: float,
        hr_at: float,
        work_rate_at: float,
        age: int,
        sex: str,
    ) -> float:
        """
        使用经验公式预测 VO2 Peak
        
        基于 AT 通常发生在 50-60% VO2 peak 的经验
        """
        # 方法1: 基于 VO2 at AT
        # AT 通常发生在 50-60% VO2 peak
        # 对于心脏病患者，可能更接近 40-50%
        vo2_peak_estimate1 = vo2_at / 0.55  # 假设 AT 在 55% VO2 peak
        
        # 方法2: 基于心率储备
        # 预测最大心率
        hr_max_pred = 220 - age
        if sex == "female":
            hr_max_pred = 206 - 0.88 * age
        
        # 假设 AT 时心率约为最大心率的 70-80%
        hr_ratio = hr_at / hr_max_pred
        if hr_ratio > 0:
            # 线性外推
            vo2_peak_estimate2 = vo2_at / hr_ratio
        else:
            vo2_peak_estimate2 = vo2_peak_estimate1
        
        # 综合两种方法
        predicted = 0.6 * vo2_peak_estimate1 + 0.4 * vo2_peak_estimate2
        
        # 限制在合理范围内
        predicted = max(8, min(60, predicted))
        
        return predicted
    
    def _calculate_confidence_interval(
        self,
        predicted: float,
        vo2_at: float,
    ) -> Tuple[float, float]:
        """计算 95% 置信区间"""
        # 基于预测误差的经验估计
        # 典型 MAE 约为 2-3 ml/kg/min
        std_error = 2.5
        
        # 95% CI = predicted ± 1.96 * SE
        margin = 1.96 * std_error
        
        return (predicted - margin, predicted + margin)
    
    def _classify_weber(self, vo2_peak: float) -> WeberClass:
        """Weber 分级"""
        for weber_class, (low, high) in self.WEBER_THRESHOLDS.items():
            if low <= vo2_peak < high:
                return weber_class
        return WeberClass.D
    
    def _calculate_percentile(
        self,
        vo2_peak: float,
        age: int,
        sex: str,
    ) -> Optional[float]:
        """计算同龄同性别百分位"""
        sex_key = sex.lower()
        if sex_key not in self.REFERENCE_VALUES:
            return None
        
        # 找到对应年龄段
        ref = None
        for age_range, values in self.REFERENCE_VALUES[sex_key].items():
            if age_range[0] <= age < age_range[1]:
                ref = values
                break
        
        if ref is None:
            return None
        
        # 计算 z-score
        z = (vo2_peak - ref["mean"]) / ref["std"]
        
        # 转换为百分位 (使用正态分布近似)
        from math import erf, sqrt
        percentile = 0.5 * (1 + erf(z / sqrt(2))) * 100
        
        return round(percentile, 1)
    
    def _calculate_prediction_confidence(
        self,
        vo2_at: float,
        hr_at: float,
        vo2_sequence: Optional[List[float]],
    ) -> float:
        """计算预测置信度"""
        confidence = 0.7  # 基础置信度
        
        # 如果有完整序列，置信度更高
        if vo2_sequence and len(vo2_sequence) >= 30:
            confidence += 0.1
        
        # 如果 VO2 at AT 在合理范围内
        if 8 <= vo2_at <= 30:
            confidence += 0.1
        
        # 如果心率在合理范围内
        if 80 <= hr_at <= 180:
            confidence += 0.05
        
        return min(0.95, confidence)
    
    def get_clinical_interpretation(
        self,
        prediction: VO2PeakPrediction,
        age: int,
        diagnosis: Optional[str] = None,
    ) -> str:
        """
        生成临床解读
        
        Args:
            prediction: 预测结果
            age: 年龄
            diagnosis: 诊断
            
        Returns:
            str: 临床解读文本
        """
        lines = []
        
        # VO2 Peak 值
        lines.append(
            f"预测 VO2 Peak: {prediction.predicted_vo2_peak} ml/kg/min "
            f"(95% CI: {prediction.confidence_interval[0]}-{prediction.confidence_interval[1]})"
        )
        
        # Weber 分级
        lines.append(f"Weber 分级: {prediction.weber_class.value} 级")
        lines.append(f"  - {prediction.weber_description}")
        
        # 百分位
        if prediction.percentile is not None:
            if prediction.percentile >= 50:
                comparison = "高于"
            else:
                comparison = "低于"
            lines.append(
                f"与同龄同性别人群相比: {comparison}平均水平 "
                f"(第 {prediction.percentile:.0f} 百分位)"
            )
        
        # 临床建议
        lines.append("")
        lines.append("临床建议:")
        
        if prediction.weber_class == WeberClass.A:
            lines.append("  - 心肺功能良好，可进行常规运动康复")
            lines.append("  - 建议中高强度有氧运动")
        elif prediction.weber_class == WeberClass.B:
            lines.append("  - 心肺功能轻度受损，建议规律运动康复")
            lines.append("  - 建议中等强度有氧运动，逐渐增加强度")
        elif prediction.weber_class == WeberClass.C:
            lines.append("  - 心肺功能明显受损，需要监护下运动康复")
            lines.append("  - 建议低至中等强度有氧运动")
            lines.append("  - 密切监测症状和心电图")
        else:
            lines.append("  - 心肺功能严重受损，需要严密监护")
            lines.append("  - 建议低强度运动，以日常活动为主")
            lines.append("  - 考虑心脏康复专科评估")
        
        return "\n".join(lines)
