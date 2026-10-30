"""
Agent Service Configuration
"""

from pathlib import Path
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings


class Settings(BaseSettings):
    app_name: str = "SDLC-Compass-Agents"
    app_version: str = "0.1.0"
    debug: bool = True

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8002

    # Ollama settings
    ollama_host: str = "http://localhost:11434"
    chat_model: str = "qwen3:14b"
    temperature: float = 0.0
    think: bool = False
    """qwen3's hidden reasoning tokens were ~80% of generation time per call
    (measured) and never reach the report, so thinking is off by default."""
    num_ctx: int = 16384
    """One context size for every model call: Ollama reloads the model whenever
    num_ctx changes between requests. 8192 proved too small once a specialist
    read a few files (the prompt got truncated and re-processed every call)."""
    keep_alive: str = "30m"
    specialist_num_predict: int = 1500
    """Max tokens per specialist reply (a tool call, a note, or a short
    summary). Without a cap the model occasionally falls into repeating
    itself and generates until the context is full: one call took 4+ min."""
    synthesis_num_predict: int = 6000
    """The synthesizer returns the whole report as JSON, so it needs more."""
    require_question: bool = True
    """Send a specialist that finishes without asking the team anything back
    once to ask a question (see runner._nudge_if_silent)."""

    # Paths & Workspaces
    base_dir: Path = Path(__file__).parent.parent
    default_workspace_dir: Path = Path.cwd().resolve()
    workspaces_dir: Path | None = None
    """Where this service clones repos it needs to read. Under base_dir/data,
    which is already volume-mounted (see docker-compose.yml), so clones
    survive container restarts and a resumed pipeline/advisor chat can reuse
    one instead of re-cloning."""
    git_clone_timeout: int = 120  # seconds

    def model_post_init(self, __context) -> None:
        if self.workspaces_dir is None:
            self.workspaces_dir = self.base_dir / "data" / "workspaces"
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
