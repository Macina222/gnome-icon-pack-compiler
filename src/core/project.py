import configparser
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from src.config import (
    CONTEXTS,
    DEFAULT_COMMENT,
    DEFAULT_ICONS_DIR,
    DEFAULT_INHERITS,
)

class ProjectNotFoundError(FileNotFoundError):
    pass

class InvalidThemeError(ValueError):
    pass

@dataclass
class LoadedIcon:
    """Pojedyncza ikona SVG odczytana z istniejącego motywu."""
    context: str
    icon_name: str
    filepath: Path

@dataclass
class ThemeProject:
    """Pełne dane wczytanego projektu motywu ikon."""
    path: Path
    name: str
    comment: str
    inherits: str
    icons: list[LoadedIcon] = field(default_factory=list)

def _resolve_theme_dir(name: str, base_dir: str | Path) -> tuple[Path, Path]:
    """Waliduje nazwę motywu i zwraca bezpieczną ścieżkę bazową oraz katalog motywu."""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Nazwa motywu nie może być pusta.")

    theme_slug = clean_name.replace(" ", "-")
    if "/" in theme_slug or "\\" in theme_slug or ".." in theme_slug:
        raise ValueError(f"Nieprawidłowa nazwa motywu: {name}")

    base_path = Path(base_dir).expanduser().resolve()
    theme_dir = (base_path / theme_slug).resolve()

    if not theme_dir.is_relative_to(base_path) or theme_dir == base_path:
        raise ValueError(f"Ścieżka motywu wykracza poza katalog bazowy: {theme_dir}")

    return base_path, theme_dir

def create_new_theme_project(
    name: str,
    output_dir: str | Path = DEFAULT_ICONS_DIR,
    comments: str = DEFAULT_COMMENT,
    inherits: str = DEFAULT_INHERITS,
) -> Path:
    _, theme_dir = _resolve_theme_dir(name, output_dir)

    # Tworzenie podkatalogów
    for context in CONTEXTS:
        (theme_dir / "scalable" / context).mkdir(parents=True, exist_ok=True)

    # Tworzenie pliku konfiguracyjnego
    config = configparser.ConfigParser()
    config.optionxform = str

    directories = [f"scalable/{context}" for context in CONTEXTS]
    config["Icon Theme"] = {
        "Name": name.strip(),
        "Comment": comments,
        "Inherits": inherits,
        "Directories": ",".join(directories),
    }

    for ctx, context_name in CONTEXTS.items():
        section_name = f"scalable/{ctx}"
        config[section_name] = {
            "Context": context_name,
            "Size": "48",
            "MinSize": "8",
            "MaxSize": "512",
            "Type": "Scalable",
        }

    # Zapis pliku konfiguracyjnego
    theme_file = theme_dir / "index.theme"
    with open(theme_file, "w", encoding="utf-8") as f:
        config.write(f, space_around_delimiters=False)

    return theme_dir

def delete_theme_project(
    name: str,
    base_dir: str | Path = DEFAULT_ICONS_DIR,
    force: bool = False,
) -> Path:
    _, theme_dir = _resolve_theme_dir(name, base_dir)

    if not theme_dir.exists():
        raise ProjectNotFoundError(f"Projekt nie istnieje: {theme_dir}")

    if not theme_dir.is_dir():
        raise ProjectNotFoundError(f"Ścieżka nie jest katalogiem: {theme_dir}")

    index_theme = theme_dir / "index.theme"
    if not force and not index_theme.exists():
        raise InvalidThemeError(f"Projekt {theme_dir} nie zawiera pliku 'index.theme'")

    shutil.rmtree(theme_dir)

    return theme_dir

def load_theme_project(theme_dir: str | Path) -> ThemeProject:
    """Wczytuje istniejący motyw ikon z dysku wraz z listą plików SVG.

    Args:
        theme_dir: Ścieżka do głównego katalogu motywu (zawierającego index.theme).

    Returns:
        ThemeProject: Obiekt z metadanymi motywu oraz listą znalezionych ikon.

    Raises:
        ProjectNotFoundError: Gdy wskazany katalog nie istnieje.
        InvalidThemeError: Gdy brakuje pliku index.theme lub ma on błędną składnię.
    """

    project_dir = Path(theme_dir).expanduser().resolve()

    # Walidacja ścieżki katalogu
    if not project_dir.exists() or not project_dir.is_dir():
        raise ProjectNotFoundError(f"Projekt {theme_dir} nie istnieje")

    index_file = project_dir / "index.theme"
    if not index_file.is_file():
        raise InvalidThemeError(f"Projekt {theme_dir} nie posiada pliku index.theme")

    # Parsowanie pliku index.theme
    config = configparser.ConfigParser()
    config.optionxform = str

    try:
        config.read(index_file, encoding="utf-8")
    except configparser.Error as e:
        raise InvalidThemeError(f"Błąd czytania pliku index.theme: {index_file}: {e}") from e

    if "Icon Theme" not in config:
        raise InvalidThemeError(f"Plik {index_file} nie zawiera sekcji [Icon Theme]")

    theme_section = config["Icon Theme"]
    name = theme_section.get("Name", project_dir.name).strip()
    comment = theme_section.get("Comment", DEFAULT_COMMENT).strip()
    inherits = theme_section.get("Inherits", DEFAULT_INHERITS).strip()

    # Skanowanie katalogów scalable
    loaded_icons: list[LoadedIcon] = []

    for context in CONTEXTS:
        context_dir = project_dir / "scalable" / context
        if not context_dir.is_dir():
            continue

        for svg in sorted(context_dir.glob("*.svg")):
            loaded_icons.append(
                LoadedIcon(
                    context=context,
                    icon_name=svg.stem,
                    filepath=svg,
                )
            )

    return ThemeProject(
        path=project_dir,
        name=name,
        comment=comment,
        inherits=inherits,
        icons=loaded_icons,
    )