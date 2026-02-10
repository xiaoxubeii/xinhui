# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) 工具定义

将 CPET 工具暴露为 MCP 格式，供 OpenCode Agent 调用。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List
from datetime import date, timedelta

# MCP 工具定义
MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "calculate_weber_class",
        "description": "根据 VO2peak 计算 Weber 心功能分级。输入峰值摄氧量(ml/kg/min)，返回分级(A/B/C/D)、描述和预后信息。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vo2_peak": {
                    "type": "number",
                    "description": "峰值摄氧量 (ml/kg/min)"
                }
            },
            "required": ["vo2_peak"]
        }
    },
    {
        "name": "calculate_bmi",
        "description": "计算体质指数(BMI)。输入体重和身高，返回BMI值和分类。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "weight_kg": {"type": "number", "description": "体重 (kg)"},
                "height_cm": {"type": "number", "description": "身高 (cm)"}
            },
            "required": ["weight_kg", "height_cm"]
        }
    },
    {
        "name": "calculate_target_hr_zone",
        "description": "计算目标心率区间。使用 Karvonen 心率储备法，根据最大心率、静息心率和目标强度计算训练心率范围。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hr_max": {"type": "integer", "description": "最大心率 (bpm)"},
                "hr_rest": {"type": "integer", "description": "静息心率 (bpm)"},
                "intensity_low": {"type": "number", "description": "强度下限 (0-1)，默认 0.5"},
                "intensity_high": {"type": "number", "description": "强度上限 (0-1)，默认 0.7"}
            },
            "required": ["hr_max", "hr_rest"]
        }
    },
    {
        "name": "calculate_mets",
        "description": "计算代谢当量(METs)。1 MET = 3.5 ml/kg/min。返回 METs 值和活动强度分类。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vo2": {"type": "number", "description": "摄氧量 (ml/kg/min)"}
            },
            "required": ["vo2"]
        }
    },
    {
        "name": "assess_exercise_risk",
        "description": "评估运动风险等级。基于 AACVPR 标准，综合运动试验结果和临床因素，返回低/中/高风险分层和建议。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "max_mets": {"type": "number", "description": "最大运动能力 (METs)"},
                "lvef": {"type": "number", "description": "左室射血分数 (%)"},
                "has_ischemia": {"type": "boolean", "description": "是否有运动诱发缺血"},
                "st_depression_mm": {"type": "number", "description": "ST 段压低 (mm)"},
                "has_arrhythmia": {"type": "boolean", "description": "是否有心律失常"},
                "arrhythmia_type": {"type": "string", "description": "心律失常类型: none/simple/complex"},
                "has_heart_failure": {"type": "boolean", "description": "是否有心力衰竭"},
                "nyha_class": {"type": "integer", "description": "NYHA 心功能分级 (1-4)"}
            },
            "required": []
        }
    },
    {
        "name": "check_contraindications",
        "description": "检查运动禁忌症。区分绝对禁忌症和相对禁忌症，返回是否可以运动及注意事项。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "has_unstable_angina": {"type": "boolean", "description": "不稳定型心绞痛"},
                "has_acute_mi": {"type": "boolean", "description": "急性心肌梗死"},
                "has_uncontrolled_arrhythmia": {"type": "boolean", "description": "未控制的心律失常"},
                "has_severe_aortic_stenosis": {"type": "boolean", "description": "重度主动脉瓣狭窄"},
                "has_acute_heart_failure": {"type": "boolean", "description": "急性心力衰竭"},
                "has_uncontrolled_hypertension": {"type": "boolean", "description": "未控制的高血压"},
                "sbp": {"type": "integer", "description": "收缩压 (mmHg)"},
                "dbp": {"type": "integer", "description": "舒张压 (mmHg)"}
            },
            "required": []
        }
    },
    {
        "name": "generate_hr_prescription",
        "description": "生成基于心率的运动处方。包含 5 个心率训练区间和推荐目标心率范围。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hr_max": {"type": "integer", "description": "最大心率 (bpm)"},
                "hr_rest": {"type": "integer", "description": "静息心率 (bpm)"},
                "hr_at": {"type": "integer", "description": "无氧阈心率 (bpm)，可选"},
                "risk_level": {"type": "string", "description": "风险等级: low/moderate/high"}
            },
            "required": ["hr_max", "hr_rest"]
        }
    },
    {
        "name": "generate_exercise_intensity",
        "description": "生成多维度运动强度处方。包含心率、VO2、METs、RPE 等多个维度的强度建议。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vo2_peak": {"type": "number", "description": "峰值摄氧量 (ml/kg/min)"},
                "hr_max": {"type": "integer", "description": "最大心率 (bpm)"},
                "hr_rest": {"type": "integer", "description": "静息心率 (bpm)"},
                "hr_at": {"type": "integer", "description": "无氧阈心率 (bpm)，可选"},
                "risk_level": {"type": "string", "description": "风险等级: low/moderate/high"}
            },
            "required": ["vo2_peak", "hr_max", "hr_rest"]
        }
    },
    {
        "name": "generate_weekly_schedule",
        "description": "生成每周运动计划。包含有氧运动、抗阻训练、柔韧性训练的完整周计划。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "risk_level": {"type": "string", "description": "风险等级: low/moderate/high"},
                "hr_max": {"type": "integer", "description": "最大心率 (bpm)"},
                "hr_rest": {"type": "integer", "description": "静息心率 (bpm)"},
                "phase": {"type": "string", "description": "康复阶段: initial/improvement/maintenance"},
                "include_resistance": {"type": "boolean", "description": "是否包含抗阻训练"},
                "include_flexibility": {"type": "boolean", "description": "是否包含柔韧性训练"}
            },
            "required": []
        }
    },
    {
        "name": "generate_exercise_plan",
        "description": "生成运动处方草案（可保存为运动规划草案/确认）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "患者 ID（用于保存为运动规划）"},
                "user_id": {"type": "string", "description": "用户 ID（如与患者不同）"},
                "session_id": {"type": "string", "description": "来源会话 ID（用于引用本会话上传/附加的报告）"},
                "risk_level": {"type": "string", "description": "风险等级: low/moderate/high"},
                "hr_max": {"type": "integer", "description": "最大心率 (bpm)"},
                "hr_rest": {"type": "integer", "description": "静息心率 (bpm)"},
                "hr_at": {"type": "integer", "description": "无氧阈心率 (bpm)，可选"},
                "phase": {"type": "string", "description": "康复阶段: initial/improvement/maintenance"},
                "include_resistance": {"type": "boolean", "description": "是否包含抗阻训练"},
                "include_flexibility": {"type": "boolean", "description": "是否包含柔韧性训练"},
                "title": {"type": "string", "description": "处方标题（可选）"},
                "valid_from": {"type": "string", "description": "开始日期 YYYY-MM-DD（可选）"},
                "valid_to": {"type": "string", "description": "结束日期 YYYY-MM-DD（可选）"},
                "save_plan": {"type": "boolean", "description": "是否保存为运动规划（默认 true）"},
                "confirm_plan": {"type": "boolean", "description": "是否直接确认保存（默认 false）"},
                "source_session_id": {"type": "string", "description": "来源会话 ID（可选，默认使用 session_id）"}
            },
            "required": []
        }
    },
    {
        "name": "generate_nutrition_plan",
        "description": "生成营养方案（能量、宏量营养素、餐次建议与约束）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string", "description": "患者 ID（用于保存为营养规划）"},
                "user_id": {"type": "string", "description": "用户 ID（如与患者不同）"},
                "weight_kg": {"type": "number", "description": "体重 (kg)"},
                "height_cm": {"type": "number", "description": "身高 (cm)"},
                "age": {"type": "integer", "description": "年龄"},
                "sex": {
                    "type": "string",
                    "description": "性别: male/female/other",
                    "enum": ["male", "female", "other"]
                },
                "activity_level": {
                    "type": "string",
                    "description": "活动水平: sedentary/light/moderate/active/very_active",
                    "enum": ["sedentary", "light", "moderate", "active", "very_active"]
                },
                "goal": {
                    "type": "string",
                    "description": "目标: loss/maintenance/gain",
                    "enum": ["loss", "maintenance", "gain"]
                },
                "diet_type": {
                    "type": "string",
                    "description": "饮食类型",
                    "enum": [
                        "balanced",
                        "low_carb",
                        "high_protein",
                        "mediterranean",
                        "dash",
                        "low_fat",
                        "low_sugar",
                        "keto"
                    ]
                },
                "meals_per_day": {"type": "integer", "description": "餐次数 (3-5)"},
                "target_kcal": {"type": "number", "description": "目标热量 (kcal)，提供则直接采用"},
                "calorie_adjustment": {"type": "number", "description": "热量调整 (kcal)"},
                "save_plan": {"type": "boolean", "description": "是否保存为营养规划（默认 true）"},
                "confirm_plan": {"type": "boolean", "description": "是否直接确认保存（默认 false）"},
                "source_session_id": {"type": "string", "description": "来源会话 ID（可选）"},
                "conditions": {
                    "type": "object",
                    "description": "伴随疾病/风险",
                    "properties": {
                        "diabetes": {"type": "boolean"},
                        "hypertension": {"type": "boolean"},
                        "constipation": {"type": "boolean"}
                    }
                },
                "allergies": {"type": "array", "items": {"type": "string"}, "description": "过敏原"},
                "preferences": {"type": "array", "items": {"type": "string"}, "description": "饮食偏好"}
            },
            "required": ["weight_kg", "height_cm", "age", "sex"]
        }
    },
    {
        "name": "retrieve_knowledge",
        "description": "从 CPET 知识库检索相关信息。输入问题，返回相关的临床指南、指标解读等专业知识。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索问题"},
                "top_k": {"type": "integer", "description": "返回结果数量，默认 3"}
            },
            "required": ["query"]
        }
    }
]


