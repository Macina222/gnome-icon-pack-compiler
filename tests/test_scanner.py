import tempfile
import unittest
from pathlib import Path

from src.core.scanner import scan_installed_apps, scan_system_icons


class TestScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_installed_apps_mocked(self):
        app_dir = self.base_path / "applications"
        app_dir.mkdir()

        # Plik 1: Standardowa ikona
        desktop1 = app_dir / "app1.desktop"
        desktop1.write_text(
            "[Desktop Entry]\n"
            "Name=Calculator\n"
            "Exec=calc\n"
            "Icon=org.gnome.Calculator\n"
            "Type=Application\n",
            encoding="utf-8",
        )

        # Plik 2: Ikona z bezwzględną ścieżką (pomijana zgodnie ze specyfikacją)
        desktop2 = app_dir / "app2.desktop"
        desktop2.write_text(
            "[Desktop Entry]\n"
            "Name=App 2\n"
            "Icon=/opt/app/icon.png\n",
            encoding="utf-8",
        )

        # Plik 3: Brak linii Icon
        desktop3 = app_dir / "app3.desktop"
        desktop3.write_text(
            "[Desktop Entry]\n"
            "Name=App 3\n",
            encoding="utf-8",
        )

        result = scan_installed_apps(desktop_dirs=[app_dir])
        self.assertIn("org.gnome.Calculator", result)
        self.assertNotIn("/opt/app/icon.png", result)
        self.assertEqual(len(result), 1)

    def test_scan_system_icons_mocked(self):
        theme_dir = self.base_path / "CustomTheme"
        (theme_dir / "scalable" / "places").mkdir(parents=True)
        (theme_dir / "48x48" / "status").mkdir(parents=True)

        (theme_dir / "scalable" / "places" / "folder-documents.svg").write_text("<svg/>")
        (theme_dir / "48x48" / "status" / "battery-full.png").write_text("png")

        icons = scan_system_icons("CustomTheme", base_icons_dir=self.base_path)
        self.assertIn("folder-documents", icons["places"])
        self.assertIn("battery-full", icons["status"])
        self.assertNotIn("apps", icons)

    def test_scan_system_icons_nonexistent(self):
        icons = scan_system_icons("NonExistentTheme", base_icons_dir=self.base_path)
        self.assertIsInstance(icons, dict)
        self.assertNotIn("apps", icons)
        self.assertEqual(icons["places"], set())


if __name__ == "__main__":
    unittest.main()
