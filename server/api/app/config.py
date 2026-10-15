from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./amusnaw.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_days: int = 90
    google_client_ids: str = ""
    apple_client_ids: str = ""
    llm_base_url: str = "http://ollama:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b"
    prompts_dir: str = "/app/prompts"
    data_dir: str = "/app/data"
    content_dir: str = "/app/content"
    # Mot de passe de la page de relecture (/review). Vide = page désactivée.
    review_token: str = ""
    # Connexion de test sans Google/Apple (à laisser à false en production).
    dev_login: bool = False

    @property
    def google_audiences(self) -> list[str]:
        return [x.strip() for x in self.google_client_ids.split(",") if x.strip()]

    @property
    def apple_audiences(self) -> list[str]:
        return [x.strip() for x in self.apple_client_ids.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
