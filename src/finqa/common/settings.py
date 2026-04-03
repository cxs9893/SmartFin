from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FINQA_", env_file=".env", extra="ignore")

    app_name: str = "SmartFin"
    workspace_dir: Path = Field(default=Path(".finqa"))
    data_dir: Path = Field(default=Path("data"))
    index_dir: Path = Field(default=Path(".finqa/index"))


settings = Settings()
