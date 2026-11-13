import configparser
import shutil
from pathlib import Path
import src.config
from src import APP_NAME_SHORT

class ProjectNotFoundError(FileNotFoundError):
    pass

class InvalidThemeError(ValueError):
    pass

def create_new_theme_project(
        name: str,
        output_dir: str | Path = src.config.DEFAULT_ICONS_DIR,
        comments: str = f"User made Icon Theme, generated using {APP_NAME_SHORT} by Macina222",
        inherits: str = "hicolor,Adwaita"

) -> Path:

    base_path = Path(output_dir).expanduser().resolve()
    theme_slug = name.lower().replace(" ", "-")
    theme_dir = base_path / theme_slug

    # Tworzenie podkatalogów
    for context in src.config.CONTEXTS:
        (theme_dir / "scalable" / context).mkdir(parents=True, exist_ok=True)

    # Tworzenie pliku konfiguracyjnego

    config = configparser.ConfigParser()
    config.optionxform = str

    directories = [f"scalable/{context}" for context in src.config.CONTEXTS]
    config["Icon Theme"] = {
        "Name": name,
        "Comment": comments,
        "Inherits": inherits,
        "Directories": ",".join(directories),
    }

    for ctx, context_name in src.config.CONTEXTS.items():
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
    base_dir: str | Path = src.config.DEFAULT_ICONS_DIR,
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