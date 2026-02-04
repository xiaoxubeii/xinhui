# -*- coding: utf-8 -*-
"""
风险分层模块

基于《心血管疾病患者门诊运动康复专家共识》表2实现的风险分层算法。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class RiskLevel(Enum):
    """运动训练风险等级"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass
class ExerciseTestResults:
    """运动测试结果"""
    # 运动能力
    max_mets: Optional[float] = None  # 最大代谢当量
    vo2_peak: Optional[float] = None  # 峰值摄氧量 (ml/kg/min)
    max_workload: Optional[float] = None  # 最大功率 (W)
    
    # 心律失常
    has_complex_arrhythmia: bool = False  # 复杂室性心律失常
    arrhythmia_during_exercise: bool = False  # 运动中出现心律失常
    arrhythmia_during_recovery: bool = False  # 恢复期出现心律失常
    
    # 症状
    has_angina: bool = False  # 心绞痛
    has_dyspnea: bool = False  # 呼吸困难
    has_dizziness: bool = False  # 头晕/眩晕
    symptom_onset_mets: Optional[float] = None  # 症状出现时的 MET
    
    # 心电图改变
    st_depression_mm: float = 0.0  # ST段压低 (mm)
    has_ischemia: bool = False  # 心肌缺血
    
    # 血流动力学
    has_abnormal_hr_response: bool = False  # 心率反应异常（变时功能不全）
    has_abnormal_bp_response: bool = False  # 血压反应异常（负荷增加时收缩压不升反降）
    has_post_exercise_hypotension: bool = False  # 运动后低血压


@dataclass
class NonExerciseTestResults:
    """非运动测试结果"""
    # 心功能
    lvef: Optional[float] = None  # 左心室射血分数 (%)
    
    # 病史
    has_cardiac_arrest_history: bool = False  # 心脏骤停/猝死病史
    has_mi_with_complications: bool = False  # 心肌梗死合并心源性休克或心衰
    has_complex_revascularization: bool = False  # 复杂冠状动脉血管重建手术
    has_chf: bool = False  # 慢性心力衰竭
    has_ischemia_symptoms: bool = False  # 心肌缺血症状
    has_clinical_depression: bool = False  # 临床抑郁症
    
    # 心律失常
    has_resting_arrhythmia: bool = False  # 静息时复杂室性心律失常


@dataclass
class PatientInfo:
    """患者基本信息"""
    age: int
    sex: str  # "male" or "female"
    height_cm: float
    weight_kg: float
    
    # 诊断
    diagnosis: List[str] = field(default_factory=list)
    
    # 心血管危险因素
    has_hypertension: bool = False
    has_diabetes: bool = False
    has_obesity: bool = False  # BMI >= 28
    is_sedentary: bool = False
    is_smoker: bool = False
    has_hyperlipidemia: bool = False
    has_family_history: bool = False
    
    # 合并症
    has_copd: bool = False
    has_renal_insufficiency: bool = False
    has_neurological_disease: bool = False
    has_anemia: bool = False
    has_orthopedic_issues: bool = False
    is_frail: bool = False
    has_sleep_apnea: bool = False
    
    # 植入器械
    has_pacemaker: bool = False
    has_icd: bool = False
    has_crt: bool = False
    
    @property
    def bmi(self) -> float:
        return self.weight_kg / (self.height_cm / 100) ** 2


