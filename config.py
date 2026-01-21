import os
from functools import lru_cache
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # --------------------
    # Environment
    # --------------------
    env: str = Field(default_factory=lambda: os.getenv("ENV", "dev"))

    # --------------------
    # Supabase (auth + storage)
    # --------------------
    public_supabase_url: str = Field(default_factory=lambda: os.getenv("PUBLIC_SUPABASE_URL", ""))
    supabase_service_role_key: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    )

    # Used only if you authenticate *to Supabase* with email/pass
    supabase_username: str | None = Field(
        default_factory=lambda: os.getenv("SUPABASE_USERNAME")
    )
    supabase_userpass: str | None = Field(
        default_factory=lambda: os.getenv("SUPABASE_USERPASS")
    )

    # --------------------
    # Storage / paths
    # --------------------
    supabase_bucket: str = Field(default_factory=lambda: os.getenv("SUPABASE_BUCKET", "climb-images"))
    data_dir: str = Field(default_factory=lambda: os.getenv("DATA_DIR", "data"))
    image_cache_dir: str = Field(
        default_factory=lambda: os.getenv("IMAGE_CACHE_DIR", "data/render_cache")
    )

    # --------------------
    # CORS
    # --------------------
    cors_origins: list[str] = Field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(",")
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    # Fail fast in prod
    if settings.env == "prod":
        missing = []
        if not settings.public_supabase_url:
            missing.append("PUBLIC_SUPABASE_URL")
        if not settings.supabase_service_role_key:
            missing.append("SUPABASE_SERVICE_ROLE_KEY")

        if missing:
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    return settings
