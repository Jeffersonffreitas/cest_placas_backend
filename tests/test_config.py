from app.core.config import Settings


def test_debug_release_env_value_is_treated_as_false() -> None:
    settings = Settings(DEBUG="release")

    assert settings.debug is False
