from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = "TerraLuna AI API"
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    app_env: str = os.getenv("APP_ENV", "development")
    data_mode: str = os.getenv("DATA_MODE", "demo_fixture")
    methodology_version: str = os.getenv("METHODOLOGY_VERSION", "terrain-v2.0")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    )


settings = Settings()

