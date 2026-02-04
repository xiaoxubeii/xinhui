from __future__ import annotations

import os
from pathlib import Path
from typing import List


class Settings:
    """Centralized configuration for the web annotation backend."""

    def __init__(self) -> None:
        base_dir = Path(__file__).resolve().parent
        default_data = Path(
            "/home/cheng/workspace/cpetx_workspace/cpet_former/artifacts/dataset/processed/processed_institutes.h5"
        )
        default_model_config = Path(
            "/home/cheng/workspace/cpetx_workspace/cpet_former/configs/model/v4/pace_former_experiment/9.yaml"
        )
        default_model_checkpoint = Path(
            "/home/cheng/workspace/cpetx_workspace/cpet_former/pace/v4/internal/variants/models/9/train/artifacts/best_model.pth"
        )
        self.data_file: Path = Path(
            os.environ.get("CPET_DATA_FILE", default_data)
        ).expanduser()
        self.db_path: Path = Path(
            os.environ.get("CPET_WEB_DB", base_dir / "annotations.db")
        ).expanduser()
        self.pace_former_config: Path = Path(
            os.environ.get("CPET_PACE_CONFIG", default_model_config)
        ).expanduser()
        self.pace_former_checkpoint: Path = Path(
            os.environ.get("CPET_PACE_CHECKPOINT", default_model_checkpoint)
        ).expanduser()
        self.pace_former_device: str = os.environ.get(
            "CPET_PACE_DEVICE", "cpu"
        )
        self.pace_former_eval_mode: str = os.environ.get(
            "CPET_PACE_EVAL_MODE", "online"
        )
        self.pace_former_norm: str = os.environ.get(
            "CPET_PACE_NORM", "per_exam"
        )
        self.pace_former_norm_min_points: int = int(
            os.environ.get("CPET_PACE_NORM_MIN_POINTS", "12")
        )
        self.pace_former_min_points: int = int(
            os.environ.get("CPET_PACE_MIN_POINTS", "8")
        )
        self.sim_default_speed: float = float(
            os.environ.get("CPET_SIM_SPEED", "1.0")
        )
        self.sim_default_smooth: str = os.environ.get(
            "CPET_SIM_SMOOTH", "none"
        )
        self.delta_sec: float = float(os.environ.get("CPET_DELTA_SEC", "15"))
        self.agent_config_path: Path = Path(
            os.environ.get("CPET_AGENT_CONFIG", base_dir.parent / "opencode.json")
        ).expanduser()
        self.qwen_api_key: str | None = os.environ.get("QWEN_API_KEY")
        self.qwen_base_url: str = os.environ.get(
            "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.qwen_model: str = os.environ.get("QWEN_MODEL", "qwen-plus")
        self.qwen_timeout: float = float(os.environ.get("QWEN_TIMEOUT", "30"))
        self.qwen_max_tokens: int = int(os.environ.get("QWEN_MAX_TOKENS", "512"))
        self.qwen_temperature: float = float(os.environ.get("QWEN_TEMPERATURE", "0.2"))
        self.opencode_base_url: str = os.environ.get(
            "OPENCODE_BASE_URL", "http://127.0.0.1:4096"
        )
        self.opencode_directory: Path = Path(
            os.environ.get("OPENCODE_DIRECTORY", base_dir.parent)
        ).expanduser()
        cors = os.environ.get("CPET_CORS_ORIGINS", "*")
        if cors.strip() == "*":
            self.cors_origins: List[str] = ["*"]
        else:
            self.cors_origins = [
                origin.strip() for origin in cors.split(",") if origin.strip()
            ]


settings = Settings()
