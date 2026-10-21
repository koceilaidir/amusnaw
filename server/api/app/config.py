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
    # Modèle spécialisé pour « Corrige… » (ex. amusnaw-v1). Vide = le modèle principal.
    llm_model_correct: str = ""
    prompts_dir: str = "/app/prompts"
    data_dir: str = "/app/data"
    content_dir: str = "/app/content"
    # Mot de passe de la page de relecture (/review). Vide = page désactivée.
    review_token: str = ""
    # Connexion de test sans Google/Apple (à laisser à false en production).
    dev_login: bool = False
    # Adresse de contact affichée dans la politique de confidentialité (/privacy)
    contact_email: str = ""
    # Citer les ouvrages et bases d'origine dans les réponses (désactivé sur le site public)
    show_sources: bool = False
    # Connexion par e-mail (code à 6 chiffres envoyé par Brevo)
    brevo_api_key: str = ""
    mail_from: str = ""            # ex. bonjour@amusnaw.dz (domaine validé chez Brevo)
    mail_from_name: str = "Amusnaw"
    # Moteur de traduction NLLB (service « mt » de docker-compose). Vide = désactivé.
    mt_url: str = "http://mt:8100"

    @property
    def google_audiences(self) -> list[str]:
        return [x.strip() for x in self.google_client_ids.split(",") if x.strip()]

    @property
    def apple_audiences(self) -> list[str]:
        return [x.strip() for x in self.apple_client_ids.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
