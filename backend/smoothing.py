from __future__ import annotations

import re
from typing import Tuple

import numpy as np
import pandas as pd


def parse_smoothing(smooth: str) -> Tuple[str, int]:
    key = (smooth or "").lower().strip()
    if key in {"", "none", "raw"}:
        return "none", 0
    match = re.match(r"(breath|sec)[:_]?(\d+)", key)
    if match:
        mode = match.group(1)
        try:
            window = int(match.group(2))
        except ValueError:
            window = 0
        return mode, max(0, window)
    return "none", 0


def apply_smoothing(df: pd.DataFrame, smooth: str) -> pd.DataFrame:
    """Apply breath-based rolling or time-based resample smoothing."""
    mode, window = parse_smoothing(smooth)
    if df.empty or mode == "none" or window <= 0:
        return df.copy()

    working = df.copy()
    numeric_cols = working.select_dtypes(include=[np.number]).columns.tolist()
    time_col = "Time"

    if mode == "breath":
        working[numeric_cols] = (
            working[numeric_cols].rolling(window=window, min_periods=1).mean()
        )
        return working

    if mode == "sec":
        if time_col not in working.columns:
            return df.copy()
        working = working.sort_values(time_col)
        working["_time_index"] = pd.to_timedelta(working[time_col], unit="s")
        working = working.set_index("_time_index")
        aggregated = working[numeric_cols].resample(f"{window}S").mean()
        non_numeric = [
            col for col in working.columns if col not in numeric_cols and col != "_time_index"
        ]
        for col in non_numeric:
            aggregated[col] = working[col].resample(f"{window}S").ffill()
        aggregated[time_col] = aggregated.index.total_seconds()
        aggregated = aggregated.reset_index(drop=True)
        return aggregated

    return df.copy()
