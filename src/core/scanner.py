from pathlib import Path
from src.config import CONTEXTS, SYSTEM_ICONS_DIR

def scan_installed_apps() -> set[str]:
    desktop_dirs = [
        Path("/usr/share/applications/"),
        Path("~/.local/share/applications/").expanduser(),
    ]

    icon_names = set()

    for dir in desktop_dirs:
        if not dir.exists():
            continue

        for file in dir.glob("**/*.desktop"):
            try:
                with open(file, "r", encoding="utf_8") as f:
                    for line in f:
                        if line.startswith("Icon="):
                            icon_name = line.split("=")[1].strip()
                            if not icon_name.startswith("/"):
                                icon_names.add(icon_name)
                            break

            except (PermissionError, UnicodeDecodeError) as e:
                continue

    return icon_names

def scan_system_icons(theme_name: str = "Adwaita") -> dict[str, set[str]]:
    theme_dir = SYSTEM_ICONS_DIR / theme_name
    icon_db = {context: set() for context in CONTEXTS if context != "apps"}

    if not theme_dir.exists():
        return icon_db

    for dir in theme_dir.iterdir():
        if not dir.is_dir():
            continue

        for context in icon_db.keys():
            context_dir = dir / context
            if not context_dir.exists():
                continue

            for icon_file in context_dir.glob("**/*.png"):
                icon_name = icon_file.stem
                icon_db[context].add(icon_name)

            for icon_file in context_dir.glob("**/*.svg"):
                icon_name = icon_file.stem
                icon_db[context].add(icon_name)

    return icon_db