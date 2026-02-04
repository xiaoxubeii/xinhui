# -*- coding: utf-8 -*-
"""
PDF 报告生成器

生成 CPET 分析报告和运动处方 PDF。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, Image, HRFlowable
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from ..prescription.generator import ExercisePrescription
from ..prescription.risk_stratification import RiskLevel
from ..inference.vo2_predictor import VO2PeakPrediction, WeberClass


@dataclass
class PatientInfo:
    """患者信息"""
    name: str
    patient_id: str
    age: int
    sex: str
    height_cm: float
    weight_kg: float
    diagnosis: List[str] = field(default_factory=list)
    medical_history: List[str] = field(default_factory=list)


@dataclass
class CPETTestResults:
    """CPET 测试结果"""
    test_date: datetime
    test_duration_seconds: float
    protocol: str  # 测试方案
    termination_reason: str  # 终止原因
    
    # 峰值指标
    vo2_peak: float
    vo2_peak_predicted_percent: float
    hr_max: float
    hr_max_predicted_percent: float
    max_workload: float
    max_mets: float
    max_rer: float
    
    # AT 相关
    at_time_seconds: float
    at_vo2: float
    at_hr: float
    at_workload: float
    
    # 通气效率
    ve_vco2_slope: Optional[float] = None
    oues: Optional[float] = None
    
    # 血压
    sbp_rest: Optional[float] = None
    sbp_peak: Optional[float] = None
    dbp_rest: Optional[float] = None
    dbp_peak: Optional[float] = None


@dataclass
class CPETReport:
    """CPET 报告"""
    patient: PatientInfo
    test_results: CPETTestResults
    vo2_prediction: Optional[VO2PeakPrediction] = None
    prescription: Optional[ExercisePrescription] = None
    
    # 图表路径
    vo2_curve_path: Optional[str] = None
    vslope_path: Optional[str] = None
    hr_curve_path: Optional[str] = None
    
    # 医生信息
    physician_name: Optional[str] = None
    physician_signature: Optional[str] = None
    report_date: datetime = field(default_factory=datetime.now)


class PDFReportGenerator:
    """PDF 报告生成器"""
    
    def __init__(self, font_path: Optional[str] = None):
        """
        初始化生成器
        
        Args:
            font_path: 中文字体路径
        """
        if not HAS_REPORTLAB:
            raise RuntimeError("reportlab not installed. Run: pip install reportlab")
        
        self.font_path = font_path
        self._register_fonts()
        self._setup_styles()
    
    def _register_fonts(self) -> None:
        """注册中文字体"""
        # 尝试注册中文字体
        font_paths = [
            self.font_path,
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/msyh.ttc",
        ]
        
        for path in font_paths:
            if path and Path(path).exists():
                try:
                    pdfmetrics.registerFont(TTFont('Chinese', path))
                    self.chinese_font = 'Chinese'
                    return
                except Exception:
                    continue
        
        # 如果没有中文字体，使用默认字体
        self.chinese_font = 'Helvetica'
    
    def _setup_styles(self) -> None:
        """设置样式"""
        self.styles = getSampleStyleSheet()
        
        # 标题样式
        self.styles.add(ParagraphStyle(
            name='ChineseTitle',
            fontName=self.chinese_font,
            fontSize=18,
            leading=24,
            alignment=1,  # 居中
            spaceAfter=12,
        ))
        
        # 副标题样式
        self.styles.add(ParagraphStyle(
            name='ChineseHeading',
            fontName=self.chinese_font,
            fontSize=14,
            leading=18,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor('#2c3e50'),
        ))
        
        # 正文样式
        self.styles.add(ParagraphStyle(
            name='ChineseBody',
            fontName=self.chinese_font,
            fontSize=10,
            leading=14,
            spaceBefore=3,
            spaceAfter=3,
        ))
        
        # 小字样式
        self.styles.add(ParagraphStyle(
            name='ChineseSmall',
            fontName=self.chinese_font,
            fontSize=8,
            leading=10,
            textColor=colors.grey,
        ))
    
    def generate_report(
        self,
        report: CPETReport,
        output_path: Optional[str] = None,
    ) -> bytes:
        """
        生成 PDF 报告
        
        Args:
            report: 报告数据
            output_path: 输出路径（可选）
            
        Returns:
            bytes: PDF 内容
        """
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )
        
        # 构建内容
        story = []
        
        # 标题
        story.append(Paragraph("心肺运动试验报告", self.styles['ChineseTitle']))
        story.append(Spacer(1, 12))
        
        # 患者信息
        story.extend(self._build_patient_section(report.patient))
        
        # 测试结果
        story.extend(self._build_results_section(report.test_results))
        
        # VO2 Peak 预测
        if report.vo2_prediction:
            story.extend(self._build_prediction_section(report.vo2_prediction))
        
        # 运动处方
        if report.prescription:
            story.append(PageBreak())
            story.extend(self._build_prescription_section(report.prescription))
        
        # 签名
        story.extend(self._build_signature_section(report))
        
        # 生成 PDF
        doc.build(story)
        
        pdf_content = buffer.getvalue()
        buffer.close()
        
        # 保存到文件
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_content)
        
        return pdf_content

    def generate_prescription_pdf(
        self,
        patient: PatientInfo,
        prescription: ExercisePrescription,
        physician_name: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> bytes:
        """
        生成仅包含运动处方的 PDF

        Args:
            patient: 患者信息
            prescription: 运动处方
            physician_name: 医生姓名
            output_path: 输出路径（可选）

        Returns:
            bytes: PDF 内容
        """
        report = CPETReport(
            patient=patient,
            test_results=CPETTestResults(
                test_date=datetime.now(),
                test_duration_seconds=0,
                protocol="",
                termination_reason="",
                vo2_peak=0,
                vo2_peak_predicted_percent=0,
                hr_max=0,
                hr_max_predicted_percent=0,
                max_workload=0,
                max_mets=0,
                max_rer=0,
                at_time_seconds=0,
                at_vo2=0,
                at_hr=0,
                at_workload=0,
            ),
            prescription=prescription,
            physician_name=physician_name,
        )

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )

        story = []
        story.extend(self._build_patient_section(patient))
        story.extend(self._build_prescription_section(prescription))
        story.extend(self._build_signature_section(report))

        doc.build(story)
        pdf_content = buffer.getvalue()

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_content)

        return pdf_content
    
    def _build_patient_section(self, patient: PatientInfo) -> List:
        """构建患者信息部分"""
        elements = []
        
        elements.append(Paragraph("患者信息", self.styles['ChineseHeading']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        
        # 患者信息表格
        data = [
            ["姓名", patient.name, "性别", patient.sex],
            ["年龄", f"{patient.age} 岁", "病历号", patient.patient_id],
            ["身高", f"{patient.height_cm} cm", "体重", f"{patient.weight_kg} kg"],
            ["BMI", f"{patient.weight_kg / (patient.height_cm/100)**2:.1f} kg/m²", "", ""],
        ]
        
        if patient.diagnosis:
            data.append(["诊断", ", ".join(patient.diagnosis), "", ""])
        
        table = Table(data, colWidths=[3*cm, 5*cm, 3*cm, 5*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
        
        return elements
    
    def _build_results_section(self, results: CPETTestResults) -> List:
        """构建测试结果部分"""
        elements = []
        
        elements.append(Paragraph("测试结果", self.styles['ChineseHeading']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        
        # 测试信息
        test_info = [
            ["测试日期", results.test_date.strftime("%Y-%m-%d %H:%M")],
            ["测试方案", results.protocol],
            ["测试时长", f"{results.test_duration_seconds/60:.1f} 分钟"],
            ["终止原因", results.termination_reason],
        ]
        
        table = Table(test_info, colWidths=[4*cm, 12*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 8))
        
        # 峰值指标
        elements.append(Paragraph("峰值指标", self.styles['ChineseBody']))
        
        peak_data = [
            ["指标", "测量值", "预计值%", "参考范围"],
            ["VO2 peak (ml/kg/min)", f"{results.vo2_peak:.1f}", 
             f"{results.vo2_peak_predicted_percent:.0f}%", ">84%"],
            ["最大心率 (bpm)", f"{results.hr_max:.0f}", 
             f"{results.hr_max_predicted_percent:.0f}%", ">85%"],
            ["最大功率 (W)", f"{results.max_workload:.0f}", "-", "-"],
            ["最大 MET", f"{results.max_mets:.1f}", "-", "-"],
            ["最大 RER", f"{results.max_rer:.2f}", "-", ">1.10"],
        ]
        
        table = Table(peak_data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 8))
        
        # AT 指标
        elements.append(Paragraph("无氧阈 (AT) 指标", self.styles['ChineseBody']))
        
        at_data = [
            ["AT 时间", f"{results.at_time_seconds/60:.1f} 分钟"],
            ["AT VO2", f"{results.at_vo2:.1f} ml/kg/min"],
            ["AT 心率", f"{results.at_hr:.0f} bpm"],
            ["AT 功率", f"{results.at_workload:.0f} W"],
        ]
        
        table = Table(at_data, colWidths=[5*cm, 5*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))
        
        return elements
    
    def _build_prediction_section(self, prediction: VO2PeakPrediction) -> List:
        """构建预测结果部分"""
        elements = []
        
        elements.append(Paragraph("AI 辅助分析", self.styles['ChineseHeading']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        
        # Weber 分级颜色
        weber_colors = {
            WeberClass.A: colors.HexColor('#27ae60'),
            WeberClass.B: colors.HexColor('#f39c12'),
            WeberClass.C: colors.HexColor('#e67e22'),
            WeberClass.D: colors.HexColor('#e74c3c'),
        }
        
        pred_data = [
            ["预测 VO2 Peak", f"{prediction.predicted_vo2_peak} ml/kg/min"],
            ["95% 置信区间", f"{prediction.confidence_interval[0]}-{prediction.confidence_interval[1]} ml/kg/min"],
            ["Weber 分级", f"{prediction.weber_class.value} 级"],
            ["分级说明", prediction.weber_description],
        ]
        
        if prediction.percentile:
            pred_data.append(["同龄百分位", f"第 {prediction.percentile:.0f} 百分位"])
        
        table = Table(pred_data, colWidths=[4*cm, 12*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))
        
        return elements
    
    def _build_prescription_section(self, prescription: ExercisePrescription) -> List:
        """构建运动处方部分"""
        elements = []
        
        elements.append(Paragraph("个性化运动处方", self.styles['ChineseTitle']))
        elements.append(Spacer(1, 12))
        
        # 风险分层
        risk_colors = {
            RiskLevel.LOW: colors.HexColor('#27ae60'),
            RiskLevel.MODERATE: colors.HexColor('#f39c12'),
            RiskLevel.HIGH: colors.HexColor('#e74c3c'),
        }
        
        elements.append(Paragraph(
            f"风险分层: {prescription.risk_level.value.upper()}",
            self.styles['ChineseHeading']
        ))
        elements.append(Paragraph(
            prescription.risk_description,
            self.styles['ChineseBody']
        ))
        elements.append(Spacer(1, 8))
        
        # 有氧运动
        elements.append(Paragraph("一、有氧运动处方", self.styles['ChineseHeading']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        
        aerobic = prescription.aerobic
        aerobic_data = [
            ["频率", aerobic.frequency_description],
            ["强度", aerobic.intensity_description],
            ["时间", aerobic.time_description],
            ["类型", aerobic.type_description],
            ["进阶", aerobic.progression_description[:100] + "..."],
        ]
        
        table = Table(aerobic_data, colWidths=[2*cm, 14*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#3498db')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 8))
        
        # 抗阻训练
        elements.append(Paragraph("二、抗阻训练处方", self.styles['ChineseHeading']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        
        resistance = prescription.resistance
        resistance_data = [
            ["频率", resistance.frequency_description],
            ["强度", resistance.intensity_description],
        ]
        
        table = Table(resistance_data, colWidths=[2*cm, 14*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#9b59b6')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 8))
        
        # 周计划
        elements.append(Paragraph("三、周训练计划", self.styles['ChineseHeading']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        
        schedule_data = [["日期", "训练内容"]]
        for day in prescription.weekly_schedule:
            schedule_data.append([day["day"], ", ".join(day["activities"])])
        
        table = Table(schedule_data, colWidths=[2*cm, 14*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 8))
        
        # 注意事项
        elements.append(Paragraph("四、注意事项", self.styles['ChineseHeading']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        
        for precaution in prescription.general_precautions[:8]:
            elements.append(Paragraph(f"• {precaution}", self.styles['ChineseBody']))
        
        elements.append(Spacer(1, 8))
        
        # 随访建议
        elements.append(Paragraph("五、随访建议", self.styles['ChineseHeading']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Paragraph(
            prescription.follow_up_recommendation,
            self.styles['ChineseBody']
        ))
        
        return elements
    
    def _build_signature_section(self, report: CPETReport) -> List:
        """构建签名部分"""
        elements = []
        
        elements.append(Spacer(1, 24))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        elements.append(Spacer(1, 12))
        
        sig_data = [
            [f"报告日期: {report.report_date.strftime('%Y-%m-%d')}", 
             f"报告医生: {report.physician_name or '_______________'}"],
        ]
        
        table = Table(sig_data, colWidths=[8*cm, 8*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        elements.append(table)
        
        # 免责声明
        elements.append(Spacer(1, 24))
        elements.append(Paragraph(
            "声明: 本报告中的 AI 辅助分析结果仅供参考，最终诊断和治疗方案请以临床医生判断为准。",
            self.styles['ChineseSmall']
        ))
        
        return elements
