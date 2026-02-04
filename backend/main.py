from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import settings
from .consensus import recompute_consensus
from .data_loader import CPETStudyData
from .db import db_conn, init_db
from .replay_data import load_replay_sequence, list_replay_sequences, scan_results_dir

app = FastAPI(
    title="CPET AT Web Annotation",
    description="Two-readers-plus-adjudicator workflow for CPET AT labeling.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared services
data_store = CPETStudyData(settings.data_file)
init_db(settings.db_path)


class AnnotationRequest(BaseModel):
    role: str = Field(..., description="a | b | adjudicator")
    reader_id: str = Field(..., description="Identifier for the annotator")
    at_time_sec: float
    smoothing: Optional[str] = "none"
    notes: Optional[str] = None


class AnnotationResponse(BaseModel):
    exam_id: str
    status: str
    t_gt: Optional[float]
    t_a: Optional[float]
    t_b: Optional[float]
    t_c: Optional[float]
    delta_sec: float


class ReplayScanRequest(BaseModel):
    results_dir: str = Field(..., description="Path to results root or mode dir")


class ReplayListRequest(BaseModel):
    results_dir: str = Field(..., description="Path to results root or mode dir")
    split: str = Field("val", description="Split name (train/val/test)")
    mode: str = Field("online", description="online | offline")


class ReplaySequenceRequest(BaseModel):
    results_dir: str = Field(..., description="Path to results root or mode dir")
    split: str = Field("val", description="Split name (train/val/test)")
    mode: str = Field("online", description="online | offline")
    examination_id: str = Field(..., description="Examination id to load")
    default_step_sec: float = Field(
        10.0, description="Fallback step size when times are missing"
    )


@app.get("/api/exams")
def list_exams(limit: int = 50, institute: Optional[str] = None) -> List[dict]:
    """List available exams from the processed H5 manifest."""
    return data_store.list_exams(limit=limit, institute=institute)


@app.get("/api/exams/{exam_id}/timeseries")
def get_timeseries(
    exam_id: str,
    smooth: str = "sec:10",
    views: Optional[str] = None,
    start: Optional[float] = None,
    end: Optional[float] = None,
) -> dict:
    """Return smoothed timeseries slices for visualization panels."""
    view_list = views.split(",") if views else []
    try:
        payload = data_store.build_timeseries_payload(
            exam_id,
            smooth=smooth,
            start=start,
            end=end,
            views=view_list,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return payload


@app.post("/api/exams/{exam_id}/annotations", response_model=AnnotationResponse)
def save_annotation(exam_id: str, request: AnnotationRequest) -> AnnotationResponse:
    role = request.role.lower().strip()
    if role not in {"a", "b", "adjudicator"}:
        raise HTTPException(status_code=400, detail="role must be a, b, or adjudicator")
    with db_conn(settings.db_path) as conn:
        conn.execute(
            """
            INSERT INTO annotations (exam_id, reader_id, role, at_time, smoothing, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam_id,
                request.reader_id,
                role,
                float(request.at_time_sec),
                request.smoothing,
                request.notes,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        state = recompute_consensus(conn, exam_id, settings.delta_sec)
    return AnnotationResponse(exam_id=exam_id, **state)


@app.get("/api/exams/{exam_id}/consensus", response_model=AnnotationResponse)
def get_consensus(exam_id: str) -> AnnotationResponse:
    with db_conn(settings.db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT status, t_gt, t_a, t_b, t_c, delta FROM consensus WHERE exam_id=?",
            (exam_id,),
        )
        row = cur.fetchone()
        if not row:
            state = recompute_consensus(conn, exam_id, settings.delta_sec)
        else:
            status, t_gt, t_a, t_b, t_c, delta = row
            state = {
                "status": status,
                "t_gt": t_gt,
                "t_a": t_a,
                "t_b": t_b,
                "t_c": t_c,
                "delta_sec": delta,
            }
    return AnnotationResponse(exam_id=exam_id, **state)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/replay/scan")
def replay_scan(request: ReplayScanRequest) -> List[dict]:
    datasets = scan_results_dir(request.results_dir)
    return [
        {
            "split": d.split,
            "mode": d.mode,
            "prob_file": str(d.prob_file) if d.prob_file else None,
            "vo2_file": str(d.vo2_file) if d.vo2_file else None,
            "at_file": str(d.at_file) if d.at_file else None,
            "ready": d.ready,
            "has_vo2": d.vo2_file is not None,
        }
        for d in datasets
    ]


@app.post("/api/replay/list")
def replay_list(request: ReplayListRequest) -> dict:
    payload = list_replay_sequences(
        results_dir=request.results_dir,
        split=request.split,
        mode=request.mode,
    )
    return payload


@app.post("/api/replay/sequence")
def replay_sequence(request: ReplaySequenceRequest) -> dict:
    return load_replay_sequence(
        results_dir=request.results_dir,
        split=request.split,
        mode=request.mode,
        examination_id=request.examination_id,
        default_step_sec=request.default_step_sec,
    )


# Static frontend
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="app")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="frontend not found")
    return FileResponse(index_file)
