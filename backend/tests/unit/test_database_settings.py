from app.core.config import Settings


def test_settings_exposes_development_and_test_database_urls() -> None:
    settings = Settings(
        database_url="mysql+asyncmy://app:secret@localhost/homepilot",
        test_database_url="mysql+asyncmy://app:secret@localhost/homepilot_test",
    )

    assert settings.database_url.endswith("/homepilot")
    assert settings.test_database_url.endswith("/homepilot_test")
