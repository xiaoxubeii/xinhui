# -*- coding: utf-8 -*-
"""
柔韧性训练和神经肌肉训练处方模块

基于《心血管疾病患者门诊运动康复专家共识》实现。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .risk_stratification import RiskLevel


class StretchType(Enum):
    """拉伸类型"""
    DYNAMIC = "dynamic"  # 动态拉伸
    STATIC_ACTIVE = "static_active"  # 主动静态拉伸
    STATIC_PASSIVE = "static_passive"  # 被动静态拉伸
    PNF = "pnf"  # 本体感觉神经肌肉促进技术


class BodyRegion(Enum):
    """身体部位"""
    NECK = "neck"
    SHOULDERS = "shoulders"
    CHEST = "chest"
    UPPER_BACK = "upper_back"
    LOWER_BACK = "lower_back"
    HIPS = "hips"
    QUADRICEPS = "quadriceps"
    HAMSTRINGS = "hamstrings"
    CALVES = "calves"


@dataclass
class StretchExercise:
    """拉伸动作"""
    name: str
    body_region: BodyRegion
    stretch_type: StretchType
    hold_seconds: int
    repetitions: int
    description: str
    precautions: List[str] = field(default_factory=list)


@dataclass
class FlexibilityPrescription:
    """柔韧性训练处方"""
    frequency_per_week: int
    frequency_description: str
    
    duration_per_stretch_seconds: tuple  # (min, max)
    total_duration_minutes: int
    
    stretch_types: List[StretchType]
    exercises: List[StretchExercise]
    
    timing_description: str  # 何时进行
    progression_description: str
    precautions: List[str]
    contraindications: List[str]


@dataclass
class NeuromuscularExercise:
    """神经肌肉训练动作"""
    name: str
    category: str  # balance, coordination, proprioception
    duration_seconds: int
    repetitions: int
    description: str
    difficulty_level: int  # 1-5
    precautions: List[str] = field(default_factory=list)


@dataclass
class NeuromuscularPrescription:
    """神经肌肉训练处方"""
    frequency_per_week: int
    frequency_description: str
    
    total_duration_minutes_per_week: int
    session_duration_minutes: int
    
    exercises: List[NeuromuscularExercise]
    
    progression_description: str
    precautions: List[str]
    recommended_activities: List[str]  # 如太极拳


class FlexibilityPrescriptionGenerator:
    """柔韧性训练处方生成器"""
    
    # 标准拉伸动作库
    STRETCH_LIBRARY = {
        "neck_rotation": StretchExercise(
            name="颈部旋转",
            body_region=BodyRegion.NECK,
            stretch_type=StretchType.DYNAMIC,
            hold_seconds=0,
            repetitions=10,
            description="缓慢转动头部，左右各转动，动作轻柔",
            precautions=["动作缓慢", "如有颈椎问题请咨询医生"],
        ),
        "neck_side_stretch": StretchExercise(
            name="颈部侧向拉伸",
            body_region=BodyRegion.NECK,
            stretch_type=StretchType.STATIC_ACTIVE,
            hold_seconds=15,
            repetitions=2,
            description="头部向一侧倾斜，感受对侧颈部拉伸",
            precautions=["不要用力拉扯"],
        ),
        "shoulder_circles": StretchExercise(
            name="肩部环绕",
            body_region=BodyRegion.SHOULDERS,
            stretch_type=StretchType.DYNAMIC,
            hold_seconds=0,
            repetitions=10,
            description="双肩向前、向上、向后、向下环绕",
            precautions=["动作幅度适中"],
        ),
        "chest_stretch": StretchExercise(
            name="胸部拉伸",
            body_region=BodyRegion.CHEST,
            stretch_type=StretchType.STATIC_ACTIVE,
            hold_seconds=20,
            repetitions=2,
            description="双手在背后交叉，挺胸，感受胸部拉伸",
            precautions=["心脏手术后3个月内避免"],
        ),
        "upper_back_stretch": StretchExercise(
            name="上背部拉伸",
            body_region=BodyRegion.UPPER_BACK,
            stretch_type=StretchType.STATIC_ACTIVE,
            hold_seconds=20,
            repetitions=2,
            description="双手前伸，含胸弓背，感受上背部拉伸",
            precautions=[],
        ),
        "lower_back_stretch": StretchExercise(
            name="下背部拉伸",
            body_region=BodyRegion.LOWER_BACK,
            stretch_type=StretchType.STATIC_ACTIVE,
            hold_seconds=20,
            repetitions=2,
            description="仰卧，双膝抱胸，轻轻摇晃",
            precautions=["有腰椎问题者动作轻柔"],
        ),
        "hip_flexor_stretch": StretchExercise(
            name="髋屈肌拉伸",
            body_region=BodyRegion.HIPS,
            stretch_type=StretchType.STATIC_ACTIVE,
            hold_seconds=20,
            repetitions=2,
            description="弓步姿势，后腿膝盖着地，感受髋前部拉伸",
            precautions=["保持平衡", "可扶墙进行"],
        ),
        "quadriceps_stretch": StretchExercise(
            name="股四头肌拉伸",
            body_region=BodyRegion.QUADRICEPS,
            stretch_type=StretchType.STATIC_ACTIVE,
            hold_seconds=20,
            repetitions=2,
            description="站立，屈膝向后抓住脚踝，感受大腿前侧拉伸",
            precautions=["扶墙保持平衡", "膝盖并拢"],
        ),
        "hamstring_stretch": StretchExercise(
            name="腘绳肌拉伸",
            body_region=BodyRegion.HAMSTRINGS,
            stretch_type=StretchType.STATIC_ACTIVE,
            hold_seconds=20,
            repetitions=2,
            description="坐姿，一腿伸直，身体前倾，感受大腿后侧拉伸",
            precautions=["不要弹震", "保持背部平直"],
        ),
        "calf_stretch": StretchExercise(
            name="小腿拉伸",
            body_region=BodyRegion.CALVES,
            stretch_type=StretchType.STATIC_ACTIVE,
            hold_seconds=20,
            repetitions=2,
            description="面墙站立，一腿后撤，脚跟着地，感受小腿拉伸",
            precautions=["保持后脚跟着地"],
        ),
    }
    
    def generate(
        self,
        risk_level: RiskLevel,
        patient_age: int,
        has_cardiac_surgery: bool = False,
        surgery_weeks_ago: Optional[int] = None,
    ) -> FlexibilityPrescription:
        """生成柔韧性训练处方"""
        
        # 确定频率
        frequency = {
            "per_week": 3,
            "description": "每周至少 2-3 次，可在有氧运动后进行",
        }
        
        # 确定拉伸时长
        if patient_age >= 60:
            duration = (30, 60)
            duration_desc = "老年人每次拉伸保持 30-60 秒"
        else:
            duration = (10, 30)
            duration_desc = "每次拉伸保持 10-30 秒"
        
        # 选择拉伸类型
        stretch_types = [StretchType.DYNAMIC, StretchType.STATIC_ACTIVE]
        
        # 选择动作
        exercises = self._select_exercises(has_cardiac_surgery, surgery_weeks_ago)
        
        # 生成注意事项
        precautions = [
            "拉伸至感到紧绷或轻微不适即可，不要过度拉伸",
            "保持正常呼吸，不要憋气",
            "动态拉伸适合热身阶段，静态拉伸适合放松阶段",
            "不要在抗阻训练前直接进行静态拉伸",
        ]
        
        contraindications = []
        if has_cardiac_surgery and surgery_weeks_ago and surgery_weeks_ago < 12:
            contraindications.append("心脏手术后 3 个月内禁止胸部拉伸")
            precautions.append("避免胸部拉伸动作")
        
        return FlexibilityPrescription(
            frequency_per_week=frequency["per_week"],
            frequency_description=frequency["description"],
            duration_per_stretch_seconds=duration,
            total_duration_minutes=10,
            stretch_types=stretch_types,
            exercises=exercises,
            timing_description="建议在有氧运动后的放松阶段进行静态拉伸，热身阶段进行动态拉伸",
            progression_description="逐渐增加拉伸保持时间和动作幅度，但不要过度拉伸",
            precautions=precautions,
            contraindications=contraindications,
        )
    
    def _select_exercises(
        self,
        has_cardiac_surgery: bool,
        surgery_weeks_ago: Optional[int],
    ) -> List[StretchExercise]:
        """选择拉伸动作"""
        exercises = list(self.STRETCH_LIBRARY.values())
        
        # 心脏手术后3个月内排除胸部拉伸
        if has_cardiac_surgery and surgery_weeks_ago and surgery_weeks_ago < 12:
            exercises = [e for e in exercises if e.body_region != BodyRegion.CHEST]
        
        return exercises


class NeuromuscularPrescriptionGenerator:
    """神经肌肉训练处方生成器"""
    
    EXERCISE_LIBRARY = {
        "single_leg_stand": NeuromuscularExercise(
            name="单腿站立",
            category="balance",
            duration_seconds=30,
            repetitions=3,
            description="单腿站立，保持平衡，可扶墙进行",
            difficulty_level=2,
            precautions=["确保周围有支撑物", "循序渐进"],
        ),
        "tandem_stand": NeuromuscularExercise(
            name="前后脚站立",
            category="balance",
            duration_seconds=30,
            repetitions=3,
            description="一脚在前一脚在后，脚跟对脚尖站立",
            difficulty_level=2,
            precautions=["可扶墙保持平衡"],
        ),
        "heel_to_toe_walk": NeuromuscularExercise(
            name="脚跟对脚尖行走",
            category="coordination",
            duration_seconds=0,
            repetitions=10,
            description="沿直线行走，每步脚跟对脚尖",
            difficulty_level=3,
            precautions=["确保行走路线安全"],
        ),
        "weight_shift": NeuromuscularExercise(
            name="重心转移",
            category="balance",
            duration_seconds=0,
            repetitions=10,
            description="站立，缓慢将重心从一侧转移到另一侧",
            difficulty_level=1,
            precautions=["动作缓慢"],
        ),
        "step_over_obstacle": NeuromuscularExercise(
            name="跨越障碍物",
            category="coordination",
            duration_seconds=0,
            repetitions=10,
            description="跨越低矮障碍物（如书本），锻炼协调性",
            difficulty_level=3,
            precautions=["障碍物高度适中", "确保安全"],
        ),
        "eyes_closed_stand": NeuromuscularExercise(
            name="闭眼站立",
            category="proprioception",
            duration_seconds=20,
            repetitions=3,
            description="双脚并拢站立，闭眼保持平衡",
            difficulty_level=3,
            precautions=["确保周围安全", "可扶墙"],
        ),
    }
    
    def generate(
        self,
        risk_level: RiskLevel,
        patient_age: int,
        has_balance_issues: bool = False,
        has_fall_history: bool = False,
    ) -> NeuromuscularPrescription:
        """生成神经肌肉训练处方"""
        
        # 确定频率和时长
        frequency = {
            "per_week": 3,
            "description": "每周 2-3 次",
        }
        
        total_minutes_per_week = 60
        session_minutes = 20
        
        # 选择动作
        exercises = self._select_exercises(
            patient_age, has_balance_issues, has_fall_history
        )
        
        # 推荐活动
        recommended = ["太极拳", "瑜伽（适度）", "平衡板训练"]
        if patient_age >= 60:
            recommended.insert(0, "太极拳（特别推荐）")
        
        precautions = [
            "确保训练环境安全，周围有支撑物",
            "循序渐进，从简单动作开始",
            "如感到头晕或不稳，立即停止并扶稳",
            "建议有人陪同进行训练",
        ]
        
        if has_fall_history:
            precautions.append("有跌倒史者必须在有人陪同下进行")
        
        return NeuromuscularPrescription(
            frequency_per_week=frequency["per_week"],
            frequency_description=frequency["description"],
            total_duration_minutes_per_week=total_minutes_per_week,
            session_duration_minutes=session_minutes,
            exercises=exercises,
            progression_description=(
                "进阶原则：\n"
                "1. 从有支撑到无支撑\n"
                "2. 从睁眼到闭眼\n"
                "3. 从稳定平面到不稳定平面\n"
                "4. 逐渐增加动作难度和持续时间"
            ),
            precautions=precautions,
            recommended_activities=recommended,
        )
    
    def _select_exercises(
        self,
        age: int,
        has_balance_issues: bool,
        has_fall_history: bool,
    ) -> List[NeuromuscularExercise]:
        """选择训练动作"""
        exercises = list(self.EXERCISE_LIBRARY.values())
        
        # 根据风险调整难度
        if has_balance_issues or has_fall_history or age >= 70:
            # 只选择低难度动作
            exercises = [e for e in exercises if e.difficulty_level <= 2]
        
        return sorted(exercises, key=lambda x: x.difficulty_level)
