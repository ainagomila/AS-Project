from functools import lru_cache
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: SecretStr  # no default -> required


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Instantiate eagerly so a missing key crashes the app at startup,
# not on the first request.
settings = get_settings()
