# -*- coding: utf-8 -*-
"""
有氧运动处方模块

基于《心血管疾病患者门诊运动康复专家共识》实现的有氧运动处方生成。
遵循 FITT-VP 原则：频率(Frequency)、强度(Intensity)、时间(Time)、
类型(Type)、运动量(Volume)、进阶(Progression)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from .risk_stratification import RiskLevel


class IntensityZone(Enum):
    """运动强度区间"""
    LOW = "low"           # < VT1, < 40% VO2peak
    MODERATE = "moderate" # VT1 ~ VT2前半段, 40-69% VO2peak
    HIGH = "high"         # VT2后半段, 70-85% VO2peak
    VERY_HIGH = "very_high"  # > 85% VO2peak


class ExerciseType(Enum):
    """有氧运动类型"""
    WALKING = "walking"
    CYCLING = "cycling"
    TREADMILL = "treadmill"
    ELLIPTICAL = "elliptical"
    ROWING = "rowing"
    SWIMMING = "swimming"
    TAI_CHI = "tai_chi"


@dataclass
class CPETResults:
    """心肺运动试验结果"""
    # 峰值指标
    vo2_peak: float  # ml/kg/min
    hr_max: float    # bpm
    hr_rest: float   # bpm
    max_workload: float  # W
    max_mets: float
    
    # 通气阈值
    vt1_vo2: Optional[float] = None  # VT1对应的VO2 (ml/kg/min)
    vt1_hr: Optional[float] = None   # VT1对应的心率
    vt1_workload: Optional[float] = None  # VT1对应的功率
    
    vt2_vo2: Optional[float] = None  # VT2对应的VO2
    vt2_hr: Optional[float] = None   # VT2对应的心率
    vt2_workload: Optional[float] = None  # VT2对应的功率
    
    # 风险阈值（如有）
    ischemia_hr: Optional[float] = None  # 缺血发生时的心率
    arrhythmia_hr: Optional[float] = None  # 心律失常发生时的心率
    symptom_hr: Optional[float] = None  # 症状出现时的心率
    
    @property
    def hr_reserve(self) -> float:
        """储备心率 = 最大心率 - 静息心率"""
        return self.hr_max - self.hr_rest


@dataclass
class AerobicPrescription:
    """有氧运动处方"""
    # 频率
    frequency_per_week: int  # 每周次数
    frequency_description: str
    
    # 强度
    intensity_zone: IntensityZone
    target_hr_range: Tuple[float, float]  # 目标心率范围
    target_vo2_percent: Tuple[float, float]  # 目标VO2百分比范围
    target_workload_range: Optional[Tuple[float, float]] = None  # 目标功率范围
    rpe_range: Tuple[int, int] = (12, 14)  # RPE范围
    intensity_description: str = ""
    
    # 时间
    warmup_minutes: int = 10
    exercise_minutes: int = 30
    cooldown_minutes: int = 10
    time_description: str = ""
    
    # 类型
    exercise_types: List[ExerciseType] = field(default_factory=list)
    type_description: str = ""
    
    # 运动量
    target_kcal_per_session: Optional[float] = None
    target_kcal_per_week: Optional[float] = None
    volume_description: str = ""
    
    # 进阶
    progression_description: str = ""
    
    # 注意事项
    precautions: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)


class AerobicPrescriptionGenerator:
    """有氧运动处方生成器"""
    
    # RPE量表对照
    RPE_SCALE = {
        6: "完全不费力",
        7: "极其轻松",
        8: "极其轻松",
        9: "非常轻松",
        10: "非常轻松",
        11: "轻松",
        12: "轻松",
        13: "有些费力",
        14: "有些费力",
        15: "费力",
        16: "费力",
        17: "非常费力",
        18: "非常费力",
        19: "极其费力",
        20: "筋疲力尽",
    }
    
    def __init__(self):
        pass
    
    def generate(
        self,
        cpet_results: CPETResults,
        risk_level: RiskLevel,
        patient_weight_kg: float,
        is_initial: bool = True,
    ) -> AerobicPrescription:
        """
        生成有氧运动处方
        
        Args:
            cpet_results: 心肺运动试验结果
            risk_level: 风险分层等级
            patient_weight_kg: 患者体重(kg)
            is_initial: 是否为初始处方
        """
        # 确定频率
        frequency = self._determine_frequency(risk_level, is_initial)
        
        # 确定强度
        intensity = self._determine_intensity(cpet_results, risk_level, is_initial)
        
        # 确定时间
        time_params = self._determine_time(risk_level, is_initial)
        
        # 确定类型
        exercise_types = self._determine_types(risk_level)
        
        # 计算运动量
        volume = self._calculate_volume(
            intensity, time_params, frequency, patient_weight_kg
        )
        
        # 生成进阶建议
        progression = self._generate_progression(risk_level, is_initial)
        
        # 生成注意事项
        precautions = self._generate_precautions(cpet_results, risk_level)
        
        return AerobicPrescription(
            frequency_per_week=frequency["per_week"],
            frequency_description=frequency["description"],
            intensity_zone=intensity["zone"],
            target_hr_range=intensity["hr_range"],
            target_vo2_percent=intensity["vo2_percent"],
            target_workload_range=intensity.get("workload_range"),
            rpe_range=intensity["rpe_range"],
            intensity_description=intensity["description"],
            warmup_minutes=time_params["warmup"],
            exercise_minutes=time_params["exercise"],
            cooldown_minutes=time_params["cooldown"],
            time_description=time_params["description"],
            exercise_types=exercise_types["types"],
            type_description=exercise_types["description"],
            target_kcal_per_session=volume.get("kcal_per_session"),
            target_kcal_per_week=volume.get("kcal_per_week"),
            volume_description=volume["description"],
            progression_description=progression,
            precautions=precautions["precautions"],
            contraindications=precautions["contraindications"],
        )
    
    def _determine_frequency(
        self, risk_level: RiskLevel, is_initial: bool
    ) -> dict:
        """确定运动频率"""
        if is_initial:
            if risk_level == RiskLevel.HIGH:
                return {
                    "per_week": 3,
                    "description": "每周 3 次，非连续日进行，确保充分恢复",
                }
            elif risk_level == RiskLevel.MODERATE:
                return {
                    "per_week": 3,
                    "description": "每周 3-4 次，可根据耐受情况逐渐增加",
                }
            else:
                return {
                    "per_week": 4,
                    "description": "每周 4-5 次，建议隔日进行",
                }
        else:
            # 非初始阶段可增加频率
            return {
                "per_week": 5,
                "description": "每周 5 次，可根据个人情况调整",
            }
    
    def _determine_intensity(
        self,
        cpet: CPETResults,
        risk_level: RiskLevel,
        is_initial: bool,
    ) -> dict:
        """
        确定运动强度
        
        基于VT1/VT2的精准运动强度制定方法
        """
        # 确定安全上限心率
        safety_hr_limit = self._get_safety_hr_limit(cpet)
        
        if is_initial or risk_level == RiskLevel.HIGH:
            # 初始阶段或高危：低强度，< VT1
            zone = IntensityZone.LOW
            vo2_percent = (30, 40)
            rpe_range = (10, 12)
            
            if cpet.vt1_hr:
                # 基于VT1的精准处方
                target_hr = (cpet.hr_rest + 20, min(cpet.vt1_hr - 5, safety_hr_limit))
            else:
                # 基于储备心率的估算
                target_hr = (
                    cpet.hr_rest + 0.3 * cpet.hr_reserve,
                    min(cpet.hr_rest + 0.4 * cpet.hr_reserve, safety_hr_limit),
                )
            
            description = (
                f"低强度有氧运动，心率控制在 {int(target_hr[0])}-{int(target_hr[1])} bpm，"
                f"RPE {rpe_range[0]}-{rpe_range[1]} 分（{self.RPE_SCALE[rpe_range[0]]}至{self.RPE_SCALE[rpe_range[1]]}），"
                "运动时应能正常对话"
            )
            
        elif risk_level == RiskLevel.MODERATE:
            # 中危：中等强度，VT1 ~ VT2前半段
            zone = IntensityZone.MODERATE
            vo2_percent = (40, 60)
            rpe_range = (12, 14)
            
            if cpet.vt1_hr and cpet.vt2_hr:
                mid_hr = (cpet.vt1_hr + cpet.vt2_hr) / 2
                target_hr = (cpet.vt1_hr, min(mid_hr, safety_hr_limit))
            elif cpet.vt1_hr:
                target_hr = (cpet.vt1_hr, min(cpet.vt1_hr + 15, safety_hr_limit))
            else:
                target_hr = (
                    cpet.hr_rest + 0.4 * cpet.hr_reserve,
                    min(cpet.hr_rest + 0.6 * cpet.hr_reserve, safety_hr_limit),
                )
            
            description = (
                f"中等强度有氧运动，心率控制在 {int(target_hr[0])}-{int(target_hr[1])} bpm，"
                f"RPE {rpe_range[0]}-{rpe_range[1]} 分（{self.RPE_SCALE[rpe_range[0]]}至{self.RPE_SCALE[rpe_range[1]]}），"
                "运动时说话略感费力但仍可交流"
            )
            
        else:
            # 低危：可进行中高强度
            zone = IntensityZone.MODERATE
            vo2_percent = (50, 70)
            rpe_range = (12, 15)
            
            if cpet.vt1_hr and cpet.vt2_hr:
                target_hr = (cpet.vt1_hr, min(cpet.vt2_hr - 5, safety_hr_limit))
            elif cpet.vt1_hr:
                target_hr = (cpet.vt1_hr, min(cpet.vt1_hr + 25, safety_hr_limit))
            else:
                target_hr = (
                    cpet.hr_rest + 0.5 * cpet.hr_reserve,
                    min(cpet.hr_rest + 0.7 * cpet.hr_reserve, safety_hr_limit),
                )
            
            description = (
                f"中等至较高强度有氧运动，心率控制在 {int(target_hr[0])}-{int(target_hr[1])} bpm，"
                f"RPE {rpe_range[0]}-{rpe_range[1]} 分，"
                "可根据耐受情况在此范围内调整"
            )
        
        # 计算功率范围（如有VT数据）
        workload_range = None
        if cpet.vt1_workload:
            if zone == IntensityZone.LOW:
                workload_range = (cpet.vt1_workload * 0.6, cpet.vt1_workload * 0.9)
            elif cpet.vt2_workload:
                workload_range = (cpet.vt1_workload, cpet.vt2_workload * 0.8)
        
        return {
            "zone": zone,
            "hr_range": target_hr,
            "vo2_percent": vo2_percent,
            "workload_range": workload_range,
            "rpe_range": rpe_range,
            "description": description,
        }
    
    def _get_safety_hr_limit(self, cpet: CPETResults) -> float:
        """获取安全心率上限"""
        limits = [cpet.hr_max * 0.9]  # 默认不超过90%最大心率
        
        # 如有风险事件阈值，取更低值
        if cpet.ischemia_hr:
            limits.append(cpet.ischemia_hr - 10)
        if cpet.arrhythmia_hr:
            limits.append(cpet.arrhythmia_hr - 10)
        if cpet.symptom_hr:
            limits.append(cpet.symptom_hr - 10)
        
        return min(limits)
    
    def _determine_time(self, risk_level: RiskLevel, is_initial: bool) -> dict:
        """确定运动时间"""
        if is_initial:
            if risk_level == RiskLevel.HIGH:
                return {
                    "warmup": 10,
                    "exercise": 15,
                    "cooldown": 10,
                    "description": "热身 10 分钟 + 运动 15-20 分钟 + 放松 10 分钟，"
                                   "可采用间歇训练模式（运动5分钟，休息2分钟）",
                }
            elif risk_level == RiskLevel.MODERATE:
                return {
                    "warmup": 10,
                    "exercise": 20,
                    "cooldown": 10,
                    "description": "热身 10 分钟 + 运动 20-30 分钟 + 放松 10 分钟",
                }
            else:
                return {
                    "warmup": 10,
                    "exercise": 30,
                    "cooldown": 10,
                    "description": "热身 10 分钟 + 运动 30-40 分钟 + 放松 10 分钟",
                }
        else:
            return {
                "warmup": 10,
                "exercise": 45,
                "cooldown": 10,
                "description": "热身 10 分钟 + 运动 45-60 分钟 + 放松 10 分钟",
            }
    
    def _determine_types(self, risk_level: RiskLevel) -> dict:
        """确定运动类型"""
        if risk_level == RiskLevel.HIGH:
            types = [ExerciseType.CYCLING, ExerciseType.WALKING]
            description = (
                "推荐功率车训练（便于监测和控制强度）或平地步行，"
                "避免跑步机等高冲击运动"
            )
        elif risk_level == RiskLevel.MODERATE:
            types = [
                ExerciseType.CYCLING,
                ExerciseType.TREADMILL,
                ExerciseType.WALKING,
                ExerciseType.ELLIPTICAL,
            ]
            description = (
                "可选择功率车、跑步机、椭圆机或户外步行，"
                "建议在有监护条件下进行"
            )
        else:
            types = [
                ExerciseType.CYCLING,
                ExerciseType.TREADMILL,
                ExerciseType.WALKING,
                ExerciseType.ELLIPTICAL,
                ExerciseType.ROWING,
                ExerciseType.SWIMMING,
            ]
            description = (
                "可选择多种有氧运动形式，包括功率车、跑步机、"
                "椭圆机、划船机、游泳等，建议交替进行"
            )
        
        return {"types": types, "description": description}
    
    def _calculate_volume(
        self,
        intensity: dict,
        time_params: dict,
        frequency: dict,
        weight_kg: float,
    ) -> dict:
        """计算运动量"""
        # 估算MET值
        zone = intensity["zone"]
        if zone == IntensityZone.LOW:
            avg_mets = 3.5
        elif zone == IntensityZone.MODERATE:
            avg_mets = 5.0
        else:
            avg_mets = 7.0
        
        # 计算每次能量消耗 (kcal)
        exercise_hours = time_params["exercise"] / 60
        kcal_per_session = avg_mets * weight_kg * exercise_hours
        
        # 计算每周能量消耗
        kcal_per_week = kcal_per_session * frequency["per_week"]
        
        description = (
            f"每次运动约消耗 {int(kcal_per_session)} kcal，"
            f"每周总消耗约 {int(kcal_per_week)} kcal"
        )
        
        return {
            "kcal_per_session": kcal_per_session,
            "kcal_per_week": kcal_per_week,
            "description": description,
        }
    
    def _generate_progression(self, risk_level: RiskLevel, is_initial: bool) -> str:
        """生成进阶建议"""
        if is_initial:
            if risk_level == RiskLevel.HIGH:
                return (
                    "进阶原则：循序渐进，每次只调整一个参数。\n"
                    "1. 首先增加运动时间：每周增加 2-3 分钟，直至达到 30 分钟\n"
                    "2. 然后增加运动强度：每周增加 5% 的目标心率\n"
                    "3. 最后增加运动频率：从每周 3 次增加到 4-5 次\n"
                    "4. 建议 2-4 周后复查心肺运动试验，根据新结果调整处方"
                )
            elif risk_level == RiskLevel.MODERATE:
                return (
                    "进阶原则：\n"
                    "1. 每周增加 5-10% 的运动时间或强度\n"
                    "2. 先增加时间，再增加强度\n"
                    "3. 运动耐受良好时可逐渐过渡到中高强度间歇训练(HIIT)\n"
                    "4. 建议 2-4 周后复查心肺运动试验"
                )
            else:
                return (
                    "进阶原则：\n"
                    "1. 每周增加 5-10% 的运动时间或强度\n"
                    "2. 可尝试高强度间歇训练(HIIT)：高强度30秒 + 恢复60秒\n"
                    "3. 逐渐增加HIIT的高强度累积时间至 15-20 分钟\n"
                    "4. 建议 4 周后复查心肺运动试验评估进展"
                )
        else:
            return (
                "维持阶段：\n"
                "1. 保持当前运动量，注重运动质量\n"
                "2. 可适当变换运动类型，保持运动兴趣\n"
                "3. 定期（每3-6个月）复查心肺运动试验"
            )
    
    def _generate_precautions(
        self, cpet: CPETResults, risk_level: RiskLevel
    ) -> dict:
        """生成注意事项"""
        precautions = [
            "运动前后测量血压和心率",
            "运动前进行 5-10 分钟热身，运动后进行 5-10 分钟放松",
            "运动过程中如出现胸闷、胸痛、头晕、呼吸困难等症状，立即停止运动",
            "避免空腹或饱餐后立即运动",
            "保持适当水分摄入",
            "穿着舒适的运动服装和鞋子",
        ]
        
        if risk_level == RiskLevel.HIGH:
            precautions.extend([
                "必须在有医护人员和心电监护的环境下进行运动",
                "随身携带急救药物（如硝酸甘油）",
                "避免单独运动",
            ])
        elif risk_level == RiskLevel.MODERATE:
            precautions.extend([
                "建议在有监护条件下进行运动",
                "运动时佩戴心率监测设备",
            ])
        
        # 根据CPET结果添加特定注意事项
        if cpet.ischemia_hr:
            precautions.append(
                f"心率不得超过 {int(cpet.ischemia_hr - 10)} bpm（缺血阈值下10次）"
            )
        if cpet.arrhythmia_hr:
            precautions.append(
                f"心率不得超过 {int(cpet.arrhythmia_hr - 10)} bpm（心律失常阈值下10次）"
            )
        
        contraindications = [
            "急性心肌梗死 < 2周",
            "不稳定型心绞痛发作期",
            "严重且无法控制的心律失常",
            "急性心力衰竭发作期",
            "急性心肌炎、心包炎或心内膜炎",
            "急性主动脉夹层",
            "静息状态血压 > 200/100 mmHg",
        ]
        
        return {
            "precautions": precautions,
            "contraindications": contraindications,
        }
