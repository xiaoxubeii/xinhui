# -*- coding: utf-8 -*-
"""HealthKit 数据同步 — JSON 文件存储"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from ..config import settings

def _data_root_for(user_id: str) -> Path:
    return settings.data_root / "users" / user_id / "healthkit"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_sync_data(
    user_id: str,
    device_id: str,
    payload: Dict[str, Any],
    data_root: Path | None = None,
) -> str:
    """持久化一次同步数据，返回 sync_id。"""
    sync_id = str(uuid4())
    root = data_root or _data_root_for(user_id)
    device_dir = root / device_id
    _ensure_dir(device_dir)

    record = {
        "sync_id": sync_id,
        "device_id": device_id,
        "synced_at": datetime.utcnow().isoformat() + "Z",
        "data": payload,
    }
    file_path = device_dir / f"{sync_id}.json"
    file_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return sync_id


def get_device_syncs(
    user_id: str,
    device_id: str,
    data_root: Path | None = None,
) -> List[Dict[str, Any]]:
    """返回指定设备的所有同步记录摘要（不含完整数据）。"""
    root = data_root or _data_root_for(user_id)
    device_dir = root / device_id
    if not device_dir.exists():
        return []

    syncs: List[Dict[str, Any]] = []
    for fp in sorted(device_dir.glob("*.json"), reverse=True):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
            data = record.get("data", {})
            syncs.append({
                "sync_id": record.get("sync_id", fp.stem),
                "synced_at": record.get("synced_at"),
                "sync_start": data.get("sync_start"),
                "sync_end": data.get("sync_end"),
                "counts": {
                    "daily_steps": len(data.get("daily_steps", [])),
                    "heart_rate_samples": len(data.get("heart_rate_samples", [])),
                    "resting_heart_rates": len(data.get("resting_heart_rates", [])),
                    "spo2_readings": len(data.get("spo2_readings", [])),
                    "sleep_sessions": len(data.get("sleep_sessions", [])),
                    "workouts": len(data.get("workouts", [])),
                },
            })
        except (json.JSONDecodeError, KeyError):
            continue
    return syncs


def get_device_summary(
    user_id: str,
    device_id: str,
    data_root: Path | None = None,
) -> Dict[str, Any]:
    """汇总指定设备的所有同步数据。"""
    root = data_root or _data_root_for(user_id)
    device_dir = root / device_id
    if not device_dir.exists():
        return {"device_id": device_id, "total_syncs": 0}

    total_syncs = 0
    total_counts: Dict[str, int] = {
        "daily_steps": 0,
        "heart_rate_samples": 0,
        "resting_heart_rates": 0,
        "spo2_readings": 0,
        "sleep_sessions": 0,
        "workouts": 0,
    }
    first_sync: str | None = None
    last_sync: str | None = None

    for fp in sorted(device_dir.glob("*.json")):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
            data = record.get("data", {})
            total_syncs += 1
            synced_at = record.get("synced_at")
            if synced_at:
                if first_sync is None:
                    first_sync = synced_at
                last_sync = synced_at
            for key in total_counts:
                total_counts[key] += len(data.get(key, []))
        except (json.JSONDecodeError, KeyError):
            continue

    return {
        "device_id": device_id,
        "total_syncs": total_syncs,
        "first_sync": first_sync,
        "last_sync": last_sync,
        "total_counts": total_counts,
    }
