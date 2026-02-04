from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

_RESULT_PATTERN = re.compile(
    r"^(?P<split>.+)_results_(?P<mode>online|offline)_(?P<tag>probs|vo2_seq|at)\.json$"
)

_CENTER_MAP_CACHE: Dict[Path, Dict[int, str]] = {}


@dataclass(frozen=True)
class ReplayDatasetInfo:
    split: str
    mode: str
    prob_file: Optional[Path]
    vo2_file: Optional[Path]
    at_file: Optional[Path]

    @property
    def ready(self) -> bool:
        return self.prob_file is not None


def _resolve_results_root(path: Path) -> Tuple[Path, Optional[str]]:
    if path.name in {"online", "offline"}:
        return path.parent, path.name
    return path, None


def _find_mode_dirs(base_dir: Path, forced_mode: Optional[str]) -> Dict[str, Path]:
    if forced_mode:
        mode_dir = base_dir / forced_mode
        return {forced_mode: mode_dir} if mode_dir.exists() else {}
    mode_dirs = {}
    for name in ("online", "offline"):
        mode_dir = base_dir / name
        if mode_dir.exists():
            mode_dirs[name] = mode_dir
    return mode_dirs


def _scan_mode_dir(mode_dir: Path) -> Dict[Tuple[str, str], ReplayDatasetInfo]:
    datasets: Dict[Tuple[str, str], ReplayDatasetInfo] = {}
    for file_path in mode_dir.glob("*.json"):
        match = _RESULT_PATTERN.match(file_path.name)
        if not match:
            continue
        split = match.group("split")
        mode = match.group("mode")
        tag = match.group("tag")
        key = (split, mode)
        info = datasets.get(
            key,
            ReplayDatasetInfo(
                split=split,
                mode=mode,
                prob_file=None,
                vo2_file=None,
                at_file=None,
            ),
        )
        if tag == "probs":
            info = ReplayDatasetInfo(
                split=info.split,
                mode=info.mode,
                prob_file=file_path,
                vo2_file=info.vo2_file,
                at_file=info.at_file,
            )
        elif tag == "vo2_seq":
            info = ReplayDatasetInfo(
                split=info.split,
                mode=info.mode,
                prob_file=info.prob_file,
                vo2_file=file_path,
                at_file=info.at_file,
            )
        elif tag == "at":
            info = ReplayDatasetInfo(
                split=info.split,
                mode=info.mode,
                prob_file=info.prob_file,
                vo2_file=info.vo2_file,
                at_file=file_path,
            )
        datasets[key] = info
    return datasets


def scan_results_dir(results_dir: str) -> List[ReplayDatasetInfo]:
    base_dir = Path(results_dir).expanduser().resolve()
    if not base_dir.exists():
        raise FileNotFoundError(f"results_dir not found: {results_dir}")
    base_dir, forced_mode = _resolve_results_root(base_dir)
    mode_dirs = _find_mode_dirs(base_dir, forced_mode)
    datasets: Dict[Tuple[str, str], ReplayDatasetInfo] = {}
    for mode_dir in mode_dirs.values():
        datasets.update(_scan_mode_dir(mode_dir))
    results = list(datasets.values())
    results.sort(key=lambda item: (item.mode, item.split))
    return results


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_vo2_peak_label(target: Optional[Iterable[Any]]) -> Optional[float]:
    if not target:
        return None
    values: List[float] = []
    for raw in target:
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isfinite(val):
            values.append(val)
    if not values:
        return None
    return float(max(values))


def _normalize_times(
    times: Optional[Iterable[Any]],
    seq_len: int,
    default_step_sec: float,
) -> List[float]:
    if times is not None:
        try:
            time_list = [float(x) for x in times]
            if len(time_list) == seq_len:
                return time_list
        except Exception:
            pass
    return [float(i) * float(default_step_sec) for i in range(seq_len)]


