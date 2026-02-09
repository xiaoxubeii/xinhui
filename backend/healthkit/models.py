# -*- coding: utf-8 -*-
"""HealthKit 数据同步 — Pydantic 模型"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DailySteps(BaseModel):
    date: str = Field(..., description="ISO8601 日期，如 2025-01-15")
    count: int = Field(..., ge=0)


class HeartRateSample(BaseModel):
    timestamp: str = Field(..., description="ISO8601 时间戳")
    bpm: float = Field(..., gt=0)


class RestingHeartRate(BaseModel):
    date: str
    bpm: float = Field(..., gt=0)


class SpO2Reading(BaseModel):
    timestamp: str
    percentage: float = Field(..., ge=0, le=100)


class SleepSession(BaseModel):
    start_time: str
    end_time: str
    stage: str = Field(..., description="inBed | awake | core | deep | rem")


class WorkoutRecord(BaseModel):
    start_time: str
    end_time: str
    activity_type: str = Field(..., description="running, cycling, walking, etc.")
    duration_seconds: float = Field(..., ge=0)
    total_energy_kcal: Optional[float] = None
    total_distance_meters: Optional[float] = None
    avg_heart_rate: Optional[float] = None
    max_heart_rate: Optional[float] = None


class HealthSyncRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    sync_start: str = Field(..., description="ISO8601 同步起始时间")
    sync_end: str = Field(..., description="ISO8601 同步结束时间")
    daily_steps: List[DailySteps] = []
    heart_rate_samples: List[HeartRateSample] = []
    resting_heart_rates: List[RestingHeartRate] = []
    spo2_readings: List[SpO2Reading] = []
    sleep_sessions: List[SleepSession] = []
    workouts: List[WorkoutRecord] = []


class HealthSyncResponse(BaseModel):
    status: str = Field(..., description="ok | partial | error")
    message: str
    received_counts: Dict[str, int]
    sync_id: str = Field(..., description="本次同步的 UUID")
