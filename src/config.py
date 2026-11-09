"""Konfiguracja i stałe dla aplikacji"""

from pathlib import Path

# Ścieżki katalogów ikon w systemie
DEFAULT_ICONS_DIR: Path = Path("~/.local/share/icons").expanduser()
SYSTEM_ICONS_DIR: Path = Path("/usr/share/icons")

# Obsługiwane rozszerzenia plików wektorowych
SUPPORTED_EXTENSIONS: tuple[str, ...] = (".svg",)

# Domyślne wartości konfiguracji motywu
DEFAULT_COMMENT: str = "User made Icon Theme, generated using GIPC by Macina222"
DEFAULT_INHERITS: str = "hicolor,Adwaita"

# Wymiary skalowalnych ikon wektorowych
DEFAULT_ICON_SIZE: int = 48
MIN_ICON_SIZE: int = 8
MAX_ICON_SIZE: int = 512

# Słownik kontekstów specyfikacji ikon
# Klucz: nazwa katalogu roboczego
# Wartość: pole Context w pliku index.theme
CONTEXTS: dict[str, str] = {
    "actions": "Actions",
    "apps": "Applications",
    "categories": "Categories",
    "devices": "Devices",
    "mimetypes": "MimeTypes",
    "places": "Places",
    "status": "Status",
    "emblems": "Emblems",
    "ui": "UI",
    }