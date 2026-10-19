import os, shutil
from pathlib import Path
from enum import Enum
import sys
import stat

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
    port: int = 8001

    base_dir: Path = Path(__file__).parent
    tmp_dir: Path | None = None

    max_file_size_bytes: int = 1_000_000  # Skip files larger than 1MB
    poc_max_files: int = 1000  # PoC scope limit
    poc_max_depth: int = 10  # depth limit (to prevent zip bombs), just a safety measure
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

    async_max_threads: int = 4

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def init(self):
        if self.tmp_dir is None:
            self.tmp_dir = self.base_dir / "tmp"

        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        
    def close(self):
        if self.tmp_dir is None:
            return
        
        cleanup_dir(self.tmp_dir)
        #shutil.rmtree(self.tmp_dir)



def _make_writable_and_retry(func, path, _exc) -> None:
    """rmtree error handler: .git objects are read-only on Windows."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def cleanup_dir(path: Path) -> None:
    target = Path(path).resolve()
    if not target.exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(target, onexc=_make_writable_and_retry)
    else:
        shutil.rmtree(target, onerror=_make_writable_and_retry)

settings = Settings()