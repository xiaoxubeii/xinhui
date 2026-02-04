# -*- coding: utf-8 -*-
"""
抗阻训练处方模块

基于《心血管疾病患者门诊运动康复专家共识》实现的抗阻训练处方生成。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .risk_stratification import RiskLevel


class MuscleGroup(Enum):
    """肌肉群"""
    CHEST = "chest"           # 胸部
    SHOULDERS = "shoulders"   # 肩部
    UPPER_BACK = "upper_back" # 上背部
    LOWER_BACK = "lower_back" # 下背部
    ABDOMEN = "abdomen"       # 腹部
    GLUTES = "glutes"         # 臀部
    QUADRICEPS = "quadriceps" # 股四头肌
    HAMSTRINGS = "hamstrings" # 腘绳肌
    CALVES = "calves"         # 小腿
    BICEPS = "biceps"         # 肱二头肌
    TRICEPS = "triceps"       # 肱三头肌


@dataclass
class ResistanceExercise:
    """单项抗阻训练"""
    name: str
    muscle_groups: List[MuscleGroup]
    sets: int
    repetitions: int
    intensity_percent_1rm: float  # 1RM百分比
    rest_seconds: int  # 组间休息时间
    description: str
    precautions: List[str] = field(default_factory=list)


@dataclass
class ResistancePrescription:
    """抗阻训练处方"""
    frequency_per_week: int
    frequency_description: str
    
    intensity_percent_1rm: tuple  # (min, max) 1RM百分比
    intensity_rpe: tuple  # RPE范围
    intensity_description: str
    
    sets_per_exercise: int
    repetitions_per_set: tuple  # (min, max)
    rest_between_sets_seconds: int
    
    exercises: List[ResistanceExercise]
    
    progression_description: str
    precautions: List[str]
    contraindications: List[str]


class ResistancePrescriptionGenerator:
    """抗阻训练处方生成器"""
    
    # 标准抗阻训练动作库
    EXERCISE_LIBRARY = {
        "seated_chest_press": ResistanceExercise(
            name="坐位胸部推举",
            muscle_groups=[MuscleGroup.CHEST, MuscleGroup.TRICEPS, MuscleGroup.SHOULDERS],
            sets=2, repetitions=12,
            intensity_percent_1rm=50,
            rest_seconds=60,
            description="坐姿，双手握住把手，向前推出至手臂伸直，缓慢收回",
            precautions=["避免憋气", "保持背部贴紧靠背"],
        ),
        "seated_shoulder_press": ResistanceExercise(
            name="坐位肩部推举",
            muscle_groups=[MuscleGroup.SHOULDERS, MuscleGroup.TRICEPS],
            sets=2, repetitions=12,
            intensity_percent_1rm=50,
            rest_seconds=60,
            description="坐姿，双手握住把手，向上推举至手臂伸直，缓慢放下",
            precautions=["避免耸肩", "保持核心稳定"],
        ),
        "triceps_extension": ResistanceExercise(
            name="肱三头肌伸展",
            muscle_groups=[MuscleGroup.TRICEPS],
            sets=2, repetitions=12,
            intensity_percent_1rm=40,
            rest_seconds=60,
            description="坐姿或站姿，手持哑铃或使用绳索，伸展手臂",
            precautions=["保持上臂固定", "动作缓慢控制"],
        ),
        "biceps_curl": ResistanceExercise(
            name="肱二头肌屈曲",
            muscle_groups=[MuscleGroup.BICEPS],
            sets=2, repetitions=12,
            intensity_percent_1rm=40,
            rest_seconds=60,
            description="站姿或坐姿，手持哑铃，屈肘将重量举起",
            precautions=["避免借力摆动", "保持肘部固定"],
        ),
        "lat_pulldown": ResistanceExercise(
            name="上背部下拉",
            muscle_groups=[MuscleGroup.UPPER_BACK, MuscleGroup.BICEPS],
            sets=2, repetitions=12,
            intensity_percent_1rm=50,
            rest_seconds=60,
            description="坐姿，双手握住横杆，向下拉至胸前，缓慢放回",
            precautions=["避免身体后仰过度", "感受背部发力"],
        ),
        "back_extension": ResistanceExercise(
            name="下背部伸展",
            muscle_groups=[MuscleGroup.LOWER_BACK, MuscleGroup.GLUTES],
            sets=2, repetitions=10,
            intensity_percent_1rm=40,
            rest_seconds=60,
            description="俯卧位，缓慢抬起上半身，保持数秒后放下",
            precautions=["动作幅度不宜过大", "有腰椎问题者慎做"],
        ),
        "abdominal_crunch": ResistanceExercise(
            name="腹部卷曲",
            muscle_groups=[MuscleGroup.ABDOMEN],
            sets=2, repetitions=15,
            intensity_percent_1rm=0,  # 自重
            rest_seconds=45,
            description="仰卧位，双手置于胸前或头后，卷曲上半身",
            precautions=["避免拉扯颈部", "呼气时卷曲"],
        ),
        "leg_press": ResistanceExercise(
            name="腿部推举",
            muscle_groups=[MuscleGroup.QUADRICEPS, MuscleGroup.GLUTES, MuscleGroup.HAMSTRINGS],
            sets=2, repetitions=12,
            intensity_percent_1rm=60,
            rest_seconds=90,
            description="坐姿，双脚置于踏板，推出至腿部伸直（不锁死），缓慢收回",
            precautions=["膝盖不要完全锁死", "保持背部贴紧靠背"],
        ),
        "leg_extension": ResistanceExercise(
            name="股四头肌伸展",
            muscle_groups=[MuscleGroup.QUADRICEPS],
            sets=2, repetitions=12,
            intensity_percent_1rm=50,
            rest_seconds=60,
            description="坐姿，伸直膝关节抬起小腿，缓慢放下",
            precautions=["避免过度伸展", "有膝关节问题者减轻重量"],
        ),
        "leg_curl": ResistanceExercise(
            name="腘绳肌腿部卷曲",
            muscle_groups=[MuscleGroup.HAMSTRINGS],
            sets=2, repetitions=12,
            intensity_percent_1rm=50,
            rest_seconds=60,
            description="俯卧或坐姿，屈膝将小腿向后卷曲",
            precautions=["动作缓慢控制", "避免借力"],
        ),
        "calf_raise": ResistanceExercise(
            name="踮脚/提踵",
            muscle_groups=[MuscleGroup.CALVES],
            sets=2, repetitions=15,
            intensity_percent_1rm=50,
            rest_seconds=45,
            description="站立，踮起脚尖，保持数秒后放下",
            precautions=["可扶墙保持平衡", "动作缓慢"],
        ),
    }
    
    def __init__(self):
        pass
    
    def generate(
        self,
        risk_level: RiskLevel,
        patient_age: int,
        has_cardiac_surgery: bool = False,
        surgery_weeks_ago: Optional[int] = None,
        has_pacemaker: bool = False,
        has_orthopedic_issues: bool = False,
    ) -> ResistancePrescription:
        """
        生成抗阻训练处方
        
        Args:
            risk_level: 风险分层等级
            patient_age: 患者年龄
            has_cardiac_surgery: 是否有心脏手术史
            surgery_weeks_ago: 手术后周数
            has_pacemaker: 是否有起搏器
            has_orthopedic_issues: 是否有骨科问题
        """
        # 检查是否可以开始抗阻训练
        can_start, delay_reason = self._check_start_eligibility(
            has_cardiac_surgery, surgery_weeks_ago, has_pacemaker
        )
        
        if not can_start:
            return self._generate_delayed_prescription(delay_reason)
        
        # 确定训练参数
        frequency = self._determine_frequency(risk_level)
        intensity = self._determine_intensity(risk_level, patient_age)
        exercises = self._select_exercises(
            risk_level, has_pacemaker, has_orthopedic_issues
        )
        
        # 调整运动参数
        adjusted_exercises = self._adjust_exercise_params(
            exercises, intensity, risk_level, patient_age
        )
        
        progression = self._generate_progression(risk_level)
        precautions = self._generate_precautions(
            risk_level, has_pacemaker, has_cardiac_surgery
        )
        
        return ResistancePrescription(
            frequency_per_week=frequency["per_week"],
            frequency_description=frequency["description"],
            intensity_percent_1rm=intensity["percent_1rm"],
            intensity_rpe=intensity["rpe"],
            intensity_description=intensity["description"],
            sets_per_exercise=intensity["sets"],
            repetitions_per_set=intensity["repetitions"],
            rest_between_sets_seconds=intensity["rest_seconds"],
            exercises=adjusted_exercises,
            progression_description=progression,
            precautions=precautions["precautions"],
            contraindications=precautions["contraindications"],
        )
    
    def _check_start_eligibility(
        self,
        has_cardiac_surgery: bool,
        surgery_weeks_ago: Optional[int],
        has_pacemaker: bool,
    ) -> tuple:
        """检查是否可以开始抗阻训练"""
        if has_cardiac_surgery and surgery_weeks_ago is not None:
            # 冠状动脉旁路移植术后需等待5周
            if surgery_weeks_ago < 5:
                return False, f"心脏手术后需等待至少5周，目前仅{surgery_weeks_ago}周"
            # 典型上肢阻力训练需等待3个月
            if surgery_weeks_ago < 12:
                return True, "可进行轻量级训练(0.5-1.5kg)，典型抗阻训练需等待术后3个月"
        
        if has_pacemaker:
            # 起搏器植入后2周内避免抬高手臂
            return True, "起搏器植入侧手臂2周内避免抬高至肩以上"
        
        return True, None
    
    def _generate_delayed_prescription(self, reason: str) -> ResistancePrescription:
        """生成延迟开始的处方"""
        return ResistancePrescription(
            frequency_per_week=0,
            frequency_description=f"暂不建议开始抗阻训练：{reason}",
            intensity_percent_1rm=(0, 0),
            intensity_rpe=(0, 0),
            intensity_description="待条件满足后再开始",
            sets_per_exercise=0,
            repetitions_per_set=(0, 0),
            rest_between_sets_seconds=0,
            exercises=[],
            progression_description="请遵医嘱，待恢复期满后再开始抗阻训练",
            precautions=[reason],
            contraindications=["当前阶段不宜进行抗阻训练"],
        )
    
    def _determine_frequency(self, risk_level: RiskLevel) -> dict:
        """确定训练频率"""
        return {
            "per_week": 2,
            "description": "每周 2-3 次，非连续日进行，确保肌肉有充分恢复时间",
        }
    
    def _determine_intensity(self, risk_level: RiskLevel, age: int) -> dict:
        """确定训练强度"""
        # 老年人或高危患者使用更低强度
        if age >= 60 or risk_level == RiskLevel.HIGH:
            return {
                "percent_1rm": (30, 40),
                "rpe": (10, 12),
                "sets": 1,
                "repetitions": (12, 15),
                "rest_seconds": 90,
                "description": (
                    "低强度抗阻训练，使用 30-40% 1RM 或能完成 12-15 次的重量，"
                    "RPE 10-12 分（轻松至略感费力），每个动作 1 组"
                ),
            }
        elif risk_level == RiskLevel.MODERATE:
            return {
                "percent_1rm": (40, 50),
                "rpe": (11, 13),
                "sets": 2,
                "repetitions": (10, 12),
                "rest_seconds": 60,
                "description": (
                    "中低强度抗阻训练，使用 40-50% 1RM，"
                    "RPE 11-13 分（轻松至有些费力），每个动作 2 组"
                ),
            }
        else:
            return {
                "percent_1rm": (40, 60),
                "rpe": (11, 14),
                "sets": 2,
                "repetitions": (10, 15),
                "rest_seconds": 60,
                "description": (
                    "中等强度抗阻训练，使用 40-60% 1RM，"
                    "RPE 11-14 分，每个动作 2-3 组"
                ),
            }
    
    def _select_exercises(
        self,
        risk_level: RiskLevel,
        has_pacemaker: bool,
        has_orthopedic_issues: bool,
    ) -> List[ResistanceExercise]:
        """选择训练动作"""
        # 基础动作（覆盖主要肌群）
        base_exercises = [
            "seated_chest_press",
            "seated_shoulder_press",
            "lat_pulldown",
            "abdominal_crunch",
            "leg_press",
            "leg_curl",
            "calf_raise",
        ]
        
        # 高危患者减少动作数量
        if risk_level == RiskLevel.HIGH:
            base_exercises = [
                "seated_chest_press",
                "lat_pulldown",
                "leg_press",
                "calf_raise",
            ]
        
        # 起搏器患者避免某些上肢动作
        if has_pacemaker:
            # 移除可能影响起搏器侧的动作
            base_exercises = [e for e in base_exercises 
                           if e not in ["seated_shoulder_press"]]
        
        # 骨科问题患者调整
        if has_orthopedic_issues:
            # 移除可能加重关节负担的动作
            base_exercises = [e for e in base_exercises 
                           if e not in ["leg_extension"]]
        
        return [self.EXERCISE_LIBRARY[name] for name in base_exercises 
                if name in self.EXERCISE_LIBRARY]
    
    def _adjust_exercise_params(
        self,
        exercises: List[ResistanceExercise],
        intensity: dict,
        risk_level: RiskLevel,
        age: int,
    ) -> List[ResistanceExercise]:
        """调整运动参数"""
        adjusted = []
        for ex in exercises:
            # 创建新的运动对象，调整参数
            new_ex = ResistanceExercise(
                name=ex.name,
                muscle_groups=ex.muscle_groups,
                sets=intensity["sets"],
                repetitions=intensity["repetitions"][1],  # 使用上限
                intensity_percent_1rm=intensity["percent_1rm"][0],  # 使用下限开始
                rest_seconds=intensity["rest_seconds"],
                description=ex.description,
                precautions=ex.precautions.copy(),
            )
            adjusted.append(new_ex)
        return adjusted
    
    def _generate_progression(self, risk_level: RiskLevel) -> str:
        """生成进阶建议"""
        return (
            "进阶原则：\n"
            "1. 首先增加重复次数：当能轻松完成规定次数上限时\n"
            "2. 然后增加组数：从 1 组增加到 2-3 组\n"
            "3. 最后增加重量：每次增加 2-5%，上肢增加 0.5-1kg，下肢增加 1-2.5kg\n"
            "4. 每次只调整一个参数\n"
            "5. 如出现过度疲劳或不适，应降低强度"
        )
    
    def _generate_precautions(
        self,
        risk_level: RiskLevel,
        has_pacemaker: bool,
        has_cardiac_surgery: bool,
    ) -> dict:
        """生成注意事项"""
        precautions = [
            "保持正确的呼吸模式：用力时呼气，放松时吸气",
            "避免 Valsalva 动作（憋气用力）",
            "动作缓慢、有控制，避免快速或爆发性动作",
            "交替进行上半身和下半身运动，使肌肉充分休息",
            "运动前先进行有氧热身",
            "如出现头晕、胸闷、心悸等症状立即停止",
        ]
        
        if has_pacemaker:
            precautions.append("起搏器植入侧手臂避免过度用力或抬高过肩")
        
        if has_cardiac_surgery:
            precautions.append("心脏手术后 3 个月内避免胸部拉伸动作")
        
        if risk_level == RiskLevel.HIGH:
            precautions.append("必须在有监护条件下进行训练")
        
        contraindications = [
            "急性心血管事件发作期",
            "未控制的高血压（>200/100 mmHg）",
            "严重心律失常",
            "急性感染或发热",
        ]
        
        return {
            "precautions": precautions,
            "contraindications": contraindications,
        }