def get_tool_definitions() -> List[Dict[str, Any]]:
    """获取所有 MCP 工具定义"""
    return MCP_TOOLS


def get_tool_by_name(name: str) -> Dict[str, Any] | None:
    """根据名称获取工具定义"""
    for tool in MCP_TOOLS:
        if tool["name"] == name:
            return tool
    return None


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行工具调用

    Args:
        name: 工具名称
        arguments: 工具参数

    Returns:
        工具执行结果
    """
    from .calculator import (
        calculate_weber_class,
        calculate_bmi,
        calculate_target_hr_zone,
        calculate_mets,
    )
    from .risk import assess_exercise_risk, check_contraindications
    from .prescription import (
        generate_hr_prescription,
        generate_exercise_intensity,
        generate_weekly_schedule,
    )
    from .nutrition import generate_nutrition_plan
    from ..plans.storage import create_plan_draft, confirm_plan

    tool_map = {
        "calculate_weber_class": lambda args: {
            "grade": (r := calculate_weber_class(args["vo2_peak"])).grade.value,
            "description": r.description,
            "prognosis": r.prognosis,
        },
        "calculate_bmi": lambda args: calculate_bmi(args["weight_kg"], args["height_cm"]),
        "calculate_target_hr_zone": lambda args: calculate_target_hr_zone(
            args["hr_max"],
            args["hr_rest"],
            args.get("intensity_low", 0.5),
            args.get("intensity_high", 0.7),
        ),
        "calculate_mets": lambda args: calculate_mets(args["vo2"]),
        "assess_exercise_risk": lambda args: {
            "level": (r := assess_exercise_risk(**args)).level.value,
            "summary": r.summary,
            "recommendations": r.recommendations,
        },
        "check_contraindications": lambda args: check_contraindications(**args),
        "generate_hr_prescription": lambda args: generate_hr_prescription(
            args["hr_max"],
            args["hr_rest"],
            args.get("hr_at"),
            args.get("risk_level", "low"),
        ),
        "generate_exercise_intensity": lambda args: generate_exercise_intensity(
            args["vo2_peak"],
            args["hr_max"],
            args["hr_rest"],
            args.get("hr_at"),
            args.get("vo2_at"),
            args.get("risk_level", "low"),
        ),
        "generate_weekly_schedule": lambda args: generate_weekly_schedule(
            args.get("risk_level", "low"),
            args.get("hr_max", 150),
            args.get("hr_rest", 70),
            args.get("hr_at"),
            args.get("include_resistance", True),
            args.get("include_flexibility", True),
            args.get("phase", "maintenance"),
        ),
        "generate_exercise_plan": lambda args: _execute_exercise_plan(
            args=args,
            generate_fn=generate_weekly_schedule,
            create_plan=create_plan_draft,
            confirm_plan_fn=confirm_plan,
        ),
        "generate_nutrition_plan": lambda args: _execute_nutrition_plan(
            args=args,
            generate_fn=generate_nutrition_plan,
            create_plan=create_plan_draft,
            confirm_plan_fn=confirm_plan,
        ),
        "retrieve_knowledge": _execute_retrieve_knowledge,
    }

    if name not in tool_map:
        return {"error": f"Unknown tool: {name}"}

    try:
        return tool_map[name](arguments)
    except Exception as e:
        return {"error": str(e)}


def _nutrition_plan_payload(result: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    today = date.today()
    valid_from = args.get("valid_from") or today.isoformat()
    valid_to = args.get("valid_to") or (today + timedelta(days=6)).isoformat()
    daily = result.get("daily_targets") or {}
    return {
        "title": args.get("title") or "营养处方",
        "summary": result.get("summary") or "营养处方",
        "valid_from": valid_from,
        "valid_to": valid_to,
        "macros": {
            "kcal": daily.get("kcal"),
            "protein_g": daily.get("protein_g"),
            "carbs_g": daily.get("carbs_g"),
            "fat_g": daily.get("fat_g"),
        },
        "meals": result.get("meals") or [],
        "constraints": result.get("constraints") or {},
    }


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        out = float(value)
        return out if out > 0 else None
    if isinstance(value, str):
        match = re.search(r"-?\d+(\.\d+)?", value)
        if match:
            try:
                out = float(match.group(0))
                return out if out > 0 else None
            except Exception:
                return None
    return None


def _coerce_int(value: Any) -> int | None:
    out = _coerce_float(value)
    if out is None:
        return None
    return int(round(out))


def _deep_collect_keys(value: Any, *, out: Dict[str, Any]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            key = str(k).strip().lower()
            if key and key not in out:
                out[key] = v
            if isinstance(v, (dict, list)):
                _deep_collect_keys(v, out=out)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                _deep_collect_keys(item, out=out)


def _infer_exercise_inputs(args: Dict[str, Any]) -> Dict[str, Any]:
    inferred: Dict[str, Any] = {}
    session_id = args.get("session_id") or args.get("source_session_id")
    user_id = args.get("__user_id") or args.get("user_id") or args.get("patient_id")
    if not session_id or not user_id:
        return inferred

    try:
        from ..artifacts.storage import list_session_artifacts, read_artifact_parsed_json

        artifacts = list_session_artifacts(user_id=user_id, session_id=session_id)
        collected: Dict[str, Any] = {}
        for row in artifacts:
            parsed = read_artifact_parsed_json(row)
            if parsed:
                _deep_collect_keys(parsed, out=collected)

        # Common CPET keys.
        inferred["vo2_peak"] = _coerce_float(
            collected.get("vo2_peak") or collected.get("vo2peak") or collected.get("vo2_peak_mlkgmin")
        )
        inferred["max_mets"] = _coerce_float(collected.get("max_mets") or collected.get("mets_max"))
        inferred["hr_max"] = _coerce_int(
            collected.get("hr_max")
            or collected.get("hrpeak")
            or collected.get("peak_hr")
            or collected.get("max_hr")
        )
        inferred["hr_rest"] = _coerce_int(collected.get("hr_rest") or collected.get("rest_hr") or collected.get("rhr"))
        inferred["hr_at"] = _coerce_int(collected.get("vt1_hr") or collected.get("hr_at") or collected.get("at_hr"))
    except Exception:
        return inferred

    return inferred


def _default_risk_level(*, vo2_peak: float | None, max_mets: float | None) -> str:
    # Conservative heuristic: use low only for good exercise capacity.
    if max_mets is not None:
        if max_mets < 5:
            return "high"
        if max_mets < 7:
            return "moderate"
        return "low"
    if vo2_peak is not None:
        if vo2_peak < 14:
            return "high"
        if vo2_peak < 18:
            return "moderate"
        return "low"
    return "moderate"


def _extract_minutes(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        mins = int(round(float(value)))
        return mins if mins > 0 else None
    if isinstance(value, str):
        match = re.search(r"\d{1,3}", value)
        if match:
            try:
                mins = int(match.group(0))
                return mins if mins > 0 else None
            except Exception:
                return None
    return None


def _exercise_plan_payload(schedule: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    today = date.today()
    valid_from = args.get("valid_from") or today.isoformat()
    valid_to = args.get("valid_to") or (today + timedelta(days=6)).isoformat()

    prescription_summary = schedule.get("prescription_summary") or {}
    weekly_summary = schedule.get("weekly_summary") or {}
    hr_zone = None
    if isinstance(prescription_summary, dict):
        hr_zone = prescription_summary.get("hr_target")
    minutes_target = None
    if isinstance(weekly_summary, dict):
        minutes_target = _coerce_float(weekly_summary.get("aerobic_minutes"))

    sessions: list[dict] = []
    for item in schedule.get("weekly_schedule") or []:
        if not isinstance(item, dict):
            continue
        day = item.get("day")
        session_type = item.get("type") or "训练"
        duration_min = _extract_minutes(item.get("duration"))
        intensity = item.get("intensity")
        kcal_est = None

        notes_parts: list[str] = []
        if isinstance(day, str) and day:
            notes_parts.append(day)
        activities = item.get("activities")
        if isinstance(activities, list):
            cleaned = [str(a) for a in activities if a]
            if cleaned:
                notes_parts.append("、".join(cleaned))
        if isinstance(item.get("hr_target"), str) and item.get("hr_target"):
            notes_parts.append(f"目标心率 {item.get('hr_target')}")
        if isinstance(item.get("notes"), str) and item.get("notes"):
            notes_parts.append(item.get("notes"))

        sessions.append(
            {
                "type": str(session_type),
                "duration_min": duration_min,
                "intensity": str(intensity) if intensity is not None else None,
                "kcal_est": kcal_est,
                "notes": " · ".join(notes_parts) if notes_parts else None,
            }
        )

    summary = None
    if isinstance(prescription_summary, dict):
        freq = prescription_summary.get("frequency")
        intensity = prescription_summary.get("intensity")
        time = prescription_summary.get("time")
        hr_target = prescription_summary.get("hr_target")
        parts = [p for p in [freq, intensity, time, hr_target] if isinstance(p, str) and p]
        if parts:
            summary = "；".join(parts)
    if not summary:
        summary = schedule.get("phase_description") or "运动处方"

    return {
        "title": args.get("title") or "运动处方",
        "summary": summary,
        "valid_from": valid_from,
        "valid_to": valid_to,
        "goals": {
            "steps_target": None,
            "minutes_target": minutes_target,
            "kcal_target": None,
            "hr_zone": hr_zone,
        },
        "sessions": sessions,
    }


def _execute_exercise_plan(
    *,
    args: Dict[str, Any],
    generate_fn,
    create_plan,
    confirm_plan_fn,
) -> Dict[str, Any]:
    inferred = _infer_exercise_inputs(args)
    vo2_peak = inferred.get("vo2_peak")
    max_mets = inferred.get("max_mets")

    risk_level = args.get("risk_level") or inferred.get("risk_level") or _default_risk_level(
        vo2_peak=vo2_peak,
        max_mets=max_mets,
    )
    hr_max = _coerce_int(args.get("hr_max")) or inferred.get("hr_max") or 150
    hr_rest = _coerce_int(args.get("hr_rest")) or inferred.get("hr_rest") or 70
    hr_at = _coerce_int(args.get("hr_at")) or inferred.get("hr_at")

    schedule = generate_fn(
        risk_level,
        hr_max,
        hr_rest,
        hr_at,
        args.get("include_resistance", True),
        args.get("include_flexibility", True),
        args.get("phase", "maintenance"),
    )

    payload = _exercise_plan_payload(schedule, args)

    save_plan = args.get("save_plan")
    if save_plan is None:
        save_plan = True

    result: Dict[str, Any] = {
        "summary": payload.get("summary") or "运动处方",
        "plan_payload": payload,
        "schedule": schedule,
        "inferred": {
            "risk_level": risk_level,
            "hr_max": hr_max,
            "hr_rest": hr_rest,
            "hr_at": hr_at,
            "vo2_peak": vo2_peak,
            "max_mets": max_mets,
        },
    }

    if save_plan:
        user_id = args.get("__user_id") or args.get("user_id") or args.get("patient_id")
        patient_id = args.get("patient_id") or user_id
        if user_id and patient_id:
            draft = create_plan(
                user_id=user_id,
                patient_id=patient_id,
                plan_type="exercise",
                payload=payload,
                summary=payload.get("summary") or "",
                source_session_id=args.get("source_session_id") or args.get("session_id") or "mcp",
                source_artifact_ids=None,
            )
            if args.get("confirm_plan"):
                confirmed = confirm_plan_fn(user_id=user_id, draft_id=draft["plan_id"])
                result["saved_plan"] = {
                    "plan_id": confirmed.get("plan_id"),
                    "status": confirmed.get("status"),
                    "confirmed_at": confirmed.get("confirmed_at"),
                }
            else:
                result["saved_plan"] = {
                    "plan_id": draft.get("plan_id"),
                    "status": draft.get("status"),
                    "confirmed_at": None,
                }
        else:
            result["saved_plan"] = {"error": "missing user_id/patient_id"}

    return result


def _execute_nutrition_plan(
    *,
    args: Dict[str, Any],
    generate_fn,
    create_plan,
    confirm_plan_fn,
) -> Dict[str, Any]:
    result = generate_fn(
        args["weight_kg"],
        args["height_cm"],
        args["age"],
        args["sex"],
        args.get("activity_level", "moderate"),
        args.get("goal", "maintenance"),
        args.get("diet_type", "balanced"),
        args.get("meals_per_day", 3),
        args.get("target_kcal"),
        args.get("calorie_adjustment"),
        args.get("conditions"),
        args.get("allergies"),
        args.get("preferences"),
    )

    save_plan = args.get("save_plan")
    if save_plan is None:
        save_plan = True

    if save_plan:
        user_id = args.get("__user_id") or args.get("user_id") or args.get("patient_id")
        patient_id = args.get("patient_id") or user_id
        if user_id and patient_id:
            payload = _nutrition_plan_payload(result, args)
            draft = create_plan(
                user_id=user_id,
                patient_id=patient_id,
                plan_type="nutrition",
                payload=payload,
                summary=payload.get("summary") or "",
                source_session_id=args.get("source_session_id") or args.get("session_id") or "mcp",
                source_artifact_ids=None,
            )
            if args.get("confirm_plan"):
                confirmed = confirm_plan_fn(user_id=user_id, draft_id=draft["plan_id"])
                result["saved_plan"] = {
                    "plan_id": confirmed.get("plan_id"),
                    "status": confirmed.get("status"),
                    "confirmed_at": confirmed.get("confirmed_at"),
                }
            else:
                result["saved_plan"] = {
                    "plan_id": draft.get("plan_id"),
                    "status": draft.get("status"),
                    "confirmed_at": None,
                }
            result["plan_payload"] = payload
        else:
            result["saved_plan"] = {"error": "missing user_id/patient_id"}

    return result


def _execute_retrieve_knowledge(args: Dict[str, Any]) -> Dict[str, Any]:
    """执行知识检索"""
    try:
        from ..rag import KnowledgeRetriever
        from pathlib import Path

        db_path = Path(__file__).resolve().parent.parent.parent / "data" / "vector_db"
        if not db_path.exists():
            return {"error": "Knowledge base not initialized", "context": ""}

        retriever = KnowledgeRetriever(db_path)
        if not retriever.is_ready():
            return {"error": "Knowledge base is empty", "context": ""}

        query = args["query"]
        top_k = args.get("top_k", 3)

        results = retriever.retrieve(query, top_k=top_k)
        context = retriever.retrieve_with_context(query, top_k=top_k)

        return {
            "query": query,
            "results": [
                {
                    "content": r.content[:500],
                    "source": r.source,
                    "score": round(r.score, 3),
                    "title": r.metadata.get("title", ""),
                }
                for r in results
            ],
            "context": context,
        }
    except ImportError:
        return {"error": "RAG module not available", "context": ""}
