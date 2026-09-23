from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Settings:
    max_bytes: int = int(os.getenv("WM_MAX_BYTES", str(50 * 1024 * 1024)))
    max_pages: int = int(os.getenv("WM_MAX_PAGES", "100"))
    task_ttl_seconds: int = int(os.getenv("WM_TASK_TTL", "3600"))
    temp_dir: Path = Path(os.getenv("WM_TEMP_DIR", ".wm-tasks"))
settings = Settings()
