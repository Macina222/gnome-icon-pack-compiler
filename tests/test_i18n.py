import os
import re
import tempfile
import unittest
from pathlib import Path

from src.i18n import (
    _DEFAULT_CONTEXT,
    _TRANSLATIONS,
    detect_system_language,
    get_language,
    load_saved_language,
    save_language,
    set_language,
    t,
)


class TestI18n(unittest.TestCase):
    def test_locales_have_identical_keys(self):
        pl_keys = set(_TRANSLATIONS["pl"].keys())
        en_keys = set(_TRANSLATIONS["en"].keys())
        self.assertGreater(len(pl_keys), 0)
        self.assertEqual(pl_keys, en_keys, f"Różnica w kluczach: {pl_keys ^ en_keys}")

    def test_all_ui_keys_exist_in_translations(self):
        main_window_path = Path(__file__).resolve().parent.parent / "src" / "ui" / "main_window.py"
        code = main_window_path.read_text(encoding="utf-8")
        used_keys = set(re.findall(r"""\bt\(\s*["\x27]([a-zA-Z0-9_.]+)["\x27]""", code))
        self.assertGreater(len(used_keys), 0)

        missing_pl = used_keys - set(_TRANSLATIONS["pl"].keys())
        missing_en = used_keys - set(_TRANSLATIONS["en"].keys())
        self.assertFalse(missing_pl, f"Klucze użyte w UI brakujące w pl.json: {missing_pl}")
        self.assertFalse(missing_en, f"Klucze użyte w UI brakujące w en.json: {missing_en}")

    def test_placeholders_match_and_render_cleanly(self):
        placeholder_re = re.compile(r"\{([a-zA-Z0-9_]+)\}")
        dummy_dynamic_vars = {
            "filepath": "/tmp/test.svg",
            "err": "Sample error",
            "files": "a.svg",
            "duplicates": "apps/firefox",
            "name": "Nordic",
            "count": 3,
            "path": "/home/user/.local/share/icons/Nordic",
        }

        for key, pl_val in _TRANSLATIONS["pl"].items():
            en_val = _TRANSLATIONS["en"][key]
            pl_vars = set(placeholder_re.findall(pl_val))
            en_vars = set(placeholder_re.findall(en_val))
            self.assertEqual(
                pl_vars,
                en_vars,
                f"Niezgodne zmienne formatowania dla klucza '{key}': {pl_vars} vs {en_vars}",
            )
            # Weryfikacja, że wszystkie placeholdery (w tym APP_NAME_FULL / APP_NAME_SHORT / VERSION) istnieją
            available = {**_DEFAULT_CONTEXT, **dummy_dynamic_vars}
            missing = pl_vars - set(available.keys())
            self.assertFalse(missing, f"Nieznane zmienne {missing} w kluczu '{key}'")

    def test_language_switch_and_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_file = Path(tmp) / "settings.json"
            save_language("en", settings_path=settings_file)
            self.assertEqual(load_saved_language(settings_path=settings_file), "en")

            set_language("en", persist=False)
            self.assertEqual(get_language(), "en")
            self.assertEqual(t("header.build.label"), "Build theme")
            self.assertIn("GIPC", t("scan.title"))

            set_language("pl", persist=False)
            self.assertEqual(get_language(), "pl")
            self.assertEqual(t("header.build.label"), "Zbuduj motyw")

    def test_unsupported_language_raises_error(self):
        with self.assertRaises(ValueError):
            set_language("de", persist=False)

    def test_fallback_for_missing_key(self):
        missing_key = "non.existent.key.xyz"
        self.assertEqual(t(missing_key), missing_key)

    def test_detect_system_language(self):
        orig_lang = os.environ.get("LANGUAGE")
        try:
            os.environ["LANGUAGE"] = "pl_PL.UTF-8"
            self.assertEqual(detect_system_language(), "pl")
            os.environ["LANGUAGE"] = "en_US.UTF-8"
            self.assertEqual(detect_system_language(), "en")
        finally:
            if orig_lang is not None:
                os.environ["LANGUAGE"] = orig_lang
            else:
                os.environ.pop("LANGUAGE", None)


if __name__ == "__main__":
    unittest.main()