from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Dict, Optional, Tuple


def _latest_by_role(rows: list[Tuple[str, float, str]]) -> Dict[str, Tuple[float, str]]:
    """Return the latest annotation per role."""
    latest: Dict[str, Tuple[float, str]] = {}
    for role, at_time, created_at in rows:
        if role not in latest or created_at > latest[role][1]:
            latest[role] = (at_time, created_at)
    return latest


def recompute_consensus(
    conn: sqlite3.Connection,
    exam_id: str,
    delta_sec: float,
) -> Dict[str, Optional[float]]:
    """
    Recompute consensus state for a given exam:
    - If both A and B exist and |tA - tB| <= delta => concordant, t_gt=avg.
    - If both exist and diff > delta => discordant (await adjudication).
    - If adjudicator present => finalized, t_gt = t_c.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT role, at_time, created_at FROM annotations WHERE exam_id=?",
        (exam_id,),
    )
    rows = cur.fetchall()
    latest = _latest_by_role(rows)
    t_a = latest.get("a", (None, None))[0]
    t_b = latest.get("b", (None, None))[0]
    t_c = latest.get("adjudicator", (None, None))[0]

    status = "pending"
    t_gt: Optional[float] = None

    if t_c is not None:
        status = "finalized"
        t_gt = t_c
    elif t_a is not None and t_b is not None:
        diff = abs(t_a - t_b)
        if diff <= delta_sec:
            status = "concordant"
            t_gt = (t_a + t_b) / 2.0
        else:
            status = "discordant"
    elif t_a is not None or t_b is not None:
        status = "partial"

    cur.execute(
        """
        INSERT INTO consensus (exam_id, delta, status, t_a, t_b, t_c, t_gt, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(exam_id) DO UPDATE SET
            delta=excluded.delta,
            status=excluded.status,
            t_a=excluded.t_a,
            t_b=excluded.t_b,
            t_c=excluded.t_c,
            t_gt=excluded.t_gt,
            updated_at=excluded.updated_at
        """,
        (
            exam_id,
            float(delta_sec),
            status,
            t_a,
            t_b,
            t_c,
            t_gt,
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )
    return {
        "status": status,
        "t_gt": t_gt,
        "t_a": t_a,
        "t_b": t_b,
        "t_c": t_c,
        "delta_sec": delta_sec,
    }
