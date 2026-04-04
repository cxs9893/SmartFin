from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FINQA_", env_file=".env", extra="ignore")

    app_name: str = "SmartFin"
    workspace_dir: Path = Field(default=Path(".finqa"))
    data_dir: Path = Field(default=Path("data"))
    index_dir: Path = Field(default=Path(".finqa/index"))
    llm_provider: str = "modelscope_local"
    llm_model: str = "models/Qwen2___5-0___5B-Instruct"
    llm_device: str = "auto"
    llm_max_new_tokens: int = 192
    llm_local_files_only: bool = True

    embedding_provider: str = "bge"
    embedding_batch_size: int = 32
    embedding_timeout_seconds: float = 30.0

    embedding_bge_model: str = "models/bge-base-zh-v1.5"
    embedding_bge_dim: int = 768
    embedding_bge_device: str = "cpu"
    embedding_bge_local_files_only: bool = True
    embedding_bge_trust_remote_code: bool = False
    embedding_strict_mode: bool = False

    embedding_hash_dim: int = 256


settings = Settings()
