import os
from pathlib import Path
from enum import Enum

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings

from pydantic import Field

class Settings(BaseSettings):

    app_name: str = "SDLC-Compass-Scanner"
    app_version: str = "0.1.0"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int= 8001

    base_dir: Path = Path(__file__).parent
    tmp_dir: Path | None = None

    max_file_size_bytes: int = 1_000_000  # Skip files larger than 1MB
    poc_max_files: int = 50  # PoC scope limit
    excluded_dirs: list[str] = [
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "env", ".env", "dist", "build", ".next", ".nuxt",
        "vendor", "target", "bin", "obj", ".idea", ".vscode",
        ".terraform", "coverage", ".nyc_output", "htmlcov",
    ]
    excluded_extensions: list[str] = [
        ".pyc", ".pyo", ".class", ".o", ".so", ".dll", ".exe",
        ".jar", ".war", ".ear", ".zip", ".tar", ".gz", ".rar",
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".bmp",
        ".mp3", ".mp4", ".avi", ".mov", ".wav",
        ".ttf", ".woff", ".woff2", ".eot",
        ".lock", ".map",
    ]

    github_clone_timeout: int = 120 #seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def init(self):
        if self.tmp_dir is None:
            self.tmp_dir = self.base_dir / "tmp"

        self.tmp_dir.mkdir(parents=True, exist_ok=True)

settings = Settings()