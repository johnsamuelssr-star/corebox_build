class Settings:
    def __init__(self):
        self.app_name = "CoreBox CRM"
        self.api_version = "1.0.0"
        self.environment = "development"
        self.secret_key = "CHANGE_ME"
        self.SECRET_KEY = self.secret_key
        self.access_token_expire_minutes = 30
        self.ACCESS_TOKEN_EXPIRE_MINUTES = self.access_token_expire_minutes
        self.database_url = "sqlite:///./corebox.db"


_settings_instance = None


def get_settings():
    """Return a singleton Settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
