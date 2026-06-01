from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 환경 변수명만 명시 (OS 환경변수나 .env에서 읽음)
    GEMINI_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()