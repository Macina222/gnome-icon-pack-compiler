import configparser
import shutil
from pathlib import Path
from src.config import CONTEXTS, DEFAULT_ICONS_DIR

class ProjectNotFoundError(FileNotFoundError):
    pass

class InvalidThemeError(ValueError):
    pass

def create_new_theme_project(
        name: str,
        output_dir: str | Path = DEFAULT_ICONS_DIR,
        comments: str = "User made Icon Theme, made using GIPC by Macina222",
        inherits: str = "hicolor,Adwaita"

) -> Path:

    base_path = Path(output_dir).expanduser().resolve()
    theme_slug = name.lower().replace(" ", "-")
    theme_dir = base_path / theme_slug

    # Tworzenie podkatalogów
    for context in CONTEXTS:
        (theme_dir / "scalable" / context).mkdir(parents=True, exist_ok=True)

    # Tworzenie pliku konfiguracyjnego

    config = configparser.ConfigParser()
    config.optionxform = str

    directories = [f"scalable/{context}" for context in CONTEXTS]
    config["Icon Theme"] = {
        "Name": name,
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

    # Zapis pliku configuracynjego
    theme_file = theme_dir / "index.theme"
    with open(theme_file, "w", encoding="utf-8") as f:
        config.write(f, space_around_delimiters=False)

    return theme_dir

def delete_theme_project(
    name: str,
    base_dir: str | Path = DEFAULT_ICONS_DIR,
    force: bool = False,
) -> Path:
    base_path = Path(base_dir).expanduser().resolve()
    theme_slug = name.lower().replace(" ", "-")
    theme_dir = base_path / theme_slug

    if not theme_dir.exists():
        raise ProjectNotFoundError(f"Projekt nie istnieje: {theme_dir}")

    if not theme_dir.is_dir():
        raise ProjectNotFoundError(f"Ścieżka nie jest katalogiem: {theme_dir}")

    index_theme = theme_dir / "index.theme"
    if not force and not index_theme.exists():
        raise InvalidThemeError(f"Projekt {theme_dir} nie zawiera pliku 'index.theme'")

    shutil.rmtree(theme_dir)

    return theme_dir