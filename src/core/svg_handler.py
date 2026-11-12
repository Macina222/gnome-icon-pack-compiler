import shutil
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from src.config import CONTEXTS, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

class InvalidSVGError(ValueError):
    pass

class InvalidContextError(ValueError):
    pass

def validate_svg(filepath: str | Path) -> Path:
    logger.debug(f"validate_svg: filepath={filepath}")
    path = Path(filepath).expanduser().resolve()

    if not path.exists() or not path.is_file():
        logger.warning(f"validate_svg: file_not_found: {filepath}")
        raise FileNotFoundError(f"Plik nie istnieje")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        logger.warning(f"validate_svg: unsupported_extension: {path.suffix}")
        raise InvalidSVGError(f"Nieobsługiwane rozszerzenie pliku {path.suffix}")

    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
    except ET.ParseError as e:
        logger.warning(f"validate_svg: invalid_xml: {path.name} -> {e}")
        raise InvalidSVGError(f"Nieprawidłowa składnia XML w pliku {path.name}: {e}") from e

    tag_name = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    if tag_name.lower() != "svg":
        logger.warning(f"validate_svg: wrong_root_element: {path.name} -> <{tag_name}>")
        raise InvalidSVGError(
            f"Główny znacznik pliku {path.name} to '<{tag_name}>', oczekiwano '<svg>'."
        )

    # KLUCZOWE: bez tego `add_icon_to_theme` otrzyma None i wywoła TypeError w `shutil.copy2`.
    # Funkcja deklaruje `-> Path`, więc zawsze zwracamy poprawną ścieżkę po pomyślnym walidacji.
    return path

def add_icon_to_theme(
    project_dir: str | Path,
    context: str,
    source_svg: str | Path,
    icon_name: str,
) -> Path:

    if context not in CONTEXTS:
        logger.warning(f"add_icon_to_theme: invalid_context: {context}")
        raise InvalidContextError(
            f"Nieznany kontekst '{context}'. Dostępne: {', '.join(CONTEXTS.keys())}"
        )

    logger.debug(f"add_icon_to_theme: context={context} source={source_svg} name={icon_name}")
    svg = validate_svg(source_svg)
    target_dir = Path(project_dir) / "scalable" / context
    target_dir.mkdir(parents=True, exist_ok=True)

    clean_name = icon_name.strip().lower()
    if clean_name.endswith(".svg"):
        clean_name = clean_name[:-4]

    dest_path = target_dir / f"{clean_name}.svg"
    shutil.copy2(svg, dest_path)

    return dest_path

def remove_icon_from_theme(
    project_dir: str | Path,
    context: str,
    icon_name: str,
) -> bool:

    if context not in CONTEXTS:
        logger.warning(f"remove_icon_from_theme: invalid_context: {context}")
        raise InvalidContextError(
            f"Nieznany kontekst: {context}"
        )

    clean_name = icon_name.strip().lower()
    if clean_name.endswith(".svg"):
        clean_name = clean_name[:-4]

    target = Path(project_dir) / "scalable" / context / f"{clean_name}.svg"

    if target.exists() and target.is_file():
        target.unlink()
        return True

    return False