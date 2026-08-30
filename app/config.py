from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LI_AT: str = ""
    JSESSIONID: str = ""
    LI_EMAIL: str = ""
    LI_PASSWORD: str = ""
    API_KEYS: str = ""
    CACHE_TTL: int = 1800
    RATE_LIMIT: int = 10

    @property
    def api_keys_list(self) -> list[str]:
        return [key.strip() for key in self.API_KEYS.split(",") if key.strip()]

    @property
    def jsessionid_clean(self) -> str:
        return self.JSESSIONID.strip('"')

    @property
    def has_credentials(self) -> bool:
        return bool(self.LI_EMAIL and self.LI_PASSWORD)

    @property
    def has_cookies(self) -> bool:
        return bool(self.LI_AT and self.JSESSIONID)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
