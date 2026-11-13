import tempfile
import unittest
from pathlib import Path

from src.config import CONTEXTS
from src.core.svg_handler import (
    InvalidContextError,
    InvalidSVGError,
    add_icon_to_theme,
    remove_icon_from_theme,
    validate_svg,
)


class TestSvgHandler(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.temp_dir.name)

        # Tworzenie przykładowego prawidłowego pliku SVG
        self.valid_svg = self.base_path / "valid.svg"
        self.valid_svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48">'
            '<circle cx="24" cy="24" r="20"/>'
            "</svg>",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validate_svg_success(self):
        result = validate_svg(self.valid_svg)
        self.assertEqual(result, self.valid_svg.resolve())

    def test_validate_svg_nonexistent(self):
        with self.assertRaises(FileNotFoundError):
            validate_svg(self.base_path / "does_not_exist.svg")

    def test_validate_svg_unsupported_extension(self):
        png_file = self.base_path / "test.png"
        png_file.write_text("not an svg")
        with self.assertRaises(InvalidSVGError):
            validate_svg(png_file)

    def test_validate_svg_invalid_xml(self):
        broken_file = self.base_path / "broken.svg"
        broken_file.write_text("<svg><unclosed>", encoding="utf-8")
        with self.assertRaises(InvalidSVGError):
            validate_svg(broken_file)

    def test_validate_svg_wrong_root_element(self):
        wrong_root = self.base_path / "wrong.svg"
        wrong_root.write_text("<xml-root></xml-root>", encoding="utf-8")
        with self.assertRaises(InvalidSVGError):
            validate_svg(wrong_root)

    def test_add_icon_to_theme_preserves_case(self):
        project_dir = self.base_path / "test-theme"
        dest = add_icon_to_theme(
            project_dir=project_dir,
            context="apps",
            source_svg=self.valid_svg,
            icon_name="org.gnome.Calculator",
        )
        self.assertTrue(dest.exists())
        self.assertEqual(dest.name, "org.gnome.Calculator.svg")
        self.assertEqual(dest.parent, project_dir / "scalable" / "apps")

    def test_add_icon_to_theme_strips_svg_extension(self):
        project_dir = self.base_path / "test-theme"
        dest = add_icon_to_theme(
            project_dir=project_dir,
            context="apps",
            source_svg=self.valid_svg,
            icon_name="my-app.SVG",
        )
        self.assertEqual(dest.name, "my-app.svg")

    def test_add_icon_to_theme_invalid_context(self):
        project_dir = self.base_path / "test-theme"
        with self.assertRaises(InvalidContextError):
            add_icon_to_theme(
                project_dir=project_dir,
                context="invalid_context_name",
                source_svg=self.valid_svg,
                icon_name="app",
            )

    def test_remove_icon_from_theme(self):
        project_dir = self.base_path / "test-theme"
        dest = add_icon_to_theme(
            project_dir=project_dir,
            context="places",
            source_svg=self.valid_svg,
            icon_name="folder-custom",
        )
        self.assertTrue(dest.exists())

        # Usunięcie ikony
        removed = remove_icon_from_theme(project_dir, "places", "folder-custom")
        self.assertTrue(removed)
        self.assertFalse(dest.exists())

        # Ponowna próba usunięcia zwraca False
        self.assertFalse(remove_icon_from_theme(project_dir, "places", "folder-custom"))


if __name__ == "__main__":
    unittest.main()
