import tempfile
import unittest
from pathlib import Path

from src.config import CONTEXTS, DEFAULT_COMMENT, DEFAULT_INHERITS
from src.core.project import (
    InvalidThemeError,
    LoadedIcon,
    ProjectNotFoundError,
    ThemeProject,
    create_new_theme_project,
    delete_theme_project,
    load_theme_project,
    save_theme_project,
)


class TestProject(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_new_theme_project_structure(self):
        theme_path = create_new_theme_project("Nordic Dark", self.base_dir)

        self.assertTrue(theme_path.exists())
        self.assertEqual(theme_path.name, "Nordic-Dark")

        # Sprawdzenie obecności podkatalogów scalable/<context>
        for context in CONTEXTS:
            context_dir = theme_path / "scalable" / context
            self.assertTrue(context_dir.is_dir(), f"Brak katalogu {context_dir}")

        # Sprawdzenie pliku index.theme
        index_file = theme_path / "index.theme"
        self.assertTrue(index_file.is_file())
        content = index_file.read_text(encoding="utf-8")
        self.assertIn("[Icon Theme]", content)
        self.assertIn("Name=Nordic Dark", content)
        self.assertIn(f"Inherits={DEFAULT_INHERITS}", content)
        self.assertIn("[scalable/apps]", content)

    def test_create_theme_empty_name_validation(self):
        with self.assertRaises(ValueError):
            create_new_theme_project("", self.base_dir)

        with self.assertRaises(ValueError):
            create_new_theme_project("   ", self.base_dir)

    def test_create_theme_path_traversal_validation(self):
        with self.assertRaises(ValueError):
            create_new_theme_project("../../escape", self.base_dir)

        with self.assertRaises(ValueError):
            create_new_theme_project("nested/theme", self.base_dir)

    def test_load_theme_project_success(self):
        theme_path = create_new_theme_project("Solarized", self.base_dir)

        # Dodajmy przykładowy plik SVG do scalable/apps
        svg_file = theme_path / "scalable" / "apps" / "terminal.svg"
        svg_file.write_text("<svg></svg>", encoding="utf-8")

        project = load_theme_project(theme_path)
        self.assertEqual(project.name, "Solarized")
        self.assertEqual(project.comment, DEFAULT_COMMENT)
        self.assertEqual(len(project.icons), 1)
        self.assertEqual(project.icons[0].context, "apps")
        self.assertEqual(project.icons[0].icon_name, "terminal")
        self.assertEqual(project.icons[0].filepath, svg_file)

    def test_load_theme_project_not_found(self):
        with self.assertRaises(ProjectNotFoundError):
            load_theme_project(self.base_dir / "nonexistent-theme")

    def test_load_theme_project_missing_index_theme(self):
        dummy_dir = self.base_dir / "broken-theme"
        dummy_dir.mkdir()
        with self.assertRaises(InvalidThemeError):
            load_theme_project(dummy_dir)

    def test_delete_theme_project_success(self):
        theme_path = create_new_theme_project("To Delete", self.base_dir)
        self.assertTrue(theme_path.exists())

        deleted = delete_theme_project("To Delete", self.base_dir)
        self.assertEqual(deleted, theme_path)
        self.assertFalse(theme_path.exists())

    def test_delete_theme_project_safety_validation(self):
        with self.assertRaises(ValueError):
            delete_theme_project("", self.base_dir)

        with self.assertRaises(ValueError):
            delete_theme_project("../../system", self.base_dir)

    def test_save_theme_project_and_clean_orphans(self):
        source_svg = self.base_dir / "source.svg"
        source_svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")

        theme_path = self.base_dir / "Custom-Theme"
        project = ThemeProject(
            path=theme_path,
            name="Custom Theme",
            comment="Opis testowy",
            inherits=DEFAULT_INHERITS,
            icons=[
                LoadedIcon(context="apps", icon_name="firefox", filepath=source_svg),
                LoadedIcon(context="places", icon_name="folder", filepath=source_svg),
            ],
        )

        saved_dir, count = save_theme_project(project, update_cache=False)
        self.assertEqual(saved_dir, theme_path)
        self.assertEqual(count, 2)
        self.assertTrue((theme_path / "scalable" / "apps" / "firefox.svg").is_file())
        self.assertTrue((theme_path / "scalable" / "places" / "folder.svg").is_file())

        # Ponowny zapis po usunięciu jednej ikony z listy (test SameFileError + clean_orphans)
        reloaded = load_theme_project(theme_path)
        reloaded.icons = [icon for icon in reloaded.icons if icon.icon_name == "firefox"]

        _, count_after = save_theme_project(reloaded, clean_orphans=True, update_cache=False)
        self.assertEqual(count_after, 1)
        self.assertTrue((theme_path / "scalable" / "apps" / "firefox.svg").is_file())
        self.assertFalse((theme_path / "scalable" / "places" / "folder.svg").exists())


if __name__ == "__main__":
    unittest.main()
