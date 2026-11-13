import logging
from pathlib import Path
from src.config import CONTEXTS, SYSTEM_ICONS_DIR

logger = logging.getLogger(__name__)

def scan_installed_apps(desktop_dirs: list[Path] | None = None) -> set[str]:
    logger.debug("scan_installed_apps_start")
    if desktop_dirs is None:
        desktop_dirs = [
            Path("/usr/share/applications/"),
            Path("~/.local/share/applications/").expanduser(),
        ]

    icon_names = set()

    for dir in desktop_dirs:
        if not dir.exists():
            logger.debug(f"scan_installed_apps_dir_not_found: {dir}")
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
                logger.warning(f"scan_installed_apps_error: {file} -> {e}")
                continue

    logger.debug(f"scan_installed_apps_done: found={len(icon_names)}")
    return icon_names

def scan_system_icons(theme_name: str = "Adwaita", base_icons_dir: Path = SYSTEM_ICONS_DIR) -> dict[str, set[str]]:
    logger.debug(f"scan_system_icons_start: theme={theme_name}")
    theme_dir = base_icons_dir / theme_name
    icon_db = {context: set() for context in CONTEXTS if context != "apps"}

    if not theme_dir.exists():
        logger.warning(f"scan_system_icons_theme_not_found: {theme_dir}")
        return icon_db

    for context in icon_db.keys():
        # Znak '*' zastępuje katalog z rozmiarem (np. 'scalable', '48x48')
        # Znak '**' zagląda do wszystkich ewentualnych podkatalogów wewnątrz kontekstu

        for icon_file in theme_dir.glob(f"*/{context}/**/*.png"):
            icon_db[context].add(icon_file.stem)

        for icon_file in theme_dir.glob(f"*/{context}/**/*.svg"):
            icon_db[context].add(icon_file.stem)

    logger.debug(f"scan_system_icons_done: theme={theme_name}")
    return icon_db

if __name__ == "__main__":
    print(scan_installed_apps())
    print(scan_system_icons())