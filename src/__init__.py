# src/__init__.py
# ----------------------------
# Główny pakiet aplikacji "gnome-icon-pack-creator".
#
# Ten plik sprawia, że katalog `src/` staje się oficjalnym pakietem Pythona,
# co umożliwia importowanie modułów z `src.core` i korzystanie z punktu wejścia
# `python -m src` (po skonfigurowaniu pyproject.toml).
#
# Wersja pakietu — aktualizuj przy każdej nowej stabilnej wersji.
# ----------------------------
APP_NAME_SHORT = "GIPC"
APP_NAME_FULL = "GIPC (GNOME Icon Pack Crator)"
APP_ID = "com.github.mzych.gnome-icon-pack-creator"
APP_AUTHOR = "Macina222"
__version__ = "1.0.0"

# Eksportowane funkcje i klasy (opcjonalnie):
# Jeśli potrzebujesz, by `from src import ...` działał bez kwalifikowania,
# umieść tu nazwę interesującego modułu lub klasę.
# np.:  Warning from config import DEFAULT_COMMENT