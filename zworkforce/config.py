from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import os

@dataclass(frozen=True)
class Rate:
    input: float
    cached: float
    output: float

@dataclass(frozen=True)
class Settings:
    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 9569
    data_dir: Path = Path("./data")
    workspace_root: Path = Path(".")
    max_workers: int = 4
    provider: str = "mock"
    provider_base_url: str = "https://api.openai.com/v1"
    provider_api_key: str = ""
    model_sol: str = "gpt-5.6"
    model_terra: str = "gpt-5.6-terra"
    model_luna: str = "gpt-5.6-luna"
    api_keys: tuple[tuple[str, str], ...] = (("dev-admin", "admin"), ("dev-operator", "operator"), ("dev-viewer", "viewer"))
    http_allowlist: tuple[str, ...] = ()
    shell_enabled: bool = False
    shell_allowlist: tuple[str, ...] = ("git", "python", "python3", "node", "npm")
    tool_timeout_seconds: int = 30
    max_request_bytes: int = 1_048_576
    global_daily_budget_credits: float = 0.0
    rates: dict[str, Rate] = field(default_factory=lambda: {
        "sol": Rate(125.0, 12.5, 750.0),
        "terra": Rate(50.0, 5.0, 300.0),
        "luna": Rate(5.0, 0.5, 30.0),
    })

    @property
    def database_path(self) -> Path:
        return self.data_dir / "zworkforce.sqlite3"

    def model_for_tier(self, tier: str) -> str:
        return {"sol": self.model_sol, "terra": self.model_terra, "luna": self.model_luna}[tier]

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.getenv("ZWORKFORCE_ENV", "development").strip().lower()
        raw_keys = os.getenv("ZWORKFORCE_API_KEYS", "").strip()
        if raw_keys:
            keys = []
            for item in raw_keys.split(","):
                key, sep, role = item.partition(":")
                if not sep or role not in {"admin", "operator", "viewer"} or not key:
                    raise ValueError("ZWORKFORCE_API_KEYS must use key:role entries with admin|operator|viewer")
                keys.append((key, role))
            api_keys = tuple(keys)
        elif env == "production":
            raise ValueError("ZWORKFORCE_API_KEYS is required in production")
        else:
            api_keys = cls().api_keys
        def f(name: str, default: float) -> float:
            return float(os.getenv(name, str(default)))
        def b(name: str, default: bool = False) -> bool:
            return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}
        def csv(name: str, default: str = "") -> tuple[str, ...]:
            return tuple(x.strip() for x in os.getenv(name, default).split(",") if x.strip())
        rates = {
            "sol": Rate(f("ZWORKFORCE_SOL_INPUT_CREDITS", 125), f("ZWORKFORCE_SOL_CACHED_CREDITS", 12.5), f("ZWORKFORCE_SOL_OUTPUT_CREDITS", 750)),
            "terra": Rate(f("ZWORKFORCE_TERRA_INPUT_CREDITS", 50), f("ZWORKFORCE_TERRA_CACHED_CREDITS", 5), f("ZWORKFORCE_TERRA_OUTPUT_CREDITS", 300)),
            "luna": Rate(f("ZWORKFORCE_LUNA_INPUT_CREDITS", 5), f("ZWORKFORCE_LUNA_CACHED_CREDITS", .5), f("ZWORKFORCE_LUNA_OUTPUT_CREDITS", 30)),
        }
        return cls(
            env=env,
            host=os.getenv("ZWORKFORCE_HOST", "0.0.0.0"),
            port=int(os.getenv("ZWORKFORCE_PORT", "9569")),
            data_dir=Path(os.getenv("ZWORKFORCE_DATA_DIR", "./data")).expanduser().resolve(),
            workspace_root=Path(os.getenv("ZWORKFORCE_WORKSPACE_ROOT", ".")).expanduser().resolve(),
            max_workers=max(1, int(os.getenv("ZWORKFORCE_MAX_WORKERS", "4"))),
            provider=os.getenv("ZWORKFORCE_PROVIDER", "mock").strip().lower(),
            provider_base_url=os.getenv("ZWORKFORCE_PROVIDER_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            provider_api_key=os.getenv("ZWORKFORCE_PROVIDER_API_KEY", ""),
            model_sol=os.getenv("ZWORKFORCE_MODEL_SOL", "gpt-5.6"),
            model_terra=os.getenv("ZWORKFORCE_MODEL_TERRA", "gpt-5.6-terra"),
            model_luna=os.getenv("ZWORKFORCE_MODEL_LUNA", "gpt-5.6-luna"),
            api_keys=api_keys,
            http_allowlist=csv("ZWORKFORCE_HTTP_ALLOWLIST"),
            shell_enabled=b("ZWORKFORCE_SHELL_ENABLED"),
            shell_allowlist=csv("ZWORKFORCE_SHELL_ALLOWLIST", "git,python,python3,node,npm"),
            tool_timeout_seconds=max(1, int(os.getenv("ZWORKFORCE_TOOL_TIMEOUT_SECONDS", "30"))),
            max_request_bytes=max(1024, int(os.getenv("ZWORKFORCE_MAX_REQUEST_BYTES", "1048576"))),
            global_daily_budget_credits=max(0.0, f("ZWORKFORCE_GLOBAL_DAILY_BUDGET_CREDITS", 0)),
            rates=rates,
        )
