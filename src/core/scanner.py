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
                with open(file, "r", encoding="utf-8") as f:
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

    for context in icon_db.keys():
        # Znak '*' zastępuje katalog z rozmiarem (np. 'scalable', '48x48')
        # Znak '**' zagląda do wszystkich ewentualnych podkatalogów wewnątrz kontekstu

        for icon_file in theme_dir.glob(f"*/{context}/**/*.png"):
            icon_db[context].add(icon_file.stem)

        for icon_file in theme_dir.glob(f"*/{context}/**/*.svg"):
            icon_db[context].add(icon_file.stem)

    return icon_db

if __name__ == "__main__":
    print(scan_installed_apps())
    print(scan_system_icons())