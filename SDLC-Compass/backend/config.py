"""
AI-SDLC Compass — Application Configuration

Central configuration for the backend application.
Uses pydantic-settings for environment variable support.
"""

import os
from pathlib import Path
from enum import Enum
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings
from pydantic import Field


class LLMProvider(str, Enum):
    """Supported LLM provider backends."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # --- Application ---
    app_name: str = "AI-SDLC Compass"
    app_version: str = "0.1.0"
    debug: bool = True

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # scanner server info
    scanner_host: str = "0.0.0.0"
    scanner_port: int = 8001
    scanner_url_base: str = f"http://{scanner_host}:{scanner_port}/api/v1"

    # --- Paths ---
    base_dir: Path = Path(__file__).parent
    data_dir: Path | None = None
    workspaces_dir: Path | None = None
    reports_dir: Path | None = None

    # --- Database ---
    database_url: str | None = None

    # --- LLM Provider ---
    llm_provider: LLMProvider = LLMProvider.OLLAMA
    llm_model: str = "llama3.1"

    # Ollama settings
    ollama_host: str = "http://localhost:11434"

    # OpenAI settings (optional)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Anthropic settings (optional)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Google settings (optional)
    google_api_key: str = ""
    google_model: str = "gemini-pro"

    # --- Scanner ---
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

    # --- GitHub ---
    github_clone_timeout: int = 120  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def model_post_init(self, __context):
        """Set computed defaults after initialization."""
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"
        if self.workspaces_dir is None:
            self.workspaces_dir = self.data_dir / "workspaces"
        if self.reports_dir is None:
            self.reports_dir = self.data_dir / "reports"
        if self.database_url is None:
            self.database_url = f"sqlite+aiosqlite:///{self.data_dir / 'sdlc_compass.db'}"

        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)


# Singleton settings instance
settings = Settings()
