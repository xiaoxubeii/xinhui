# -*- coding: utf-8 -*-
"""
CPET 专业计算工具模块

提供 CPET 相关的专业计算功能，可被 Agent 调用。
"""

from .calculator import (
    calculate_weber_class,
    calculate_bmi,
    calculate_predicted_hr_max,
    calculate_target_hr_zone,
    calculate_hrr_target,
    calculate_mets,
    calculate_vo2_from_mets,
    calculate_predicted_vo2max,
    calculate_ve_vco2_slope,
    calculate_oxygen_pulse,
    calculate_breathing_reserve,
    calculate_anaerobic_threshold_ratio,
)

from .risk import (
    assess_exercise_risk,
    get_monitoring_recommendation,
    check_contraindications,
)

from .prescription import (
    generate_hr_prescription,
    generate_exercise_intensity,
    generate_weekly_schedule,
)

__all__ = [
    # Calculator
    "calculate_weber_class",
    "calculate_bmi",
    "calculate_predicted_hr_max",
    "calculate_target_hr_zone",
    "calculate_hrr_target",
    "calculate_mets",
    "calculate_vo2_from_mets",
    "calculate_predicted_vo2max",
    "calculate_ve_vco2_slope",
    "calculate_oxygen_pulse",
    "calculate_breathing_reserve",
    "calculate_anaerobic_threshold_ratio",
    # Risk
    "assess_exercise_risk",
    "get_monitoring_recommendation",
    "check_contraindications",
    # Prescription
    "generate_hr_prescription",
    "generate_exercise_intensity",
    "generate_weekly_schedule",
]
