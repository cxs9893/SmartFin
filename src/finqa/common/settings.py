from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FINQA_", env_file=".env", extra="ignore")

    app_name: str = "SmartFin"
    workspace_dir: Path = Field(default=Path(".finqa"))
    data_dir: Path = Field(default=Path("data"))
    index_dir: Path = Field(default=Path(".finqa/index"))
    llm_provider: str = "qwen"
    llm_api_key: str = ""
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model: str = "qwen3-max-2026-01-23"
    llm_timeout_seconds: int = 20


settings = Settings()
