# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) 工具定义

将 CPET 工具暴露为 MCP 格式，供 OpenCode Agent 调用。
"""

from __future__ import annotations

from typing import Any, Dict, List

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
        "retrieve_knowledge": _execute_retrieve_knowledge,
    }

    if name not in tool_map:
        return {"error": f"Unknown tool: {name}"}

    try:
        return tool_map[name](arguments)
    except Exception as e:
        return {"error": str(e)}


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
