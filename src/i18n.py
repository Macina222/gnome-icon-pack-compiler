"""Moduł internacjonalizacji (i18n) dla aplikacji GIPC."""

import json
import locale
import logging
import os
from pathlib import Path

from src import APP_NAME_FULL, APP_NAME_SHORT, __version__

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES: tuple[str, ...] = ("pl", "en")
DEFAULT_CONFIG_DIR: Path = Path("~/.config/gipc").expanduser()
SETTINGS_FILE: Path = DEFAULT_CONFIG_DIR / "settings.json"


def _resolve_locales_dir() -> Path:
    candidates = [
        Path(__file__).resolve().parent / "locales",
        Path(__file__).resolve().parent.parent / "locales",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]


LOCALES_DIR: Path = _resolve_locales_dir()

_DEFAULT_CONTEXT: dict[str, object] = {
    "APP_NAME_SHORT": APP_NAME_SHORT,
    "APP_NAME_FULL": APP_NAME_FULL,
    "VERSION": __version__,
}


def _load_locale_file(lang: str) -> dict[str, str]:
    """Wczytuje słownik tłumaczeń z katalogu locales."""
    locale_path = LOCALES_DIR / f"{lang}.json"
    if not locale_path.is_file():
        # Re-check candidate directory if LOCALES_DIR was resolved before directory creation
        fallback = _resolve_locales_dir() / f"{lang}.json"
        if fallback.is_file():
            locale_path = fallback
        else:
            logger.error(f"Nie znaleziono pliku tłumaczeń: {locale_path}")
            return {}

    try:
        return json.loads(locale_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        logger.error(
            f"Błąd składni JSON w {locale_path} "
            f"(linia {err.lineno}, kolumna {err.colno}): {err.msg}"
        )
        return {}
    except OSError as err:
        logger.error(f"Błąd odczytu pliku {locale_path}: {err}")
        return {}


_TRANSLATIONS: dict[str, dict[str, str]] = {
    lang: _load_locale_file(lang) for lang in SUPPORTED_LANGUAGES
}


def reload_translations() -> None:
    """Przeładowuje słowniki tłumaczeń ze wszystkich plików językowych."""
    global LOCALES_DIR, _TRANSLATIONS
    LOCALES_DIR = _resolve_locales_dir()
    _TRANSLATIONS.clear()
    _TRANSLATIONS.update({lang: _load_locale_file(lang) for lang in SUPPORTED_LANGUAGES})


def detect_system_language() -> str:
    """Wykrywa język systemu operacyjnego ('pl' dla polskiego, 'en' dla pozostałych)."""
    sys_lang = (
        os.environ.get("LANGUAGE")
        or os.environ.get("LC_ALL")
        or os.environ.get("LC_MESSAGES")
        or os.environ.get("LANG")
    )
    if not sys_lang:
        try:
            sys_lang = locale.getlocale()[0]
        except Exception:
            sys_lang = None

    if sys_lang and sys_lang.lower().startswith("pl"):
        return "pl"
    return "en"


def load_saved_language(settings_path: Path = SETTINGS_FILE) -> str:
    """Odczytuje zapisany język z pliku konfiguracyjnego lub wykrywa go z systemu."""
    if settings_path.is_file():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            saved = data.get("language")
            if saved in SUPPORTED_LANGUAGES:
                return saved
        except (json.JSONDecodeError, OSError) as err:
            logger.warning(f"Błąd odczytu ustawień języka z {settings_path}: {err}")
    return detect_system_language()


def save_language(lang: str, settings_path: Path = SETTINGS_FILE) -> None:
    """Zapisuje wybrany kod języka w pliku konfiguracyjnym użytkownika."""
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        existing: dict[str, object] = {}
        if settings_path.is_file():
            try:
                existing = json.loads(settings_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = {}
        existing["language"] = lang
        settings_path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as err:
        logger.warning(f"Nie udało się zapisać ustawień języka w {settings_path}: {err}")


_current_language: str = load_saved_language()
os.environ["LANGUAGE"] = _current_language


def get_language() -> str:
    """Zwraca kod aktualnie aktywnego języka ('pl' lub 'en')."""
    return _current_language


def set_language(lang: str, persist: bool = True) -> str:
    """Ustawia aktywny język aplikacji i opcjonalnie zapisuje wybór na dysku."""
    global _current_language
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Nieobsługiwany język: {lang}. Dostępne: {SUPPORTED_LANGUAGES}")

    _current_language = lang
    os.environ["LANGUAGE"] = lang
    if persist:
        save_language(lang)
    logger.debug(f"language_changed: {lang}")
    return _current_language


def t(key: str, **kwargs: object) -> str:
    """Zwraca przetłumaczony tekst z automatycznym podstawieniem stałych aplikacji."""
    if not _TRANSLATIONS.get("pl") and not _TRANSLATIONS.get("en"):
        reload_translations()

    lang_dict = _TRANSLATIONS.get(_current_language, {})
    template = lang_dict.get(key) or _TRANSLATIONS.get("en", {}).get(key) or key
    context = {**_DEFAULT_CONTEXT, **kwargs}
    try:
        return template.format(**context)
    except (KeyError, ValueError, IndexError) as err:
        logger.warning(f"Błąd formatowania w tłumaczeniu '{key}': {err}")
        return template