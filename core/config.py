from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    rapidapi_key: str = ""
    allowed_origins: str = "*"
    firebase_web_api_key: str = ""
    firebase_service_account_path: str = "serviceAccount.json"
    firebase_service_account_json: str = ""  # Cloud deployment için JSON string

    class Config:
        env_file = ".env"

    def __init__(self, **data):
        super().__init__(**data)
        if not self.openai_api_key or not self.openai_api_key.startswith("sk-"):
            raise RuntimeError("Geçerli bir OPENAI_API_KEY tanımlı değil")

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