def _build_at_lookup(at_payload: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    if not at_payload:
        return {}
    exam_ids = at_payload.get("examination_ids") or []
    preds = at_payload.get("predictions") or []
    targets = at_payload.get("targets") or []
    at_lookup: Dict[str, Dict[str, float]] = {}
    for idx, exam_id in enumerate(exam_ids):
        if exam_id is None:
            continue
        pred_val = preds[idx] if idx < len(preds) else None
        tgt_val = targets[idx] if idx < len(targets) else None
        payload: Dict[str, float] = {}
        try:
            if pred_val is not None and math.isfinite(float(pred_val)):
                payload["at_pred"] = float(pred_val)
        except (TypeError, ValueError):
            pass
        try:
            if tgt_val is not None and math.isfinite(float(tgt_val)):
                payload["at_target"] = float(tgt_val)
        except (TypeError, ValueError):
            pass
        if payload:
            at_lookup[str(exam_id)] = payload
    return at_lookup


def _extract_center_mapping(data: Dict[str, Any]) -> Dict[int, str]:
    mapping = data.get("center_mapping")
    if not isinstance(mapping, dict):
        return {}
    center_map: Optional[Dict[str, Any]] = None
    if any(isinstance(v, dict) for v in mapping.values()):
        if isinstance(mapping.get("Institute_Name"), dict):
            center_map = mapping.get("Institute_Name")
        else:
            center_map = next(
                (v for v in mapping.values() if isinstance(v, dict)),
                None,
            )
    else:
        center_map = mapping
    if not isinstance(center_map, dict):
        return {}
    id_to_name: Dict[int, str] = {}
    for name, idx in center_map.items():
        try:
            idx_val = int(idx)
        except (TypeError, ValueError):
            continue
        name_val = str(name).strip()
        if name_val and idx_val not in id_to_name:
            id_to_name[idx_val] = name_val
    return id_to_name


def _load_center_id_mapping(results_dir: str) -> Dict[int, str]:
    base_dir = Path(results_dir).expanduser().resolve()
    base_dir, _ = _resolve_results_root(base_dir)
    cached = _CENTER_MAP_CACHE.get(base_dir)
    if cached is not None:
        return cached
    mapping: Dict[int, str] = {}
    if yaml is None:
        _CENTER_MAP_CACHE[base_dir] = mapping
        return mapping
    config_root = base_dir.parent / "configs"
    if config_root.exists():
        candidates = list(config_root.rglob("*.yaml")) + list(
            config_root.rglob("*.yml")
        )
        for path in sorted(candidates):
            try:
                content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            mapping = _extract_center_mapping(content)
            if mapping:
                break
    _CENTER_MAP_CACHE[base_dir] = mapping
    return mapping


def _resolve_dataset(results_dir: str, split: str, mode: str) -> ReplayDatasetInfo:
    datasets = scan_results_dir(results_dir)
    target = next(
        (
            item
            for item in datasets
            if item.split == split and item.mode == mode
        ),
        None,
    )
    if target is None:
        raise FileNotFoundError(
            f"No dataset found for split={split}, mode={mode} under {results_dir}"
        )
    if target.prob_file is None:
        raise FileNotFoundError(
            f"Missing probs file for split={split}, mode={mode}"
        )
    return target


def list_replay_sequences(
    *, results_dir: str, split: str, mode: str
) -> Dict[str, Any]:
    target = _resolve_dataset(results_dir, split, mode)
    center_map = _load_center_id_mapping(results_dir)
    prob_payload = _load_json(target.prob_file)
    prob_sequences = prob_payload.get("sequences") or []
    vo2_ids: set[str] = set()
    if target.vo2_file:
        vo2_payload = _load_json(target.vo2_file)
        vo2_sequences = vo2_payload.get("sequences") or []
        for seq in vo2_sequences:
            exam_id = str(seq.get("examination_id", "")).strip()
            if exam_id:
                vo2_ids.add(exam_id)

    items: List[Dict[str, Any]] = []
    for seq in prob_sequences:
        exam_id = str(seq.get("examination_id", "")).strip()
        if not exam_id:
            continue
        probs = seq.get("probs") or []
        center_id = seq.get("center_id")
        center_name = None
        if center_id is not None:
            try:
                center_name = center_map.get(int(center_id))
            except (TypeError, ValueError):
                center_name = None
        items.append(
            {
                "examination_id": exam_id,
                "t_star": seq.get("t_star"),
                "length": len(probs),
                "has_vo2": exam_id in vo2_ids,
                "center_id": center_id,
                "center_name": center_name,
            }
        )

    return {
        "split": split,
        "mode": mode,
        "sequence_count": len(items),
        "sequences": items,
    }


def load_replay_sequence(
    *,
    results_dir: str,
    split: str,
    mode: str,
    examination_id: str,
    default_step_sec: float = 10.0,
) -> Dict[str, Any]:
    target = _resolve_dataset(results_dir, split, mode)
    center_map = _load_center_id_mapping(results_dir)
    prob_payload = _load_json(target.prob_file)
    prob_sequences = prob_payload.get("sequences") or []
    prob_map: Dict[str, Dict[str, Any]] = {}
    for seq in prob_sequences:
        exam_id = str(seq.get("examination_id", "")).strip()
        if not exam_id:
            continue
        prob_map[exam_id] = seq

    seq = prob_map.get(examination_id)
    if seq is None:
        raise FileNotFoundError(f"examination_id not found: {examination_id}")

    vo2_map: Dict[str, Dict[str, Any]] = {}
    if target.vo2_file:
        vo2_payload = _load_json(target.vo2_file)
        for vseq in vo2_payload.get("sequences") or []:
            exam_id = str(vseq.get("examination_id", "")).strip()
            if not exam_id:
                continue
            vo2_map[exam_id] = vseq

    at_payload = _load_json(target.at_file) if target.at_file else None
    at_lookup = _build_at_lookup(at_payload)

    probs = seq.get("probs") or []
    mask = seq.get("mask") or []
    seq_len = len(probs)
    times_raw = seq.get("times")
    times = _normalize_times(times_raw, seq_len, default_step_sec)

    center_id = seq.get("center_id")
    center_name = None
    if center_id is not None:
        try:
            center_name = center_map.get(int(center_id))
        except (TypeError, ValueError):
            center_name = None

    record: Dict[str, Any] = {
        "examination_id": examination_id,
        "probs": probs,
        "mask": mask,
        "t_star": seq.get("t_star"),
        "times": times,
        "center_id": center_id,
        "center_name": center_name,
        "phase": seq.get("phase"),
        "default_step_sec": float(default_step_sec),
        "source": {
            "results_dir": str(Path(results_dir).expanduser().resolve()),
            "prob_file": str(target.prob_file),
            "vo2_file": str(target.vo2_file) if target.vo2_file else None,
            "at_file": str(target.at_file) if target.at_file else None,
            "loaded_at": datetime.utcnow().isoformat(timespec="seconds"),
        },
    }

    vo2_seq = vo2_map.get(examination_id)
    if vo2_seq is None:
        record.update(
            {
                "vo2_pred": None,
                "vo2_target": None,
                "vo2_mask": None,
                "vo2_peak_label": None,
                "vo2_weight_kg": None,
            }
        )
    else:
        vo2_target = vo2_seq.get("target") or []
        record.update(
            {
                "vo2_pred": vo2_seq.get("pred"),
                "vo2_target": vo2_target,
                "vo2_mask": vo2_seq.get("mask"),
                "vo2_peak_label": _resolve_vo2_peak_label(vo2_target),
                "vo2_weight_kg": vo2_seq.get("weight_kg"),
            }
        )

    at_info = at_lookup.get(examination_id)
    if at_info:
        record.update(at_info)

    return record
