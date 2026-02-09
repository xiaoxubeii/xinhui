# -*- coding: utf-8 -*-
"""
CPET 专业计算器

提供 CPET 相关的核心计算功能。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class WeberClass(Enum):
    """Weber 心功能分级"""
    A = "A"  # 轻度或无损害
    B = "B"  # 轻中度损害
    C = "C"  # 中重度损害
    D = "D"  # 重度损害


@dataclass
class WeberResult:
    """Weber 分级结果"""
    grade: WeberClass
    vo2_peak: float
    description: str
    prognosis: str


def calculate_weber_class(vo2_peak: float) -> WeberResult:
    """
    根据 VO2peak 计算 Weber 心功能分级

    Args:
        vo2_peak: 峰值摄氧量 (ml/kg/min)

    Returns:
        WeberResult: 包含分级、描述和预后信息

    Reference:
        Weber KT, Janicki JS. Cardiopulmonary exercise testing. 1986.
    """
    if vo2_peak > 20:
        return WeberResult(
            grade=WeberClass.A,
            vo2_peak=vo2_peak,
            description="A级 - 轻度或无心功能损害",
            prognosis="预后良好，1年生存率 >95%"
        )
    elif vo2_peak > 16:
        return WeberResult(
            grade=WeberClass.B,
            vo2_peak=vo2_peak,
            description="B级 - 轻中度心功能损害",
            prognosis="预后较好，需定期随访"
        )
    elif vo2_peak > 10:
        return WeberResult(
            grade=WeberClass.C,
            vo2_peak=vo2_peak,
            description="C级 - 中重度心功能损害",
            prognosis="预后欠佳，建议强化治疗"
        )
    else:
        return WeberResult(
            grade=WeberClass.D,
            vo2_peak=vo2_peak,
            description="D级 - 重度心功能损害",
            prognosis="预后不良，考虑心脏移植评估（VO2peak <14 为移植候选标准）"
        )


def calculate_bmi(weight_kg: float, height_cm: float) -> dict:
    """
    计算体质指数 (BMI)

    Args:
        weight_kg: 体重 (kg)
        height_cm: 身高 (cm)

    Returns:
        dict: BMI 值和分类
    """
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)

    if bmi < 18.5:
        category = "偏瘦"
        risk = "营养不良风险"
    elif bmi < 24:
        category = "正常"
        risk = "健康范围"
    elif bmi < 28:
        category = "超重"
        risk = "心血管风险轻度增加"
    else:
        category = "肥胖"
        risk = "心血管风险显著增加"

    return {
        "bmi": round(bmi, 1),
        "category": category,
        "risk": risk,
        "weight_kg": weight_kg,
        "height_cm": height_cm,
    }


def calculate_predicted_hr_max(age: int, method: str = "tanaka") -> dict:
    """
    计算预测最大心率

    Args:
        age: 年龄
        method: 计算方法
            - "traditional": 220 - age
            - "tanaka": 208 - 0.7 × age (推荐)
            - "gellish": 207 - 0.7 × age

    Returns:
        dict: 预测最大心率和计算方法
    """
    methods = {
        "traditional": 220 - age,
        "tanaka": 208 - 0.7 * age,
        "gellish": 207 - 0.7 * age,
    }

    if method not in methods:
        method = "tanaka"

    hr_max = methods[method]

    return {
        "predicted_hr_max": round(hr_max),
        "method": method,
        "formula": {
            "traditional": "220 - age",
            "tanaka": "208 - 0.7 × age",
            "gellish": "207 - 0.7 × age",
        }[method],
        "age": age,
        "note": "实测 HRmax 优于预测值，建议以 CPET 实测为准"
    }


def calculate_target_hr_zone(
    hr_max: int,
    hr_rest: int,
    intensity_low: float = 0.5,
    intensity_high: float = 0.7,
    method: str = "karvonen"
) -> dict:
    """
    计算目标心率区间

    Args:
        hr_max: 最大心率
        hr_rest: 静息心率
        intensity_low: 强度下限 (0-1)
        intensity_high: 强度上限 (0-1)
        method: 计算方法
            - "karvonen": 心率储备法 (推荐)
            - "percentage": 最大心率百分比法

    Returns:
        dict: 目标心率区间
    """
    if method == "karvonen":
        # Karvonen 公式: THR = (HRmax - HRrest) × intensity + HRrest
        hrr = hr_max - hr_rest
        target_low = hrr * intensity_low + hr_rest
        target_high = hrr * intensity_high + hr_rest
        formula = "THR = (HRmax - HRrest) × intensity% + HRrest"
    else:
        # 最大心率百分比法
        target_low = hr_max * intensity_low
        target_high = hr_max * intensity_high
        formula = "THR = HRmax × intensity%"

    return {
        "target_hr_low": round(target_low),
        "target_hr_high": round(target_high),
        "target_hr_range": f"{round(target_low)}-{round(target_high)} bpm",
        "intensity_range": f"{int(intensity_low*100)}-{int(intensity_high*100)}%",
        "method": method,
        "formula": formula,
        "hr_max": hr_max,
        "hr_rest": hr_rest,
    }


def calculate_hrr_target(
    hr_max: int,
    hr_rest: int,
    intensity: float
) -> dict:
    """
    使用心率储备法计算特定强度的目标心率

    Args:
        hr_max: 最大心率
        hr_rest: 静息心率
        intensity: 目标强度 (0-1)

    Returns:
        dict: 目标心率
    """
    hrr = hr_max - hr_rest
    target_hr = hrr * intensity + hr_rest

    # 强度分类
    if intensity < 0.4:
        intensity_category = "极低强度"
    elif intensity < 0.5:
        intensity_category = "低强度"
    elif intensity < 0.7:
        intensity_category = "中等强度"
    elif intensity < 0.85:
        intensity_category = "高强度"
    else:
        intensity_category = "极高强度"

    return {
        "target_hr": round(target_hr),
        "intensity": intensity,
        "intensity_percent": f"{int(intensity*100)}%",
        "intensity_category": intensity_category,
        "heart_rate_reserve": hrr,
        "hr_max": hr_max,
        "hr_rest": hr_rest,
    }


def calculate_mets(vo2: float, weight_kg: Optional[float] = None) -> dict:
    """
    计算代谢当量 (METs)

    Args:
        vo2: 摄氧量
            - 如果 weight_kg 为 None，假设 vo2 单位为 ml/kg/min
            - 如果提供 weight_kg，假设 vo2 单位为 ml/min (绝对值)
        weight_kg: 体重 (kg)，可选

    Returns:
        dict: METs 值和活动强度分类

    Note:
        1 MET = 3.5 ml/kg/min (静息代谢率)
    """
    if weight_kg is not None:
        # 绝对 VO2 转换为相对 VO2
        vo2_relative = vo2 / weight_kg
    else:
        vo2_relative = vo2

    mets = vo2_relative / 3.5

    # METs 强度分类
    if mets < 2:
        category = "静息/极轻活动"
        examples = "坐着、站立、缓慢步行"
    elif mets < 3:
        category = "轻度活动"
        examples = "慢走 (3-4 km/h)、轻度家务"
    elif mets < 6:
        category = "中等强度活动"
        examples = "快走 (5-6 km/h)、骑车、游泳"
    elif mets < 9:
        category = "高强度活动"
        examples = "慢跑、爬楼梯、有氧操"
    else:
        category = "极高强度活动"
        examples = "快跑、竞技运动"

    return {
        "mets": round(mets, 1),
        "vo2_ml_kg_min": round(vo2_relative, 1),
        "category": category,
        "examples": examples,
    }


def calculate_vo2_from_mets(mets: float) -> dict:
    """
    从 METs 计算 VO2

    Args:
        mets: 代谢当量

    Returns:
        dict: VO2 值 (ml/kg/min)
    """
    vo2 = mets * 3.5

    return {
        "vo2_ml_kg_min": round(vo2, 1),
        "mets": mets,
        "formula": "VO2 = METs × 3.5 ml/kg/min"
    }


def calculate_predicted_vo2max(
    age: int,
    sex: str,
    weight_kg: Optional[float] = None,
    height_cm: Optional[float] = None,
    method: str = "wasserman"
) -> dict:
    """
    计算预测 VO2max

    Args:
        age: 年龄
        sex: 性别 ("male" 或 "female")
        weight_kg: 体重 (kg)
        height_cm: 身高 (cm)
        method: 计算方法
            - "wasserman": Wasserman 公式
            - "jones": Jones 公式

    Returns:
        dict: 预测 VO2max
    """
    sex_lower = sex.lower()

    if method == "wasserman" and weight_kg:
        # Wasserman 公式
        if sex_lower == "male":
            vo2max = (weight_kg * (50.72 - 0.372 * age))
        else:
            vo2max = (weight_kg * (22.78 - 0.17 * age))
        formula = "Wasserman"
        unit = "ml/min"
        vo2max_relative = vo2max / weight_kg if weight_kg else None
    elif method == "jones" and height_cm:
        # Jones 公式 (基于身高)
        if sex_lower == "male":
            vo2max = (height_cm - age) * 20
        else:
            vo2max = (height_cm - age) * 14
        formula = "Jones"
        unit = "ml/min"
        vo2max_relative = vo2max / weight_kg if weight_kg else None
    else:
        # 简化公式 (基于年龄和性别)
        if sex_lower == "male":
            vo2max_relative = 60 - 0.55 * age
        else:
            vo2max_relative = 48 - 0.37 * age
        vo2max = vo2max_relative * weight_kg if weight_kg else None
        formula = "Age-based"
        unit = "ml/kg/min"

    return {
        "predicted_vo2max_absolute": round(vo2max) if vo2max else None,
        "predicted_vo2max_relative": round(vo2max_relative, 1) if vo2max_relative else None,
        "unit": unit,
        "formula": formula,
        "age": age,
        "sex": sex,
        "note": "预测值仅供参考，实测值更准确"
    }


def calculate_ve_vco2_slope(
    ve_values: list,
    vco2_values: list
) -> dict:
    """
    计算 VE/VCO2 斜率

    Args:
        ve_values: 分钟通气量序列 (L/min)
        vco2_values: 二氧化碳排出量序列 (L/min)

    Returns:
        dict: VE/VCO2 斜率和临床解读
    """
    if len(ve_values) != len(vco2_values) or len(ve_values) < 2:
        return {"error": "数据点数量不足或不匹配"}

    # 简单线性回归计算斜率
    n = len(ve_values)
    sum_x = sum(vco2_values)
    sum_y = sum(ve_values)
    sum_xy = sum(x * y for x, y in zip(vco2_values, ve_values))
    sum_x2 = sum(x ** 2 for x in vco2_values)

    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)

    # 临床解读
    if slope < 30:
        interpretation = "正常"
        prognosis = "通气效率正常"
    elif slope < 34:
        interpretation = "临界值"
        prognosis = "通气效率轻度下降，需关注"
    elif slope < 45:
        interpretation = "异常"
        prognosis = "通气效率明显下降，心衰预后不良指标"
    else:
        interpretation = "严重异常"
        prognosis = "严重通气-灌注失匹配，预后差"

    return {
        "ve_vco2_slope": round(slope, 1),
        "interpretation": interpretation,
        "prognosis": prognosis,
        "reference": {
            "normal": "<30",
            "borderline": "30-34",
            "abnormal": ">34",
            "severe": ">45"
        },
        "data_points": n,
    }


def calculate_oxygen_pulse(vo2: float, hr: int) -> dict:
    """
    计算氧脉搏 (O2 Pulse)

    Args:
        vo2: 摄氧量 (ml/min)
        hr: 心率 (bpm)

    Returns:
        dict: 氧脉搏值和解读

    Note:
        O2 Pulse = VO2 / HR，反映每搏心输出量
    """
    o2_pulse = vo2 / hr

    # 正常参考值（简化）
    if o2_pulse > 15:
        interpretation = "正常偏高"
        note = "每搏量充足"
    elif o2_pulse > 10:
        interpretation = "正常"
        note = "心功能正常"
    elif o2_pulse > 8:
        interpretation = "偏低"
        note = "每搏量可能受限"
    else:
        interpretation = "明显降低"
        note = "提示心功能受损或每搏量受限"

    return {
        "o2_pulse": round(o2_pulse, 1),
        "unit": "ml/beat",
        "interpretation": interpretation,
        "note": note,
        "vo2_ml_min": vo2,
        "hr": hr,
        "formula": "O2 Pulse = VO2 / HR"
    }


def calculate_breathing_reserve(ve_max: float, mvv: float) -> dict:
    """
    计算呼吸储备 (Breathing Reserve)

    Args:
        ve_max: 最大分钟通气量 (L/min)
        mvv: 最大自主通气量 (L/min)，可用 FEV1 × 40 估算

    Returns:
        dict: 呼吸储备和解读
    """
    br = (1 - ve_max / mvv) * 100
    ve_mvv_ratio = ve_max / mvv * 100

    if br > 30:
        interpretation = "正常"
        note = "通气储备充足，运动受限非呼吸因素"
    elif br > 15:
        interpretation = "轻度降低"
        note = "通气储备轻度受限"
    else:
        interpretation = "明显降低"
        note = "通气储备不足，可能存在通气受限"

    return {
        "breathing_reserve": round(br, 1),
        "breathing_reserve_percent": f"{round(br, 1)}%",
        "ve_mvv_ratio": round(ve_mvv_ratio, 1),
        "interpretation": interpretation,
        "note": note,
        "ve_max": ve_max,
        "mvv": mvv,
        "reference": {
            "normal": ">30%",
            "mild_reduction": "15-30%",
            "significant_reduction": "<15%"
        }
    }


def calculate_anaerobic_threshold_ratio(at_vo2: float, vo2_peak: float) -> dict:
    """
    计算无氧阈占峰值摄氧量的比例

    Args:
        at_vo2: 无氧阈时的 VO2 (ml/kg/min)
        vo2_peak: 峰值 VO2 (ml/kg/min)

    Returns:
        dict: AT/VO2peak 比值和解读
    """
    ratio = at_vo2 / vo2_peak * 100

    if ratio > 60:
        interpretation = "偏高"
        fitness = "有氧能力较好，可能为训练有素者"
    elif ratio > 50:
        interpretation = "正常"
        fitness = "有氧代谢能力正常"
    elif ratio > 40:
        interpretation = "偏低"
        fitness = "有氧代谢能力下降"
    else:
        interpretation = "明显降低"
        fitness = "有氧代谢能力明显受损"

    return {
        "at_vo2peak_ratio": round(ratio, 1),
        "at_vo2peak_percent": f"{round(ratio, 1)}%",
        "interpretation": interpretation,
        "fitness_level": fitness,
        "at_vo2": at_vo2,
        "vo2_peak": vo2_peak,
        "reference": {
            "trained": ">60%",
            "normal": "50-60%",
            "reduced": "40-50%",
            "impaired": "<40%"
        }
    }
