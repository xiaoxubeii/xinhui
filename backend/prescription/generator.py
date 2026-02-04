# -*- coding: utf-8 -*-
"""
运动处方综合生成器

整合风险分层、有氧运动、抗阻训练、柔韧性训练和神经肌肉训练，
生成完整的个性化运动处方。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .risk_stratification import (
    RiskStratifier,
    RiskLevel,
    ExerciseTestResults,
    NonExerciseTestResults,
    PatientInfo,
)
from .aerobic import (
    AerobicPrescription,
    AerobicPrescriptionGenerator,
    CPETResults,
)
from .resistance import (
    ResistancePrescription,
    ResistancePrescriptionGenerator,
)
from .flexibility import (
    FlexibilityPrescription,
    FlexibilityPrescriptionGenerator,
    NeuromuscularPrescription,
    NeuromuscularPrescriptionGenerator,
)


@dataclass
class ExercisePrescription:
    """完整运动处方"""
    # 基本信息
    patient_name: str
    patient_id: str
    generated_at: datetime
    valid_until: datetime
    
    # 风险分层
    risk_level: RiskLevel
    risk_description: str
    monitoring_recommendation: dict
    
    # 各类运动处方
    aerobic: AerobicPrescription
    resistance: ResistancePrescription
    flexibility: FlexibilityPrescription
    neuromuscular: NeuromuscularPrescription
    
    # 总体建议
    weekly_schedule: List[dict]
    general_precautions: List[str]
    emergency_instructions: List[str]
    follow_up_recommendation: str
    
    # 医生签名
    prescribing_physician: Optional[str] = None
    physician_notes: Optional[str] = None


class PrescriptionGenerator:
    """运动处方综合生成器"""
    
    def __init__(self):
        self.risk_stratifier = RiskStratifier()
        self.aerobic_generator = AerobicPrescriptionGenerator()
        self.resistance_generator = ResistancePrescriptionGenerator()
        self.flexibility_generator = FlexibilityPrescriptionGenerator()
        self.neuromuscular_generator = NeuromuscularPrescriptionGenerator()
    
    def generate(
        self,
        patient_info: PatientInfo,
        cpet_results: CPETResults,
        exercise_test_results: ExerciseTestResults,
        non_exercise_results: NonExerciseTestResults,
        has_cardiac_surgery: bool = False,
        surgery_weeks_ago: Optional[int] = None,
        has_balance_issues: bool = False,
        has_fall_history: bool = False,
        prescribing_physician: Optional[str] = None,
        validity_weeks: int = 4,
    ) -> ExercisePrescription:
        """
        生成完整运动处方
        
        Args:
            patient_info: 患者基本信息
            cpet_results: 心肺运动试验结果
            exercise_test_results: 运动测试结果（用于风险分层）
            non_exercise_results: 非运动测试结果（用于风险分层）
            has_cardiac_surgery: 是否有心脏手术史
            surgery_weeks_ago: 手术后周数
            has_balance_issues: 是否有平衡问题
            has_fall_history: 是否有跌倒史
            prescribing_physician: 开具处方的医生
            validity_weeks: 处方有效期（周）
        """
        # 1. 风险分层
        risk_level = self.risk_stratifier.stratify(
            exercise_test_results, non_exercise_results, patient_info
        )
        risk_description = self._get_risk_description(risk_level)
        monitoring_rec = self.risk_stratifier.get_monitoring_recommendation(risk_level)
        
        # 2. 生成有氧运动处方
        aerobic = self.aerobic_generator.generate(
            cpet_results=cpet_results,
            risk_level=risk_level,
            patient_weight_kg=patient_info.weight_kg,
            is_initial=True,
        )
        
        # 3. 生成抗阻训练处方
        resistance = self.resistance_generator.generate(
            risk_level=risk_level,
            patient_age=patient_info.age,
            has_cardiac_surgery=has_cardiac_surgery,
            surgery_weeks_ago=surgery_weeks_ago,
            has_pacemaker=patient_info.has_pacemaker,
            has_orthopedic_issues=patient_info.has_orthopedic_issues,
        )
        
        # 4. 生成柔韧性训练处方
        flexibility = self.flexibility_generator.generate(
            risk_level=risk_level,
            patient_age=patient_info.age,
            has_cardiac_surgery=has_cardiac_surgery,
            surgery_weeks_ago=surgery_weeks_ago,
        )
        
        # 5. 生成神经肌肉训练处方
        neuromuscular = self.neuromuscular_generator.generate(
            risk_level=risk_level,
            patient_age=patient_info.age,
            has_balance_issues=has_balance_issues,
            has_fall_history=has_fall_history,
        )
        
        # 6. 生成周计划
        weekly_schedule = self._generate_weekly_schedule(
            risk_level, aerobic, resistance
        )
        
        # 7. 生成总体注意事项
        general_precautions = self._generate_general_precautions(
            risk_level, patient_info
        )
        
        # 8. 生成紧急情况处理指南
        emergency_instructions = self._generate_emergency_instructions()
        
        # 9. 生成随访建议
        follow_up = self._generate_follow_up_recommendation(risk_level)
        
        # 生成时间
        now = datetime.now()
        from datetime import timedelta
        valid_until = now + timedelta(weeks=validity_weeks)
        
        return ExercisePrescription(
            patient_name=f"{patient_info.sex}性, {patient_info.age}岁",
            patient_id="",  # 需要外部提供
            generated_at=now,
            valid_until=valid_until,
            risk_level=risk_level,
            risk_description=risk_description,
            monitoring_recommendation=monitoring_rec,
            aerobic=aerobic,
            resistance=resistance,
            flexibility=flexibility,
            neuromuscular=neuromuscular,
            weekly_schedule=weekly_schedule,
            general_precautions=general_precautions,
            emergency_instructions=emergency_instructions,
            follow_up_recommendation=follow_up,
            prescribing_physician=prescribing_physician,
        )
    
    def _get_risk_description(self, risk_level: RiskLevel) -> str:
        """获取风险等级描述"""
        descriptions = {
            RiskLevel.LOW: (
                "低危：运动测试结果良好，无复杂心律失常，无症状，"
                "血流动力学反应正常，运动能力≥7 MET，心功能正常。"
                "可在较少监护下进行运动康复。"
            ),
            RiskLevel.MODERATE: (
                "中危：运动测试中出现轻度异常，如中等强度运动时出现症状、"
                "轻度ST段改变或运动能力受限。需要适当监护下进行运动康复。"
            ),
            RiskLevel.HIGH: (
                "高危：存在复杂心律失常、低强度运动即出现症状、"
                "明显心肌缺血改变或血流动力学异常。"
                "必须在严密监护下进行运动康复。"
            ),
        }
        return descriptions[risk_level]
    
    def _generate_weekly_schedule(
        self,
        risk_level: RiskLevel,
        aerobic: AerobicPrescription,
        resistance: ResistancePrescription,
    ) -> List[dict]:
        """生成周训练计划"""
        if risk_level == RiskLevel.HIGH:
            return [
                {"day": "周一", "activities": ["有氧运动（监护下）", "柔韧性训练"]},
                {"day": "周二", "activities": ["休息或轻度活动"]},
                {"day": "周三", "activities": ["有氧运动（监护下）", "抗阻训练"]},
                {"day": "周四", "activities": ["休息或轻度活动"]},
                {"day": "周五", "activities": ["有氧运动（监护下）", "柔韧性训练"]},
                {"day": "周六", "activities": ["休息"]},
                {"day": "周日", "activities": ["休息或轻度散步"]},
            ]
        elif risk_level == RiskLevel.MODERATE:
            return [
                {"day": "周一", "activities": ["有氧运动", "柔韧性训练"]},
                {"day": "周二", "activities": ["抗阻训练", "神经肌肉训练"]},
                {"day": "周三", "activities": ["有氧运动", "柔韧性训练"]},
                {"day": "周四", "activities": ["休息或轻度活动"]},
                {"day": "周五", "activities": ["有氧运动", "抗阻训练"]},
                {"day": "周六", "activities": ["神经肌肉训练（如太极拳）"]},
                {"day": "周日", "activities": ["休息或轻度散步"]},
            ]
        else:
            return [
                {"day": "周一", "activities": ["有氧运动", "柔韧性训练"]},
                {"day": "周二", "activities": ["抗阻训练", "神经肌肉训练"]},
                {"day": "周三", "activities": ["有氧运动", "柔韧性训练"]},
                {"day": "周四", "activities": ["抗阻训练", "神经肌肉训练"]},
                {"day": "周五", "activities": ["有氧运动", "柔韧性训练"]},
                {"day": "周六", "activities": ["有氧运动或户外活动"]},
                {"day": "周日", "activities": ["休息或轻度活动"]},
            ]
    
    def _generate_general_precautions(
        self,
        risk_level: RiskLevel,
        patient_info: PatientInfo,
    ) -> List[str]:
        """生成总体注意事项"""
        precautions = [
            "运动前后测量血压和心率，记录运动日志",
            "运动时佩戴心率监测设备",
            "保持适当水分摄入，避免脱水",
            "避免在极端天气（过热、过冷）下运动",
            "避免空腹或饱餐后立即运动",
            "穿着舒适、透气的运动服装和合适的运动鞋",
            "循序渐进，不要急于求成",
        ]
        
        if risk_level == RiskLevel.HIGH:
            precautions.insert(0, "必须在有医护人员和心电监护的环境下进行运动")
            precautions.append("随身携带急救药物和紧急联系方式")
        
        if patient_info.has_diabetes:
            precautions.append("糖尿病患者注意监测血糖，避免低血糖")
        
        if patient_info.has_hypertension:
            precautions.append("高血压患者运动前确保血压控制良好")
        
        if patient_info.age >= 65:
            precautions.append("老年患者注意防跌倒，建议有人陪同")
        
        return precautions
    
    def _generate_emergency_instructions(self) -> List[str]:
        """生成紧急情况处理指南"""
        return [
            "如出现以下症状，立即停止运动并寻求帮助：",
            "• 胸痛、胸闷或压迫感",
            "• 严重呼吸困难",
            "• 头晕、眩晕或即将晕厥感",
            "• 心悸或心跳不规则",
            "• 恶心、呕吐或冷汗",
            "• 视物模糊或意识改变",
            "",
            "紧急处理步骤：",
            "1. 立即停止运动，坐下或躺下休息",
            "2. 如有硝酸甘油，舌下含服",
            "3. 拨打急救电话 120",
            "4. 如有AED设备且患者无反应，按指示使用",
        ]
    
    def _generate_follow_up_recommendation(self, risk_level: RiskLevel) -> str:
        """生成随访建议"""
        if risk_level == RiskLevel.HIGH:
            return (
                "建议 2 周后复诊评估运动耐受情况，"
                "4 周后复查心肺运动试验，根据结果调整运动处方。"
                "如有任何不适，随时就诊。"
            )
        elif risk_level == RiskLevel.MODERATE:
            return (
                "建议 4 周后复诊评估运动进展，"
                "复查心肺运动试验，根据结果调整运动处方。"
                "如有任何不适，及时就诊。"
            )
        else:
            return (
                "建议 4-6 周后复诊评估运动进展，"
                "可根据情况复查心肺运动试验。"
                "保持良好的运动习惯，定期随访。"
            )
    
    def generate_summary_text(self, prescription: ExercisePrescription) -> str:
        """生成处方摘要文本"""
        lines = [
            "=" * 60,
            "个性化运动处方",
            "=" * 60,
            f"生成日期: {prescription.generated_at.strftime('%Y-%m-%d')}",
            f"有效期至: {prescription.valid_until.strftime('%Y-%m-%d')}",
            "",
            f"【风险分层】{prescription.risk_level.value.upper()}",
            prescription.risk_description,
            "",
            "【有氧运动】",
            f"频率: {prescription.aerobic.frequency_description}",
            f"强度: {prescription.aerobic.intensity_description}",
            f"时间: {prescription.aerobic.time_description}",
            f"类型: {prescription.aerobic.type_description}",
            "",
            "【抗阻训练】",
            f"频率: {prescription.resistance.frequency_description}",
            f"强度: {prescription.resistance.intensity_description}",
            "",
            "【柔韧性训练】",
            f"频率: {prescription.flexibility.frequency_description}",
            f"时机: {prescription.flexibility.timing_description}",
            "",
            "【神经肌肉训练】",
            f"频率: {prescription.neuromuscular.frequency_description}",
            f"推荐活动: {', '.join(prescription.neuromuscular.recommended_activities)}",
            "",
            "【周训练计划】",
        ]
        
        for day in prescription.weekly_schedule:
            lines.append(f"{day['day']}: {', '.join(day['activities'])}")
        
        lines.extend([
            "",
            "【注意事项】",
        ])
        for p in prescription.general_precautions[:5]:
            lines.append(f"• {p}")
        
        lines.extend([
            "",
            "【随访建议】",
            prescription.follow_up_recommendation,
            "",
            "=" * 60,
        ])
        
        if prescription.prescribing_physician:
            lines.append(f"开具医生: {prescription.prescribing_physician}")
        
        return "\n".join(lines)
