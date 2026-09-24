from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    work_dir: Path = Path(".work")
    max_file_size: int = 500 * 1024 * 1024
    small_file_threshold: int = 20 * 1024 * 1024
    chunk_size: int = 5 * 1024 * 1024
    max_iterations: int = 3
    ssim_threshold: float = .90
    rate_limit_per_minute: int = 30
    max_workers: int | None = None
    ffmpeg_binary: str = "ffmpeg"

settings = Settings()
settings.work_dir.mkdir(parents=True, exist_ok=True)
