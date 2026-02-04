from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, Iterator, Optional, Tuple

import numpy as np
import pandas as pd

from ..config import settings
from ..data_loader import CPETStudyData
from ..inference.at_predictor import CPETDataPoint


@dataclass
class SimulationConfig:
    speed: float = 1.0
    smooth: str = "none"
    start: Optional[float] = None
    end: Optional[float] = None


def _safe_float(value: object, default: Optional[float] = None) -> Optional[float]:
    try:
        val = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(val) or math.isinf(val):
        return default
    return val


class CPETSimulator:
    """Stream CPET samples from processed_institutes.h5 for realtime simulation."""

    def __init__(self, study_data: CPETStudyData) -> None:
        self.study_data = study_data
        self.rng = random.Random()

    def sample_exam_id(self) -> str:
        if not self.study_data.exam_to_institute:
            raise RuntimeError("No exams found in CPET dataset.")
        return self.rng.choice(list(self.study_data.exam_to_institute.keys()))

    def load_exam(
        self,
        exam_id: str,
        *,
        smooth: str = "none",
        start: Optional[float] = None,
        end: Optional[float] = None,
    ) -> pd.DataFrame:
        return self.study_data.load_exam_dataframe(
            exam_id,
            smooth=smooth,
            start=start,
            end=end,
        )

    def build_sample_payload(self, row: pd.Series, timestamp: float) -> Dict[str, Optional[float]]:
        payload = {
            "timestamp": timestamp,
            "vo2": _safe_float(row.get("VO2")),
            "vco2": _safe_float(row.get("VCO2")),
            "ve": _safe_float(row.get("VE")),
            "hr": _safe_float(row.get("HR")),
            "rr": _safe_float(row.get("Bf")),
            "rer": _safe_float(row.get("RER")),
            "work_rate": _safe_float(row.get("Power_Load")),
            "spo2": _safe_float(row.get("SpO2")),
            "sbp": _safe_float(row.get("BP_Syst")),
            "dbp": _safe_float(row.get("BP_Diast")),
            "vt": _safe_float(row.get("VT")),
            "peto2": _safe_float(row.get("PetO2")),
            "petco2": _safe_float(row.get("PetCO2")),
            "ve_vo2": _safe_float(row.get("VE_VO2")),
            "ve_vco2": _safe_float(row.get("VE_VCO2")),
            "vo2_hr": _safe_float(row.get("VO2_HR")),
            "bf": _safe_float(row.get("Bf")),
        }
        return payload

    def build_data_point(self, row: pd.Series, timestamp: float) -> CPETDataPoint:
        extras = {
            str(col).lower(): _safe_float(row.get(col))
            for col in row.index
            if col not in {"Examination_ID"}
        }
        return CPETDataPoint(
            timestamp=timestamp,
            vo2=_safe_float(row.get("VO2"), 0.0) or 0.0,
            vco2=_safe_float(row.get("VCO2"), 0.0) or 0.0,
            ve=_safe_float(row.get("VE"), 0.0) or 0.0,
            hr=_safe_float(row.get("HR"), 0.0) or 0.0,
            rr=_safe_float(row.get("Bf"), 0.0) or 0.0,
            rer=_safe_float(row.get("RER"), 0.0) or 0.0,
            work_rate=_safe_float(row.get("Power_Load"), 0.0) or 0.0,
            spo2=_safe_float(row.get("SpO2")),
            sbp=_safe_float(row.get("BP_Syst")),
            dbp=_safe_float(row.get("BP_Diast")),
            extras=extras,
        )

    def iter_samples(
        self,
        df: pd.DataFrame,
        *,
        speed: float = 1.0,
        default_step: Optional[float] = None,
    ) -> Iterator[Tuple[Dict[str, Optional[float]], CPETDataPoint, float]]:
        if df.empty:
            return iter(())

        default_step_sec = default_step if default_step is not None else settings.delta_sec
        times = df["Time"].tolist() if "Time" in df.columns else None

        prev_time = None
        for idx, row in df.iterrows():
            timestamp = _safe_float(times[idx], float(idx) * default_step_sec) if times else float(idx) * default_step_sec
            sample = self.build_sample_payload(row, timestamp)
            point = self.build_data_point(row, timestamp)

            sleep_sec = 0.0
            if prev_time is not None:
                delta = max(0.0, float(timestamp) - float(prev_time))
                speed_safe = max(speed, 1e-3)
                sleep_sec = delta / speed_safe
            prev_time = timestamp
            yield sample, point, sleep_sec
