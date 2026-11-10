from src.config import CONTEXTS
from src.core.scanner import scan_installed_apps, scan_system_icons

class IconDatabase:
    def __init__(self, fallback_theme: str = "Adwaita"):
        self.fallback_theme = fallback_theme
        self._database: dict[str, list[str]] = {ctx: [] for ctx in CONTEXTS}
        self._is_loaded: bool = False

    def build_database(self) -> None:
        app_icons = scan_installed_apps()
        self._database["apps"] = sorted(list(app_icons))

        theme_icons = scan_system_icons(self.fallback_theme)
        for context in CONTEXTS:
            if context == "apps":
                continue

            context_set = theme_icons.get(context, set())

            self._database[context] = sorted(list(context_set))

        self._is_loaded = True

    def load_database(self, context: str) -> list[str]:
        if not self._is_loaded:
            self.build_database()

        if context not in CONTEXTS:
            return []

        return self._database[context]

    def reload_database(self) -> None:
        self._is_loaded = False
        self.build_database()