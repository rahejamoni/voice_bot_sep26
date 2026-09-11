import os
from dataclasses import dataclass


@dataclass
class Settings:
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    google_application_credentials: str = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    default_language: str = os.environ.get("DEFAULT_LANGUAGE", "en-IN")


settings = Settings()
