"""App settings. Reads env vars (and .env); values are never printed. (Pattern reused from Need Map Chat.)"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    bp_dataset: str = ""  # env BP_DATASET, e.g. "100k"; empty → 100k, else 10k, 1m, 10m (first that exists)
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.6-flash"
    gemini_rpm: int = 10  # client-side requests/min (stay under the free tier)
    mock_llm: bool = False
    mock_chat: bool = False
    n_boot: int = 100  # env N_BOOT: optimizer bootstrap iterations

    @property
    def data_dir(self) -> Path:
        return ROOT / "data"

    @property
    def bench_dir(self) -> Path:
        return ROOT / "bench"


settings = Settings()
