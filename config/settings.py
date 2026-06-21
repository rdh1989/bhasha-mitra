from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    APP_NAME: str = "Bhasha Mitra"

    VERSION: str = "1.0.0"

    HOST: str = "0.0.0.0"

    PORT: int = 8000

settings = Settings()