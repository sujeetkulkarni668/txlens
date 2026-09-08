"""Application configuration.

Loaded from environment variables (see .env.example at repo root). No
provider is hard-coded here — RPC endpoints, AI provider, and secrets are
all configurable so TxLens never binds itself to one vendor.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_env: str = Field(default="development", alias="API_ENV")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_secret_key: str = Field(default="change-me-in-local-env", alias="API_SECRET_KEY")
    api_cors_origins: str = Field(default="http://localhost:3000", alias="API_CORS_ORIGINS")

    database_url: str = Field(
        default="postgresql+asyncpg://txlens:txlens@localhost:5432/txlens",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    evm_chain: str = Field(default="base-sepolia", alias="EVM_CHAIN")
    evm_rpc_url: str = Field(default="https://sepolia.base.org", alias="EVM_RPC_URL")
    evm_chain_id: int = Field(default=84532, alias="EVM_CHAIN_ID")

    ai_provider: str = Field(default="anthropic", alias="AI_PROVIDER")
    ai_api_key: str = Field(default="", alias="AI_API_KEY")
    ai_model: str = Field(default="", alias="AI_MODEL")

    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.api_env.lower() in ("production", "prod")

    def insecure_defaults(self) -> list[str]:
        """Returns a list of human-readable problems if any secret is
        still at its insecure .env.example default. Checked at startup
        (see main.py) — a production deployment must fail loudly here
        rather than silently run with a guessable JWT signing key."""
        problems = []
        if self.api_secret_key == "change-me-in-local-env":
            problems.append(
                "API_SECRET_KEY is still the default placeholder value — this key signs "
                "every access token; anyone who knows it can forge a valid login for any "
                "user. Set a real random value in .env."
            )
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
