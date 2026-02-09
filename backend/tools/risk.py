# -*- coding: utf-8 -*-
"""
运动风险评估工具

提供运动风险分层和禁忌症检查功能。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass
class RiskFactor:
    """风险因素"""
    name: str
    present: bool
    severity: str  # "mild", "moderate", "severe"
    description: str


@dataclass
class RiskAssessment:
    """风险评估结果"""
    level: RiskLevel
    score: int
    factors: List[RiskFactor]
    summary: str
    recommendations: List[str]


def assess_exercise_risk(
    # 运动试验结果
    max_mets: Optional[float] = None,
    has_ischemia: bool = False,
    st_depression_mm: float = 0,
    has_angina: bool = False,
    has_arrhythmia: bool = False,
    arrhythmia_type: str = "none",  # "none", "simple", "complex"
    has_abnormal_bp: bool = False,
    bp_response: str = "normal",  # "normal", "hypertensive", "hypotensive"
    # 非运动试验因素
    lvef: Optional[float] = None,
    has_heart_failure: bool = False,
    nyha_class: Optional[int] = None,
    has_cardiac_arrest_history: bool = False,
    has_mi_history: bool = False,
    mi_weeks_ago: Optional[int] = None,
    has_cabg_history: bool = False,
    cabg_weeks_ago: Optional[int] = None,
    has_pci_history: bool = False,
    # 其他因素
    has_diabetes: bool = False,
    has_renal_disease: bool = False,
    age: Optional[int] = None,
) -> RiskAssessment:
    """
    评估运动风险等级

    基于 AACVPR 风险分层标准

    Returns:
        RiskAssessment: 风险评估结果
    """
    factors: List[RiskFactor] = []
    high_risk_count = 0
    moderate_risk_count = 0

    # 1. 运动能力评估
    if max_mets is not None:
        if max_mets < 5:
            factors.append(RiskFactor(
                name="运动能力",
                present=True,
                severity="severe",
                description=f"运动能力严重受限 ({max_mets:.1f} METs < 5)"
            ))
            high_risk_count += 1
        elif max_mets < 7:
            factors.append(RiskFactor(
                name="运动能力",
                present=True,
                severity="moderate",
                description=f"运动能力中度受限 ({max_mets:.1f} METs)"
            ))
            moderate_risk_count += 1

    # 2. 心肌缺血评估
    if has_ischemia or st_depression_mm > 0:
        if st_depression_mm >= 2:
            factors.append(RiskFactor(
                name="心肌缺血",
                present=True,
                severity="severe",
                description=f"运动诱发明显缺血 (ST压低 {st_depression_mm}mm)"
            ))
            high_risk_count += 1
        elif st_depression_mm >= 1:
            factors.append(RiskFactor(
                name="心肌缺血",
                present=True,
                severity="moderate",
                description=f"运动诱发轻度缺血 (ST压低 {st_depression_mm}mm)"
            ))
            moderate_risk_count += 1

    # 3. 心绞痛评估
    if has_angina:
        factors.append(RiskFactor(
            name="心绞痛",
            present=True,
            severity="moderate",
            description="运动诱发心绞痛"
        ))
        moderate_risk_count += 1

    # 4. 心律失常评估
    if has_arrhythmia:
        if arrhythmia_type == "complex":
            factors.append(RiskFactor(
                name="心律失常",
                present=True,
                severity="severe",
                description="运动诱发复杂心律失常（室速、多形室早等）"
            ))
            high_risk_count += 1
        elif arrhythmia_type == "simple":
            factors.append(RiskFactor(
                name="心律失常",
                present=True,
                severity="mild",
                description="运动诱发简单心律失常"
            ))

    # 5. 血压反应评估
    if has_abnormal_bp:
        if bp_response == "hypotensive":
            factors.append(RiskFactor(
                name="血压反应",
                present=True,
                severity="severe",
                description="运动性低血压"
            ))
            high_risk_count += 1
        elif bp_response == "hypertensive":
            factors.append(RiskFactor(
                name="血压反应",
                present=True,
                severity="moderate",
                description="运动性高血压反应"
            ))
            moderate_risk_count += 1

    # 6. 左室功能评估
    if lvef is not None:
        if lvef < 40:
            factors.append(RiskFactor(
                name="左室功能",
                present=True,
                severity="severe",
                description=f"左室射血分数降低 (LVEF {lvef}%)"
            ))
            high_risk_count += 1
        elif lvef < 50:
            factors.append(RiskFactor(
                name="左室功能",
                present=True,
                severity="moderate",
                description=f"左室射血分数轻度降低 (LVEF {lvef}%)"
            ))
            moderate_risk_count += 1

    # 7. 心衰评估
    if has_heart_failure:
        if nyha_class and nyha_class >= 3:
            factors.append(RiskFactor(
                name="心力衰竭",
                present=True,
                severity="severe",
                description=f"心功能 NYHA {nyha_class} 级"
            ))
            high_risk_count += 1
        else:
            factors.append(RiskFactor(
                name="心力衰竭",
                present=True,
                severity="moderate",
                description="心力衰竭病史"
            ))
            moderate_risk_count += 1

    # 8. 心脏骤停史
    if has_cardiac_arrest_history:
        factors.append(RiskFactor(
            name="心脏骤停",
            present=True,
            severity="severe",
            description="心脏骤停病史"
        ))
        high_risk_count += 1

    # 9. 近期心梗
    if has_mi_history and mi_weeks_ago is not None and mi_weeks_ago < 4:
        factors.append(RiskFactor(
            name="近期心梗",
            present=True,
            severity="severe",
            description=f"近期心肌梗死 ({mi_weeks_ago} 周前)"
        ))
        high_risk_count += 1

    # 10. 近期手术
    if has_cabg_history and cabg_weeks_ago is not None and cabg_weeks_ago < 4:
        factors.append(RiskFactor(
            name="近期手术",
            present=True,
            severity="moderate",
            description=f"近期 CABG 手术 ({cabg_weeks_ago} 周前)"
        ))
        moderate_risk_count += 1

    # 确定风险等级
    if high_risk_count >= 1:
        level = RiskLevel.HIGH
        summary = f"高风险：存在 {high_risk_count} 个高危因素"
    elif moderate_risk_count >= 2:
        level = RiskLevel.MODERATE
        summary = f"中风险：存在 {moderate_risk_count} 个中危因素"
    elif moderate_risk_count == 1:
        level = RiskLevel.MODERATE
        summary = "中风险：存在 1 个中危因素"
    else:
        level = RiskLevel.LOW
        summary = "低风险：无明显高危因素"

    # 生成建议
    recommendations = _generate_risk_recommendations(level, factors)

    return RiskAssessment(
        level=level,
        score=high_risk_count * 3 + moderate_risk_count,
        factors=factors,
        summary=summary,
        recommendations=recommendations,
    )


def _generate_risk_recommendations(level: RiskLevel, factors: List[RiskFactor]) -> List[str]:
    """根据风险等级生成建议"""
    recommendations = []

    if level == RiskLevel.HIGH:
        recommendations.extend([
            "建议在医疗监督下进行运动康复",
            "运动时需持续心电监护",
            "从低强度开始，缓慢递增",
            "确保急救设备和人员就位",
            "建议心内科会诊评估",
        ])
    elif level == RiskLevel.MODERATE:
        recommendations.extend([
            "建议在专业指导下进行运动",
            "初期运动时建议心电监护",
            "中等强度运动为主",
            "定期随访评估",
        ])
    else:
        recommendations.extend([
            "可进行中高强度运动",
            "逐步过渡到无监护运动",
            "定期复查 CPET",
        ])

    # 针对特定因素的建议
    for factor in factors:
        if factor.name == "心肌缺血" and factor.present:
            recommendations.append("运动强度应低于缺血阈值心率")
        if factor.name == "心律失常" and factor.severity == "severe":
            recommendations.append("考虑 ICD 植入评估")
        if factor.name == "左室功能" and factor.severity == "severe":
            recommendations.append("优化心衰药物治疗")

    return recommendations


def get_monitoring_recommendation(risk_level: RiskLevel) -> dict:
    """
    根据风险等级获取监护建议

    Args:
        risk_level: 风险等级

    Returns:
        dict: 监护建议
    """
    if risk_level == RiskLevel.HIGH:
        return {
            "level": "高级监护",
            "ecg_monitoring": "持续心电监护",
            "supervision": "医疗人员直接监督",
            "equipment": "除颤器、急救药品就位",
            "frequency": "每次运动全程监护",
            "duration": "至少 12-18 次监护运动后评估",
            "staff_ratio": "1:1 或 1:2",
        }
    elif risk_level == RiskLevel.MODERATE:
        return {
            "level": "中级监护",
            "ecg_monitoring": "间歇心电监护",
            "supervision": "专业人员在场",
            "equipment": "急救设备可及",
            "frequency": "初期每次监护，后期可间歇",
            "duration": "6-12 次监护运动后评估",
            "staff_ratio": "1:4 或 1:5",
        }
    else:
        return {
            "level": "基础监护",
            "ecg_monitoring": "无需常规监护",
            "supervision": "可自主运动",
            "equipment": "了解急救流程即可",
            "frequency": "定期随访",
            "duration": "可过渡到社区/家庭运动",
            "staff_ratio": "1:10 或更高",
        }


@dataclass
class Contraindication:
    """禁忌症"""
    name: str
    type: str  # "absolute" 或 "relative"
    description: str
    recommendation: str


def check_contraindications(
    # 绝对禁忌症
    has_unstable_angina: bool = False,
    has_acute_mi: bool = False,
    acute_mi_days: Optional[int] = None,
    has_uncontrolled_arrhythmia: bool = False,
    has_severe_aortic_stenosis: bool = False,
    has_acute_heart_failure: bool = False,
    has_acute_pe: bool = False,
    has_acute_myocarditis: bool = False,
    has_acute_pericarditis: bool = False,
    has_aortic_dissection: bool = False,
    # 相对禁忌症
    has_uncontrolled_hypertension: bool = False,
    sbp: Optional[int] = None,
    dbp: Optional[int] = None,
    has_moderate_valve_disease: bool = False,
    has_electrolyte_abnormality: bool = False,
    has_hypertrophic_cardiomyopathy: bool = False,
    has_high_degree_av_block: bool = False,
    has_mental_impairment: bool = False,
    has_orthopedic_limitation: bool = False,
) -> dict:
    """
    检查运动禁忌症

    Returns:
        dict: 禁忌症检查结果
    """
    absolute: List[Contraindication] = []
    relative: List[Contraindication] = []

    # 绝对禁忌症检查
    if has_unstable_angina:
        absolute.append(Contraindication(
            name="不稳定型心绞痛",
            type="absolute",
            description="近期发作的不稳定型心绞痛",
            recommendation="禁止运动，立即心内科评估"
        ))

    if has_acute_mi or (acute_mi_days is not None and acute_mi_days < 2):
        absolute.append(Contraindication(
            name="急性心肌梗死",
            type="absolute",
            description="急性心肌梗死 48 小时内",
            recommendation="禁止运动，待病情稳定后评估"
        ))

    if has_uncontrolled_arrhythmia:
        absolute.append(Contraindication(
            name="未控制的心律失常",
            type="absolute",
            description="症状性或血流动力学不稳定的心律失常",
            recommendation="禁止运动，先控制心律失常"
        ))

    if has_severe_aortic_stenosis:
        absolute.append(Contraindication(
            name="重度主动脉瓣狭窄",
            type="absolute",
            description="症状性重度主动脉瓣狭窄",
            recommendation="禁止运动，评估手术指征"
        ))

    if has_acute_heart_failure:
        absolute.append(Contraindication(
            name="急性心力衰竭",
            type="absolute",
            description="失代偿性心力衰竭",
            recommendation="禁止运动，先稳定心功能"
        ))

    if has_acute_pe:
        absolute.append(Contraindication(
            name="急性肺栓塞",
            type="absolute",
            description="急性肺栓塞或深静脉血栓",
            recommendation="禁止运动，抗凝治疗稳定后评估"
        ))

    if has_acute_myocarditis:
        absolute.append(Contraindication(
            name="急性心肌炎",
            type="absolute",
            description="急性心肌炎",
            recommendation="禁止运动至少 3-6 个月"
        ))

    if has_acute_pericarditis:
        absolute.append(Contraindication(
            name="急性心包炎",
            type="absolute",
            description="急性心包炎",
            recommendation="禁止运动，待炎症消退"
        ))

    if has_aortic_dissection:
        absolute.append(Contraindication(
            name="主动脉夹层",
            type="absolute",
            description="已知主动脉夹层",
            recommendation="禁止运动，外科评估"
        ))

    # 相对禁忌症检查
    if has_uncontrolled_hypertension or (sbp and sbp > 180) or (dbp and dbp > 110):
        bp_str = f"{sbp}/{dbp} mmHg" if sbp and dbp else "未控制"
        relative.append(Contraindication(
            name="未控制的高血压",
            type="relative",
            description=f"血压 {bp_str}",
            recommendation="先控制血压至 <180/110 mmHg"
        ))

    if has_moderate_valve_disease:
        relative.append(Contraindication(
            name="中度瓣膜病",
            type="relative",
            description="中度瓣膜狭窄或反流",
            recommendation="低中强度运动，定期超声随访"
        ))

    if has_electrolyte_abnormality:
        relative.append(Contraindication(
            name="电解质紊乱",
            type="relative",
            description="电解质异常（低钾、低镁等）",
            recommendation="纠正电解质后运动"
        ))

    if has_hypertrophic_cardiomyopathy:
        relative.append(Contraindication(
            name="肥厚型心肌病",
            type="relative",
            description="肥厚型心肌病",
            recommendation="避免竞技运动和高强度运动"
        ))

    if has_high_degree_av_block:
        relative.append(Contraindication(
            name="高度房室传导阻滞",
            type="relative",
            description="二度 II 型或三度房室传导阻滞",
            recommendation="考虑起搏器植入后运动"
        ))

    if has_orthopedic_limitation:
        relative.append(Contraindication(
            name="骨骼肌肉限制",
            type="relative",
            description="骨关节疾病限制运动",
            recommendation="选择适合的运动方式，避免负重"
        ))

    # 汇总结果
    can_exercise = len(absolute) == 0
    needs_caution = len(relative) > 0

    if absolute:
        overall = "存在绝对禁忌症，禁止运动"
    elif relative:
        overall = "存在相对禁忌症，需谨慎评估后运动"
    else:
        overall = "无明显禁忌症，可进行运动"

    return {
        "can_exercise": can_exercise,
        "needs_caution": needs_caution,
        "overall": overall,
        "absolute_contraindications": [
            {
                "name": c.name,
                "description": c.description,
                "recommendation": c.recommendation,
            }
            for c in absolute
        ],
        "relative_contraindications": [
            {
                "name": c.name,
                "description": c.description,
                "recommendation": c.recommendation,
            }
            for c in relative
        ],
        "absolute_count": len(absolute),
        "relative_count": len(relative),
    }
