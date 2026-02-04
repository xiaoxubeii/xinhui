from __future__ import annotations

import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import h5py
import numpy as np
import pandas as pd

from .smoothing import apply_smoothing


class CPETStudyData:
    """HDF5-backed CPET exam loader with lightweight caching."""

    def __init__(self, data_file: Path) -> None:
        self.data_file = Path(data_file).expanduser()
        if not self.data_file.exists():
            raise FileNotFoundError(f"CPET data file not found: {self.data_file}")
        self.exam_to_institute = self._build_exam_index()

    def _build_exam_index(self) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        with h5py.File(self.data_file, "r") as h5:
            institutes = h5.get("institutes")
            if institutes is None:
                return mapping
            for inst_name, inst_group in institutes.items():
                exam_ids_ds = inst_group.get("exam_ids")
                if exam_ids_ds is None:
                    continue
                raw = exam_ids_ds[()]
                if isinstance(raw, (bytes, str)):
                    ids = [raw.decode("utf-8")
                           if isinstance(raw, bytes) else str(raw)]
                else:
                    ids = []
                    for item in raw:
                        if isinstance(item, (bytes, np.bytes_)):
                            ids.append(item.decode("utf-8"))
                        else:
                            ids.append(str(item))
                for eid in ids:
                    if eid:
                        mapping[eid] = inst_name
        return mapping

    def list_exams(self, limit: int = 50, institute: Optional[str] = None) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []
        for idx, (exam_id, inst) in enumerate(self.exam_to_institute.items()):
            if institute and inst != institute:
                continue
            entries.append({"exam_id": exam_id, "institute": inst})
            if len(entries) >= limit:
                break
        return entries

    @lru_cache(maxsize=2)
    def _load_institute_features(self, institute: str) -> pd.DataFrame:
        with h5py.File(self.data_file, "r") as h5:
            inst_group = h5["institutes"].get(institute)
            if inst_group is None:
                raise KeyError(f"Institution not found: {institute}")
            features_ds = inst_group.get("features")
            if features_ds is None:
                raise KeyError(f"Features dataset missing for institute {institute}")
            raw = features_ds[()]
        buffer = memoryview(raw).tobytes()
        df = pickle.loads(buffer)
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"Decoded features are not a DataFrame for {institute}")
        return df

    @lru_cache(maxsize=2)
    def _load_institute_metadata(self, institute: str) -> pd.DataFrame:
        with h5py.File(self.data_file, "r") as h5:
            inst_group = h5["institutes"].get(institute)
            if inst_group is None:
                raise KeyError(f"Institution not found: {institute}")
            metadata_ds = inst_group.get("metadata")
            if metadata_ds is None:
                raise KeyError(f"Metadata dataset missing for institute {institute}")
            raw = metadata_ds[()]
        buffer = memoryview(raw).tobytes()
        df = pickle.loads(buffer)
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"Decoded metadata is not a DataFrame for {institute}")
        return df

    def load_exam_dataframe(
        self,
        exam_id: str,
        *,
        start: Optional[float] = None,
        end: Optional[float] = None,
        smooth: str = "none",
    ) -> pd.DataFrame:
        if exam_id not in self.exam_to_institute:
            raise KeyError(f"Exam {exam_id} not found in index.")
        institute = self.exam_to_institute[exam_id]
        features = self._load_institute_features(institute)
        exam_df = features[features["Examination_ID"] == exam_id].copy()
        if "Time" in exam_df.columns:
            exam_df = exam_df.sort_values("Time")
        if start is not None:
            exam_df = exam_df[exam_df["Time"] >= float(start)]
        if end is not None:
            exam_df = exam_df[exam_df["Time"] <= float(end)]
        smoothed = apply_smoothing(exam_df, smooth)
        return smoothed.reset_index(drop=True)

    def load_exam_metadata(self, exam_id: str) -> Dict[str, Any]:
        if exam_id not in self.exam_to_institute:
            raise KeyError(f"Exam {exam_id} not found in index.")
        institute = self.exam_to_institute[exam_id]
        metadata = self._load_institute_metadata(institute)
        row = metadata[metadata["Examination_ID"] == exam_id]
        if row.empty:
            return {"exam_id": exam_id, "institute": institute}
        payload = row.iloc[0].to_dict()
        payload["exam_id"] = exam_id
        payload["institute"] = institute
        return payload

    def build_timeseries_payload(
        self,
        exam_id: str,
        *,
        smooth: str = "none",
        start: Optional[float] = None,
        end: Optional[float] = None,
        views: Iterable[str] | None = None,
    ) -> Dict[str, object]:
        views_set = {v.strip().lower() for v in (views or []) if v}
        df = self.load_exam_dataframe(exam_id, start=start, end=end, smooth=smooth)
        if df.empty:
            return {"exam_id": exam_id, "smooth": smooth, "duration_sec": 0, "views": {}, "table": []}

        time_values = df["Time"].tolist() if "Time" in df.columns else list(range(len(df)))
        payload: Dict[str, object] = {
            "exam_id": exam_id,
            "smooth": smooth,
            "duration_sec": float(df["Time"].max()) if "Time" in df.columns else len(df),
            "views": {},
            "table": [],
        }

        # V-Slope
        vo2_series = df.get("VO2", pd.Series(dtype=float)).tolist()
        vco2_series = df.get("VCO2", pd.Series(dtype=float)).tolist()
        ve_series = df.get("VE", pd.Series(dtype=float)).tolist()
        hr_series = df.get("HR", pd.Series(dtype=float)).tolist()
        vt_series = df.get("VT", pd.Series(dtype=float)).tolist()
        rer_series = df.get("RER", pd.Series(dtype=float)).tolist()
        peto2_series = df.get("PetO2", pd.Series(dtype=float)).tolist()
        petco2_series = df.get("PetCO2", pd.Series(dtype=float)).tolist()

        # Panel 1: VE vs Time
        if not views_set or "panel1" in views_set:
            payload["views"]["panel1"] = {
                "time_sec": time_values,
                "ve": ve_series,
            }

        # Panel 2: HR vs Time
        if not views_set or "panel2" in views_set:
            payload["views"]["panel2"] = {
                "time_sec": time_values,
                "hr": hr_series,
            }

        # Panel 3: VO2 vs Time
        if not views_set or "panel3" in views_set:
            payload["views"]["panel3"] = {
                "time_sec": time_values,
                "vo2": vo2_series,
            }

        # Panel 4: VO2 vs VCO2 (second V-Slope / RCP view)
        if not views_set or "panel4" in views_set:
            payload["views"]["panel4"] = {
                "time_sec": time_values,
                "vo2": vo2_series,
                "vco2": vco2_series,
            }

        # Panel 5: Primary V-Slope (same as vslope for backward compatibility)
        if not views_set or "panel5" in views_set or "vslope" in views_set:
            payload["views"]["panel5"] = {
                "time_sec": time_values,
                "vo2": vo2_series,
                "vco2": vco2_series,
            }
            # legacy key for existing clients
            payload["views"]["vslope"] = payload["views"]["panel5"]

        # Panel 6
        if not views_set or "panel6" in views_set:
            payload["views"]["panel6"] = {
                "time_sec": time_values,
                "ve_vo2": df.get("VE_VO2", pd.Series(dtype=float)).tolist(),
                "ve_vco2": df.get("VE_VCO2", pd.Series(dtype=float)).tolist(),
            }

        # Panel 9
        if not views_set or "panel9" in views_set:
            payload["views"]["panel9"] = {
                "time_sec": time_values,
                "peto2": peto2_series,
                "petco2": petco2_series,
            }

        # Panel 7: VT vs VE (breathing pattern)
        if not views_set or "panel7" in views_set:
            payload["views"]["panel7"] = {
                "time_sec": time_values,
                "ve": ve_series,
                "vt": vt_series,
            }

        # Panel 8: RER vs Time
        if not views_set or "panel8" in views_set:
            payload["views"]["panel8"] = {
                "time_sec": time_values,
                "rer": rer_series,
            }

        table_cols = [
            "Time",
            "Load_Phase",
            "Power_Load",
            "VO2",
            "VCO2",
            "RER",
            "VE_VO2",
            "VE_VCO2",
            "PetO2",
            "PetCO2",
            "HR",
            "VE",
        ]
        for _, row in df.iterrows():
            entry = {col: row[col] if col in df.columns else None for col in table_cols}
            entry["Time"] = float(entry.get("Time") or 0.0)
            payload["table"].append(entry)

        return payload