class RiskStratifier:
    """
    风险分层器
    
    基于美国心血管与肺康复协会(AACVPR)制定的风险分层标准，
    评估患者运动训练期间发生心脏事件的风险。
    """
    
    def __init__(self):
        pass
    
    def stratify(
        self,
        exercise_results: ExerciseTestResults,
        non_exercise_results: NonExerciseTestResults,
        patient_info: Optional[PatientInfo] = None,
    ) -> RiskLevel:
        """
        进行风险分层
        
        Returns:
            RiskLevel: LOW, MODERATE, or HIGH
        """
        # 检查高危条件
        if self._is_high_risk(exercise_results, non_exercise_results):
            return RiskLevel.HIGH
        
        # 检查中危条件
        if self._is_moderate_risk(exercise_results, non_exercise_results):
            return RiskLevel.MODERATE
        
        # 检查低危条件
        if self._is_low_risk(exercise_results, non_exercise_results):
            return RiskLevel.LOW
        
        # 默认中危
        return RiskLevel.MODERATE
    
    def _is_high_risk(
        self,
        ex: ExerciseTestResults,
        non_ex: NonExerciseTestResults,
    ) -> bool:
        """检查是否为高危"""
        # 运动测试高危条件
        exercise_high_risk = any([
            # 运动测试或恢复期出现复杂室性心律失常
            ex.has_complex_arrhythmia,
            # 低强度(<5 MET)运动中出现症状
            (ex.symptom_onset_mets is not None and ex.symptom_onset_mets < 5.0 and 
             (ex.has_angina or ex.has_dyspnea or ex.has_dizziness)),
            # 明显心电图缺血改变(ST段压低≥2mm)
            ex.st_depression_mm >= 2.0,
            # 血流动力学异常
            ex.has_abnormal_hr_response or ex.has_abnormal_bp_response,
            # 严重运动后低血压
            ex.has_post_exercise_hypotension,
        ])
        
        # 非运动测试高危条件
        non_exercise_high_risk = any([
            # LVEF < 40%
            non_ex.lvef is not None and non_ex.lvef < 40,
            # 心脏骤停或猝死病史
            non_ex.has_cardiac_arrest_history,
            # 静息时复杂性心律失常
            non_ex.has_resting_arrhythmia,
            # 心肌梗死合并心源性休克或心衰
            non_ex.has_mi_with_complications,
            # 复杂冠状动脉血管重建手术
            non_ex.has_complex_revascularization,
            # 合并慢性心力衰竭
            non_ex.has_chf,
            # 合并心肌缺血症状
            non_ex.has_ischemia_symptoms,
            # 存在临床抑郁症
            non_ex.has_clinical_depression,
        ])
        
        return exercise_high_risk or non_exercise_high_risk
    
    def _is_moderate_risk(
        self,
        ex: ExerciseTestResults,
        non_ex: NonExerciseTestResults,
    ) -> bool:
        """检查是否为中危"""
        # 运动测试中危条件
        exercise_moderate_risk = any([
            # 中高强度(5-6.9 MET)运动中出现症状
            (ex.symptom_onset_mets is not None and 
             5.0 <= ex.symptom_onset_mets < 7.0 and
             (ex.has_angina or ex.has_dyspnea or ex.has_dizziness)),
            # 轻至中度心电图缺血改变(ST段压低<2mm)
            0 < ex.st_depression_mm < 2.0,
            # 最大负荷 < 5 MET
            ex.max_mets is not None and ex.max_mets < 5.0,
        ])
        
        # 非运动测试中危条件
        non_exercise_moderate_risk = (
            non_ex.lvef is not None and 40 <= non_ex.lvef < 50
        )
        
        return exercise_moderate_risk or non_exercise_moderate_risk
    
    def _is_low_risk(
        self,
        ex: ExerciseTestResults,
        non_ex: NonExerciseTestResults,
    ) -> bool:
        """检查是否为低危"""
        # 运动测试低危条件（需全部满足）
        exercise_low_risk = all([
            # 无复杂室性心律失常
            not ex.has_complex_arrhythmia,
            not ex.arrhythmia_during_exercise,
            not ex.arrhythmia_during_recovery,
            # 无心绞痛、呼吸困难、头晕
            not ex.has_angina,
            not ex.has_dyspnea,
            not ex.has_dizziness,
            # 血流动力学反应正常
            not ex.has_abnormal_hr_response,
            not ex.has_abnormal_bp_response,
            # 最大负荷 >= 7 MET
            ex.max_mets is not None and ex.max_mets >= 7.0,
        ])
        
        # 非运动测试低危条件（需全部满足）
        non_exercise_low_risk = all([
            # LVEF >= 50%
            non_ex.lvef is None or non_ex.lvef >= 50,
            # 无心衰
            not non_ex.has_chf,
            # 无缺血症状
            not non_ex.has_ischemia_symptoms,
            # 无静息心律失常
            not non_ex.has_resting_arrhythmia,
            # 无临床抑郁症
            not non_ex.has_clinical_depression,
        ])
        
        return exercise_low_risk and non_exercise_low_risk
    
    def get_monitoring_recommendation(self, risk_level: RiskLevel) -> dict:
        """
        获取监护建议
        
        基于风险分层给出运动康复的监护建议。
        """
        recommendations = {
            RiskLevel.LOW: {
                "start_timing": "心脏事件或手术后 30 天内",
                "supervised_sessions": "6-18 次有心电监护的有氧运动",
                "transition": "逐渐过渡到居家康复",
                "monitoring": "运动过程中心电图和血流动力学正常时可逐渐增加强度",
            },
            RiskLevel.MODERATE: {
                "start_timing": "心脏事件或手术后 60 天内",
                "supervised_sessions": "12-24 次有医护和心电监护的有氧运动",
                "transition": "逐渐过渡到居家康复",
                "monitoring": "需持续监测，出现异常需降低强度或重新评估",
            },
            RiskLevel.HIGH: {
                "start_timing": "心脏事件或手术后 90 天内",
                "supervised_sessions": "18-36 次有心电监护的有氧运动",
                "transition": "需专业评估确认安全性后方可过渡",
                "monitoring": "出现异常需立即重新评估，可能需中止训练",
            },
        }
        return recommendations[risk_level]
