"""应用配置；不读取或打印任何密钥。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AppSettings:
    service_name: str = "xinghe-ecommerce-agent"
    version: str = "2.0.0"
    api_v1_prefix: str = "/api/v1"
    legacy_prefix: str = "/v1"
    data_directory: Path = PROJECT_ROOT / ".agent_data" / "app"
    use_llm: bool = False
    rate_limit: int = 30
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    @classmethod
    def from_environment(cls) -> "AppSettings":
        origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "ECOMMERCE_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        )
        return cls(
            data_directory=Path(
                os.getenv("ECOMMERCE_DATA_DIRECTORY", str(cls.data_directory))
            ),
            use_llm=os.getenv("ECOMMERCE_USE_LLM", "false").lower()
            in {"1", "true", "yes"},
            rate_limit=int(os.getenv("ECOMMERCE_RATE_LIMIT", "30")),
            cors_origins=origins,
        )
