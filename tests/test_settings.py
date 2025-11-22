from backend.app.core.settings import get_settings


def test_settings_defaults():
    settings = get_settings()
    assert settings.app_name == "CoreBox CRM"
    assert settings.environment == "development"
    assert isinstance(settings.secret_key, str) and settings.secret_key
    assert isinstance(settings.database_url, str) and settings.database_url
