# -*- coding: utf-8 -*-
"""
运动处方生成工具

提供基于 CPET 结果的运动处方生成功能。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum


class IntensityLevel(Enum):
    """运动强度等级"""
    VERY_LIGHT = "very_light"
    LIGHT = "light"
    MODERATE = "moderate"
    VIGOROUS = "vigorous"
    NEAR_MAXIMAL = "near_maximal"


@dataclass
class HRZone:
    """心率区间"""
    zone: int
    name: str
    hr_low: int
    hr_high: int
    intensity_low: float
    intensity_high: float
    description: str
    benefit: str


def generate_hr_prescription(
    hr_max: int,
    hr_rest: int,
    hr_at: Optional[int] = None,
    risk_level: str = "low",
    use_at_based: bool = True,
) -> dict:
    """
    生成基于心率的运动处方

    Args:
        hr_max: 最大心率 (实测)
        hr_rest: 静息心率
        hr_at: 无氧阈心率 (可选)
        risk_level: 风险等级 ("low", "moderate", "high")
        use_at_based: 是否使用 AT 心率作为基准

    Returns:
        dict: 心率处方
    """
    hrr = hr_max - hr_rest

    # 根据风险等级调整强度范围
    intensity_ranges = {
        "low": {"min": 0.50, "max": 0.80, "optimal_min": 0.60, "optimal_max": 0.75},
        "moderate": {"min": 0.40, "max": 0.70, "optimal_min": 0.50, "optimal_max": 0.65},
        "high": {"min": 0.30, "max": 0.60, "optimal_min": 0.40, "optimal_max": 0.55},
    }

    ranges = intensity_ranges.get(risk_level, intensity_ranges["moderate"])

    # 计算心率区间 (Karvonen 公式)
    def calc_hr(intensity: float) -> int:
        return round(hrr * intensity + hr_rest)

    # 生成 5 个心率区间
    zones: List[HRZone] = [
        HRZone(
            zone=1,
            name="恢复区",
            hr_low=calc_hr(0.50),
            hr_high=calc_hr(0.60),
            intensity_low=0.50,
            intensity_high=0.60,
            description="非常轻松，可正常交谈",
            benefit="促进恢复，热身放松"
        ),
        HRZone(
            zone=2,
            name="有氧基础区",
            hr_low=calc_hr(0.60),
            hr_high=calc_hr(0.70),
            intensity_low=0.60,
            intensity_high=0.70,
            description="轻松，可持续交谈",
            benefit="提高有氧基础，燃脂"
        ),
        HRZone(
            zone=3,
            name="有氧耐力区",
            hr_low=calc_hr(0.70),
            hr_high=calc_hr(0.80),
            intensity_low=0.70,
            intensity_high=0.80,
            description="中等吃力，交谈略困难",
            benefit="提高心肺耐力"
        ),
        HRZone(
            zone=4,
            name="无氧阈区",
            hr_low=calc_hr(0.80),
            hr_high=calc_hr(0.90),
            intensity_low=0.80,
            intensity_high=0.90,
            description="吃力，难以交谈",
            benefit="提高乳酸阈值"
        ),
        HRZone(
            zone=5,
            name="最大强度区",
            hr_low=calc_hr(0.90),
            hr_high=hr_max,
            intensity_low=0.90,
            intensity_high=1.00,
            description="非常吃力，无法交谈",
            benefit="提高最大摄氧量"
        ),
    ]

    # 推荐训练区间
    target_hr_low = calc_hr(ranges["optimal_min"])
    target_hr_high = calc_hr(ranges["optimal_max"])

    # 如果有 AT 心率，使用 AT 作为参考
    at_based_prescription = None
    if hr_at and use_at_based:
        at_based_prescription = {
            "at_hr": hr_at,
            "below_at": {
                "hr_range": f"{hr_at - 20}-{hr_at - 5} bpm",
                "description": "低于无氧阈，有氧为主",
                "suitable_for": "长时间耐力训练、康复初期"
            },
            "at_zone": {
                "hr_range": f"{hr_at - 5}-{hr_at + 5} bpm",
                "description": "无氧阈附近，最佳训练区",
                "suitable_for": "提高有氧能力的最佳强度"
            },
            "above_at": {
                "hr_range": f"{hr_at + 5}-{hr_at + 20} bpm",
                "description": "高于无氧阈，无氧参与增加",
                "suitable_for": "间歇训练、提高乳酸耐受"
            },
        }

    return {
        "prescription": {
            "target_hr_low": target_hr_low,
            "target_hr_high": target_hr_high,
            "target_hr_range": f"{target_hr_low}-{target_hr_high} bpm",
            "intensity_range": f"{int(ranges['optimal_min']*100)}-{int(ranges['optimal_max']*100)}% HRR",
            "risk_level": risk_level,
        },
        "parameters": {
            "hr_max": hr_max,
            "hr_rest": hr_rest,
            "heart_rate_reserve": hrr,
            "hr_at": hr_at,
        },
        "zones": [
            {
                "zone": z.zone,
                "name": z.name,
                "hr_range": f"{z.hr_low}-{z.hr_high} bpm",
                "intensity": f"{int(z.intensity_low*100)}-{int(z.intensity_high*100)}%",
                "description": z.description,
                "benefit": z.benefit,
            }
            for z in zones
        ],
        "at_based_prescription": at_based_prescription,
        "method": "Karvonen (心率储备法)",
        "note": "建议以实测心率为准，RPE 作为辅助参考"
    }


def generate_exercise_intensity(
    vo2_peak: float,
    hr_max: int,
    hr_rest: int,
    hr_at: Optional[int] = None,
    vo2_at: Optional[float] = None,
    risk_level: str = "low",
) -> dict:
    """
    生成多维度运动强度处方

    Args:
        vo2_peak: 峰值摄氧量 (ml/kg/min)
        hr_max: 最大心率
        hr_rest: 静息心率
        hr_at: 无氧阈心率
        vo2_at: 无氧阈 VO2
        risk_level: 风险等级

    Returns:
        dict: 多维度强度处方
    """
    hrr = hr_max - hr_rest

    # 根据风险等级设定强度
    intensity_config = {
        "low": {
            "vo2_percent": (50, 80),
            "hrr_percent": (50, 80),
            "rpe": (11, 15),
            "description": "中等至较高强度"
        },
        "moderate": {
            "vo2_percent": (40, 70),
            "hrr_percent": (40, 70),
            "rpe": (11, 14),
            "description": "低至中等强度"
        },
        "high": {
            "vo2_percent": (30, 60),
            "hrr_percent": (30, 60),
            "rpe": (9, 13),
            "description": "低强度为主"
        },
    }

    config = intensity_config.get(risk_level, intensity_config["moderate"])

    # 计算各维度强度
    vo2_low = vo2_peak * config["vo2_percent"][0] / 100
    vo2_high = vo2_peak * config["vo2_percent"][1] / 100

    hr_low = round(hrr * config["hrr_percent"][0] / 100 + hr_rest)
    hr_high = round(hrr * config["hrr_percent"][1] / 100 + hr_rest)

    mets_low = vo2_low / 3.5
    mets_high = vo2_high / 3.5

    # 功率估算 (简化公式)
    # 功率 ≈ (VO2 - 7) × 体重 / 10.3 (仅供参考)

    result = {
        "risk_level": risk_level,
        "intensity_description": config["description"],
        "heart_rate": {
            "target_low": hr_low,
            "target_high": hr_high,
            "range": f"{hr_low}-{hr_high} bpm",
            "percent_hrr": f"{config['hrr_percent'][0]}-{config['hrr_percent'][1]}%",
        },
        "vo2": {
            "target_low": round(vo2_low, 1),
            "target_high": round(vo2_high, 1),
            "range": f"{round(vo2_low, 1)}-{round(vo2_high, 1)} ml/kg/min",
            "percent_peak": f"{config['vo2_percent'][0]}-{config['vo2_percent'][1]}%",
        },
        "mets": {
            "target_low": round(mets_low, 1),
            "target_high": round(mets_high, 1),
            "range": f"{round(mets_low, 1)}-{round(mets_high, 1)} METs",
        },
        "rpe": {
            "target_low": config["rpe"][0],
            "target_high": config["rpe"][1],
            "range": f"{config['rpe'][0]}-{config['rpe'][1]}",
            "description": _get_rpe_description(config["rpe"][0], config["rpe"][1]),
        },
        "talk_test": _get_talk_test(config["hrr_percent"][0], config["hrr_percent"][1]),
    }

    # 如果有 AT 数据，添加 AT 相关建议
    if hr_at:
        result["at_based"] = {
            "hr_at": hr_at,
            "recommended_range": f"{hr_at - 10}-{hr_at + 5} bpm",
            "note": "基于无氧阈的训练区间，安全有效"
        }

    if vo2_at:
        result["vo2_at"] = {
            "vo2_at": vo2_at,
            "at_percent_peak": round(vo2_at / vo2_peak * 100, 1),
        }

    return result


def _get_rpe_description(rpe_low: int, rpe_high: int) -> str:
    """获取 RPE 描述"""
    rpe_scale = {
        6: "完全不费力",
        7: "极其轻松",
        8: "极其轻松",
        9: "非常轻松",
        10: "非常轻松",
        11: "轻松",
        12: "轻松",
        13: "有些吃力",
        14: "有些吃力",
        15: "吃力",
        16: "吃力",
        17: "很吃力",
        18: "很吃力",
        19: "非常吃力",
        20: "筋疲力尽",
    }
    low_desc = rpe_scale.get(rpe_low, "")
    high_desc = rpe_scale.get(rpe_high, "")
    return f"{low_desc} 至 {high_desc}"


def _get_talk_test(intensity_low: float, intensity_high: float) -> dict:
    """获取谈话测试建议"""
    avg_intensity = (intensity_low + intensity_high) / 2

    if avg_intensity < 50:
        return {
            "description": "可轻松交谠，唱歌无困难",
            "intensity": "低强度"
        }
    elif avg_intensity < 70:
        return {
            "description": "可交谈但略喘，唱歌有困难",
            "intensity": "中等强度"
        }
    else:
        return {
            "description": "交谈困难，只能说短句",
            "intensity": "高强度"
        }


@dataclass
class ExerciseSession:
    """单次运动安排"""
    day: str
    type: str
    duration_min: int
    intensity: str
    hr_target: str
    notes: str


def generate_weekly_schedule(
    risk_level: str = "low",
    hr_max: int = 150,
    hr_rest: int = 70,
    hr_at: Optional[int] = None,
    include_resistance: bool = True,
    include_flexibility: bool = True,
    phase: str = "maintenance",  # "initial", "improvement", "maintenance"
) -> dict:
    """
    生成每周运动计划

    Args:
        risk_level: 风险等级
        hr_max: 最大心率
        hr_rest: 静息心率
        hr_at: 无氧阈心率
        include_resistance: 是否包含抗阻训练
        include_flexibility: 是否包含柔韧性训练
        phase: 康复阶段

    Returns:
        dict: 每周运动计划
    """
    hrr = hr_max - hr_rest

    # 根据风险等级和阶段设定参数
    phase_config = {
        "initial": {
            "low": {"freq": 3, "duration": 20, "intensity": (0.40, 0.55)},
            "moderate": {"freq": 3, "duration": 15, "intensity": (0.35, 0.50)},
            "high": {"freq": 3, "duration": 10, "intensity": (0.30, 0.45)},
        },
        "improvement": {
            "low": {"freq": 4, "duration": 30, "intensity": (0.50, 0.70)},
            "moderate": {"freq": 4, "duration": 25, "intensity": (0.45, 0.60)},
            "high": {"freq": 3, "duration": 20, "intensity": (0.35, 0.55)},
        },
        "maintenance": {
            "low": {"freq": 5, "duration": 45, "intensity": (0.55, 0.75)},
            "moderate": {"freq": 4, "duration": 35, "intensity": (0.50, 0.65)},
            "high": {"freq": 4, "duration": 25, "intensity": (0.40, 0.55)},
        },
    }

    config = phase_config.get(phase, phase_config["maintenance"]).get(
        risk_level, phase_config["maintenance"]["moderate"]
    )

    # 计算目标心率
    hr_low = round(hrr * config["intensity"][0] + hr_rest)
    hr_high = round(hrr * config["intensity"][1] + hr_rest)
    hr_target = f"{hr_low}-{hr_high} bpm"

    # 生成每周计划
    sessions: List[dict] = []
    days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    aerobic_days = config["freq"]
    resistance_days = 2 if include_resistance and risk_level != "high" else 0

    # 有氧运动安排
    aerobic_schedule = [0, 2, 4] if aerobic_days == 3 else [0, 1, 3, 4] if aerobic_days == 4 else [0, 1, 2, 3, 4]

    for i, day in enumerate(days):
        if i in aerobic_schedule[:aerobic_days]:
            sessions.append({
                "day": day,
                "type": "有氧运动",
                "activities": ["步行", "骑车", "游泳"],
                "duration": f"{config['duration']} 分钟",
                "intensity": f"{int(config['intensity'][0]*100)}-{int(config['intensity'][1]*100)}% HRR",
                "hr_target": hr_target,
                "structure": {
                    "warmup": "5-10 分钟低强度热身",
                    "main": f"{config['duration'] - 15} 分钟目标强度",
                    "cooldown": "5-10 分钟放松"
                }
            })
        elif include_resistance and i in [1, 4] and resistance_days > 0:
            sessions.append({
                "day": day,
                "type": "抗阻训练",
                "activities": ["弹力带", "哑铃", "器械"],
                "duration": "20-30 分钟",
                "intensity": "40-60% 1RM",
                "sets_reps": "1-2 组 × 10-15 次",
                "muscle_groups": ["上肢", "下肢", "核心"],
                "notes": "避免屏气，用力时呼气"
            })
        elif include_flexibility and i == 6:
            sessions.append({
                "day": day,
                "type": "柔韧性/休息",
                "activities": ["拉伸", "瑜伽", "太极"],
                "duration": "15-20 分钟",
                "notes": "轻度活动或完全休息"
            })
        else:
            sessions.append({
                "day": day,
                "type": "休息日",
                "activities": ["轻度活动"],
                "notes": "可进行轻度步行或拉伸"
            })

    # 每周总结
    weekly_summary = {
        "aerobic_sessions": aerobic_days,
        "aerobic_minutes": aerobic_days * config["duration"],
        "resistance_sessions": resistance_days,
        "total_active_days": aerobic_days + resistance_days,
        "rest_days": 7 - aerobic_days - resistance_days,
    }

    return {
        "phase": phase,
        "phase_description": {
            "initial": "初始阶段 (1-4周): 建立运动习惯，低强度起始",
            "improvement": "提高阶段 (5-16周): 逐步增加强度和时间",
            "maintenance": "维持阶段 (>16周): 保持运动习惯，灵活调整",
        }[phase],
        "risk_level": risk_level,
        "prescription_summary": {
            "frequency": f"{aerobic_days} 次/周有氧",
            "intensity": f"{int(config['intensity'][0]*100)}-{int(config['intensity'][1]*100)}% HRR",
            "time": f"{config['duration']} 分钟/次",
            "type": "步行、骑车、游泳等",
            "hr_target": hr_target,
        },
        "weekly_schedule": sessions,
        "weekly_summary": weekly_summary,
        "progression": {
            "frequency": "每 2-4 周可增加 1 次/周",
            "duration": "每 1-2 周可增加 5 分钟",
            "intensity": "每 2-4 周可增加 5% HRR",
            "note": "以无不适为前提，循序渐进"
        },
        "precautions": [
            "运动前后监测心率和血压",
            "出现胸痛、气短、头晕立即停止",
            "避免空腹和饱餐后运动",
            "保持适当水分摄入",
            "极端天气避免户外运动",
        ]
    }
