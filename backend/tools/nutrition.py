# -*- coding: utf-8 -*-
"""
营养方案生成工具

提供基于基础信息的能量、宏量营养素与餐次建议。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


def _mifflin_st_jeor(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Mifflin-St Jeor 公式计算 BMR"""
    sex = (sex or "").lower()
    if sex in {"male", "m", "man", "男"}:
        s = 5
    else:
        s = -161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + s


def _activity_factor(activity_level: str) -> float:
    mapping = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    return mapping.get(activity_level, mapping["moderate"])


def _goal_adjustment(tdee: float, goal: str) -> float:
    if goal == "loss":
        return max(-500.0, -0.15 * tdee)
    if goal == "gain":
        return min(300.0, 0.10 * tdee)
    return 0.0


def _macro_ratio(diet_type: str) -> Tuple[float, float, float]:
    ratios = {
        "balanced": (0.25, 0.50, 0.25),
        "low_carb": (0.30, 0.30, 0.40),
        "high_protein": (0.35, 0.40, 0.25),
        "mediterranean": (0.20, 0.45, 0.35),
        "dash": (0.20, 0.50, 0.30),
        "low_fat": (0.20, 0.60, 0.20),
        "low_sugar": (0.25, 0.45, 0.30),
        "keto": (0.25, 0.10, 0.65),
    }
    return ratios.get(diet_type, ratios["balanced"])


def _meal_distribution(meals_per_day: int) -> Tuple[List[str], List[float]]:
    if meals_per_day <= 3:
        return ["早餐", "午餐", "晚餐"], [0.30, 0.40, 0.30]
    if meals_per_day == 4:
        return ["早餐", "午餐", "晚餐", "加餐"], [0.25, 0.35, 0.25, 0.15]
    return ["早餐", "午餐", "晚餐", "上午加餐", "下午加餐"], [0.25, 0.25, 0.20, 0.15, 0.15]


def _meal_template(meal_type: str, diet_type: str) -> List[str]:
    is_low_carb = diet_type in {"low_carb", "keto"}
    is_high_protein = diet_type in {"high_protein"}
    base = []
    if "早餐" in meal_type:
        base = [
            "全谷物主食(燕麦/全麦)",
            "优质蛋白(鸡蛋/低脂奶/豆浆)",
            "蔬果(1份)",
            "坚果(少量)",
        ]
    elif "午餐" in meal_type:
        base = [
            "瘦肉/鱼/豆制品",
            "全谷物主食",
            "蔬菜(2份)",
            "健康脂肪(橄榄油/坚果)",
        ]
    elif "晚餐" in meal_type:
        base = [
            "鱼/禽/豆腐",
            "蔬菜(2份)",
            "全谷物主食(少量)",
            "汤/清炒为主",
        ]
    else:
        base = [
            "水果(1份)",
            "酸奶/坚果",
            "全谷物小点(少量)",
        ]

    if is_low_carb:
        base = [b.replace("全谷物主食", "低碳主食/非淀粉蔬菜") for b in base]
    if is_high_protein:
        base.insert(0, "高蛋白来源(鱼/禽/蛋/豆)")
    return base


def generate_nutrition_plan(
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: str,
    activity_level: str = "moderate",
    goal: str = "maintenance",
    diet_type: str = "balanced",
    meals_per_day: int = 3,
    target_kcal: Optional[float] = None,
    calorie_adjustment: Optional[float] = None,
    conditions: Optional[Dict[str, bool]] = None,
    allergies: Optional[List[str]] = None,
    preferences: Optional[List[str]] = None,
) -> dict:
    """
    生成营养方案（能量 + 宏量营养素 + 餐次建议）

    Args:
        weight_kg: 体重 (kg)
        height_cm: 身高 (cm)
        age: 年龄
        sex: 性别: male/female/other
        activity_level: 活动水平
        goal: 目标: loss/maintenance/gain
        diet_type: 饮食类型
        meals_per_day: 餐次数
        target_kcal: 目标热量（如提供则直接采用）
        calorie_adjustment: 热量调整（如提供则覆盖默认目标调整）
        conditions: 伴随疾病/风险，如 {"diabetes": True, "hypertension": False}
        allergies: 过敏原列表
        preferences: 饮食偏好列表
    """
    if target_kcal is None:
        bmr = _mifflin_st_jeor(weight_kg, height_cm, age, sex)
        tdee = bmr * _activity_factor(activity_level)
        adjustment = calorie_adjustment if calorie_adjustment is not None else _goal_adjustment(tdee, goal)
        target_kcal = tdee + adjustment
    else:
        bmr = _mifflin_st_jeor(weight_kg, height_cm, age, sex)
        tdee = bmr * _activity_factor(activity_level)

    target_kcal = round(float(target_kcal))
    protein_pct, carbs_pct, fat_pct = _macro_ratio(diet_type)

    protein_g = round(target_kcal * protein_pct / 4)
    carbs_g = round(target_kcal * carbs_pct / 4)
    fat_g = round(target_kcal * fat_pct / 9)

    conditions = conditions or {}
    low_sugar = bool(conditions.get("diabetes")) or diet_type in {"low_sugar", "low_carb", "keto"}
    low_salt = bool(conditions.get("hypertension")) or diet_type in {"dash"}
    high_fiber = bool(conditions.get("constipation")) or diet_type in {"dash", "mediterranean", "balanced"}

    fiber_g = round(target_kcal / 1000 * 14)
    sodium_mg = 2000 if low_salt else 2300
    water_ml = round(max(1500, min(3500, weight_kg * 30)))

    meal_types, ratios = _meal_distribution(max(3, min(5, meals_per_day)))
    meals = []
    remaining = target_kcal
    for idx, (meal_type, ratio) in enumerate(zip(meal_types, ratios)):
        kcal = round(target_kcal * ratio)
        if idx == len(meal_types) - 1:
            kcal = max(0, remaining)
        remaining -= kcal
        meals.append(
            {
                "meal_type": meal_type,
                "kcal": kcal,
                "foods": _meal_template(meal_type, diet_type),
            }
        )

    notes = []
    if allergies:
        notes.append(f"避免过敏原：{', '.join(allergies)}")
    if preferences:
        notes.append(f"偏好：{', '.join(preferences)}")

    summary = (
        f"{goal} 目标，{diet_type} 方案；"
        f"日能量 {target_kcal} kcal，蛋白 {protein_g}g / 碳水 {carbs_g}g / 脂肪 {fat_g}g。"
    )

    return {
        "summary": summary,
        "daily_targets": {
            "kcal": target_kcal,
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "fiber_g": fiber_g,
            "sodium_mg": sodium_mg,
            "water_ml": water_ml,
        },
        "macro_ratio": {
            "protein_pct": protein_pct,
            "carbs_pct": carbs_pct,
            "fat_pct": fat_pct,
        },
        "meals": meals,
        "constraints": {
            "low_sugar": low_sugar,
            "low_salt": low_salt,
            "high_fiber": high_fiber,
            "notes": "；".join(notes) if notes else None,
        },
        "parameters": {
            "bmr_kcal": round(bmr),
            "tdee_kcal": round(tdee),
            "activity_level": activity_level,
            "goal": goal,
            "diet_type": diet_type,
            "meals_per_day": len(meal_types),
        },
    }
