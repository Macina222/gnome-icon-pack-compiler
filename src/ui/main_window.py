import sys
import logging
import threading
from pathlib import Path
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src import __version__, APP_NAME_FULL, APP_AUTHOR, APP_ID, APP_NAME_SHORT
from src.core.svg_handler import InvalidSVGError, validate_svg
from src.config import (
    CONTEXTS,
    DEFAULT_COMMENT,
    DEFAULT_ICONS_DIR,
    DEFAULT_INHERITS,
)
from src.core.project import (
    InvalidThemeError,
    LoadedIcon,
    ProjectNotFoundError,
    ThemeProject,
    load_theme_project,
    save_theme_project,
)
from src.core.icon_database import IconDatabase
from src.i18n import get_language, set_language, t

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class IconRow(Gtk.ListBoxRow):
    """Reprezentuje wiersz mapowania: Ikona systemowa -> Nowa ikona SVG."""

    def __init__(
        self,
        filepath: str,
        suggestions_map: dict[str, list[str]],
        initial_context: str | None = None,
        initial_name: str | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.filepath = str(filepath)
        self.filename = Path(filepath).name
        self.suggestions_map = suggestions_map
        self._pending_initial_name = initial_name

        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row_box.set_margin_top(8)
        row_box.set_margin_bottom(8)
        row_box.set_margin_start(10)
        row_box.set_margin_end(10)

        # --- LEWA STRONA: IKONA SYSTEMOWA (CEL) ---
        # 1. Wybór kontekstu (apps, status, places...)
        context_keys = list(self.suggestions_map.keys())
        self.context_dropdown = Gtk.DropDown(model=Gtk.StringList.new(context_keys))
        self.context_dropdown.set_valign(Gtk.Align.CENTER)
        self.context_dropdown.connect("notify::selected-item", self.on_context_changed)
        row_box.append(self.context_dropdown)

        # 2. Wyszukiwalny dropdown nazwy ikony systemowej
        expression = Gtk.PropertyExpression.new(Gtk.StringObject, None, "string")
        self.name_dropdown = Gtk.DropDown()
        self.name_dropdown.set_expression(expression)
        self.name_dropdown.set_hexpand(True)
        self.name_dropdown.set_enable_search(True)
        self.name_dropdown.set_valign(Gtk.Align.CENTER)
        self.name_dropdown.connect("notify::selected-item", self.on_name_changed)
        row_box.append(self.name_dropdown)

        # 3. Miniatura obecnej ikony z systemu
        self.target_preview = Gtk.Image.new_from_icon_name("image-missing")
        self.target_preview.set_pixel_size(48)
        row_box.append(self.target_preview)

        # --- ŚRODEK: STRZAŁKA ZASTĄPIENIA ---
        arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
        arrow.add_css_class("dim-label")
        row_box.append(arrow)

        # --- PRAWA STRONA: NOWA IKONA (Z PLIKU SVG) ---
        # 4. Miniatura nowego pliku SVG z dysku
        self.input_preview = Gtk.Image.new_from_file(self.filepath)
        self.input_preview.set_pixel_size(48)
        row_box.append(self.input_preview)

        # 5. Nazwa dodanego pliku SVG
        self.filename_label = Gtk.Label(
            label=f"<b>{GLib.markup_escape_text(self.filename)}</b>",
            use_markup=True,
        )
        self.filename_label.set_halign(Gtk.Align.START)
        self.filename_label.set_width_chars(18)
        self.filename_label.set_max_width_chars(18)
        self.filename_label.set_ellipsize(3)  # Pango.EllipsizeMode.END
        row_box.append(self.filename_label)

        # 6. Przycisk usuwania wiersza
        self.btn_remove = Gtk.Button(icon_name="user-trash-symbolic")
        self.btn_remove.add_css_class("destructive-action")
        self.btn_remove.add_css_class("flat")
        self.btn_remove.set_valign(Gtk.Align.CENTER)
        row_box.append(self.btn_remove)

        self.set_child(row_box)
        self.retranslate()

        # Inicjalizacja kontekstu (wczytanego z projektu lub domyślnego pierwszego)
        logger.debug(
            f"IconRow init filepath={filepath} initial_context={initial_context} "
            f"initial_name={initial_name} contexts={context_keys}"
        )
        if initial_context and initial_context in context_keys:
            context_idx = context_keys.index(initial_context)
            if context_idx == 0:
                # Indeks 0 jest już wybrany domyślnie przez GTK4 — sygnał nie zostanie wyemitowany
                self.on_context_changed(self.context_dropdown, None)
            else:
                self.context_dropdown.set_selected(context_idx)
        else:
            self.on_context_changed(self.context_dropdown, None)

    def retranslate(self) -> None:
        """Aktualizuje podpowiedzi wiersza po zmianie języka."""
        self.context_dropdown.set_tooltip_text(t("row.context.tooltip"))
        self.name_dropdown.set_tooltip_text(t("row.name.tooltip"))
        self.target_preview.set_tooltip_text(t("row.target_preview.tooltip"))
        self.input_preview.set_tooltip_text(t("row.input_preview.tooltip"))
        self.filename_label.set_tooltip_text(t("row.filename.tooltip", filepath=self.filepath))
        self.btn_remove.set_tooltip_text(t("row.remove.tooltip"))

    @classmethod
    def from_loaded_icon(
        cls,
        icon: LoadedIcon,
        suggestions_map: dict[str, list[str]],
    ) -> "IconRow":
        """Tworzy wiersz GUI bezpośrednio z obiektu domenowego LoadedIcon."""
        return cls(
            filepath=str(icon.filepath),
            suggestions_map=suggestions_map,
            initial_context=icon.context,
            initial_name=icon.icon_name,
        )

    def to_loaded_icon(self) -> LoadedIcon:
        """Serializuje aktualny stan widżetów wiersza do obiektu LoadedIcon."""
        return LoadedIcon(
            context=self.get_selected_context(),
            icon_name=self.get_selected_name(),
            filepath=Path(self.filepath),
        )

    def update_suggestions_map(self, suggestions_map: dict[str, list[str]]) -> None:
        """Odświeża listy podpowiedzi (np. po zakończeniu skanowania w tle) z zachowaniem wyboru."""
        current_context = self.get_selected_context()
        current_name = self.get_selected_name()

        self.suggestions_map = suggestions_map
        self._pending_initial_name = current_name or None

        context_keys = list(self.suggestions_map.keys())
        self.context_dropdown.set_model(Gtk.StringList.new(context_keys))

        if current_context and current_context in context_keys:
            context_idx = context_keys.index(current_context)
            if context_idx == 0:
                self.on_context_changed(self.context_dropdown, None)
            else:
                self.context_dropdown.set_selected(context_idx)
        else:
            self.on_context_changed(self.context_dropdown, None)

    def on_context_changed(self, dropdown: Gtk.DropDown, pspec) -> None:
        """Podmienia model podpowiedzi po zmianie kontekstu i zaznacza docelową nazwę."""
        selected_item = dropdown.get_selected_item()
        if not selected_item:
            return

        context = selected_item.get_string()
        new_suggestions = list(self.suggestions_map.get(context, []))

        target_name = self._pending_initial_name
        self._pending_initial_name = None

        if target_name and target_name not in new_suggestions:
            new_suggestions.insert(0, target_name)

        logger.debug(
            f"IconRow context changed: {context} suggestions_count={len(new_suggestions)} "
            f"target_name={target_name}"
        )
        self.name_dropdown.set_model(Gtk.StringList.new(new_suggestions))

        if target_name and target_name in new_suggestions:
            name_idx = new_suggestions.index(target_name)
            if name_idx != 0:
                self.name_dropdown.set_selected(name_idx)
            else:
                self.on_name_changed(self.name_dropdown, None)
        else:
            self.on_name_changed(self.name_dropdown, None)

    def on_name_changed(self, dropdown: Gtk.DropDown, pspec) -> None:
        """Odświeża miniaturę ikony systemowej na podstawie wybranej nazwy."""
        selected_item = dropdown.get_selected_item()
        if selected_item:
            icon_name = selected_item.get_string()
            logger.debug(f"IconRow name changed: {icon_name}")
            self.target_preview.set_from_icon_name(icon_name)
        else:
            logger.debug("IconRow name changed: none")
            self.target_preview.set_from_icon_name("image-missing")

    def get_selected_context(self) -> str:
        item = self.context_dropdown.get_selected_item()
        return item.get_string() if item else ""

    def get_selected_name(self) -> str:
        item = self.name_dropdown.get_selected_item()
        return item.get_string() if item else ""


class MainWindow(Gtk.ApplicationWindow):
    """Klasa głównego okna aplikacji"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.set_default_size(1200, 800)
        self.set_resizable(True)

        self.icon_db: IconDatabase | None = None
        self.suggestions_map: dict[str, list[str]] = {ctx: [] for ctx in CONTEXTS}
        self._scanning_dialog: Gtk.Window | None = None
        self._ui_ready: bool = False

        self._setup_header_bar()
        self._setup_layout()

        self._ui_ready = True
        self.retranslate()

        # Wyświetlamy modalne okienko oczekiwania i uruchamiamy skaner w tle
        self._show_scanning_dialog()
        self._start_database_load_thread()

    def _show_scanning_dialog(self) -> None:
        """Tworzy i wyświetla okno skanera ikon"""
        dialog = Gtk.Window(
            transient_for=self,
            modal=True,
            resizable=False,
            deletable=False,
        )
        dialog.set_title(t("scan.title"))
        dialog.set_default_size(320, 120)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(32)
        box.set_margin_end(32)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        spinner = Gtk.Spinner()
        spinner.set_size_request(32, 32)
        spinner.start()
        box.append(spinner)

        label = Gtk.Label(label=f"<b>{GLib.markup_escape_text(t('scan.heading'))}</b>",
                          use_markup=True)
        box.append(label)

        sub_label = Gtk.Label(label=t("scan.sublabel"))
        sub_label.add_css_class("dim-label")
        box.append(sub_label)

        dialog.set_child(box)
        self._scanning_dialog = dialog
        dialog.present()

    def _close_scanning_dialog(self) -> None:
        """Bezpiecznie zamyka okno skanowania, jeśli jest otwarte"""
        if self._scanning_dialog is not None:
            self._scanning_dialog.destroy()
            self._scanning_dialog = None

    def _start_database_load_thread(self) -> None:
        """Uruchamia wątek pracujący w tle, zapobiegając zamrożeniu okna (freezing)."""
        thread = threading.Thread(target=self._load_database_worker, daemon=True)
        thread.start()

    def _load_database_worker(self) -> None:
        """Praca wykonywana w tle (POZA głównym wątkiem GTK)."""
        logger.debug("thread_database_scan_begin")
        try:
            icon_db = IconDatabase(fallback_theme="Adwaita")
            icon_db.build_database()
            new_map = {ctx: icon_db.get_suggestions(ctx) for ctx in CONTEXTS}
        except Exception as err:
            logger.exception(f"thread_database_scan_failed: {err}")
            GLib.idle_add(self._on_database_load_failed, str(err))
            return

        GLib.idle_add(self._on_database_loaded, icon_db, new_map)

    def _on_database_loaded(self, icon_db: IconDatabase, new_map: dict[str, list[str]]) -> bool:
        """Odbiera dane z wątku i aktualizuje interfejs (WYKONYWANE W GŁÓWNYM WĄTKU)."""
        self.icon_db = icon_db
        self.suggestions_map = new_map

        row = self.icons_listbox.get_first_child()
        while row is not None:
            if isinstance(row, IconRow):
                row.update_suggestions_map(new_map)
            row = row.get_next_sibling()

        self._close_scanning_dialog()
        logger.debug("thread_database_scan_success")
        return GLib.SOURCE_REMOVE

    def _on_database_load_failed(self, error: str) -> bool:
        """Zamyka okno oczekiwania w razie awarii skanera, aby nie zablokować aplikacji."""
        self._close_scanning_dialog()
        logger.error(f"Nie udało się zbudować bazy ikon: {error}")
        return GLib.SOURCE_REMOVE

    def _setup_header_bar(self) -> None:
        """Tworzy natywny pasek tytułowy GNOME"""
        header_bar = Gtk.HeaderBar()
        self.set_titlebar(header_bar)

        self.about_btn = Gtk.Button(icon_name="dialog-information-symbolic")
        self.about_btn.add_css_class("flat")
        self.about_btn.connect("clicked", self.on_about_clicked)
        header_bar.pack_start(self.about_btn)

        # Przełącznik języka PL | EN
        self.lang_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.lang_box.add_css_class("linked")

        self.btn_lang_pl = Gtk.ToggleButton(label="PL")
        self.btn_lang_en = Gtk.ToggleButton(label="EN")
        self.btn_lang_en.set_group(self.btn_lang_pl)

        current_lang = get_language()
        self.btn_lang_pl.set_active(current_lang == "pl")
        self.btn_lang_en.set_active(current_lang == "en")

        self.btn_lang_pl.connect("toggled", self._on_language_toggled, "pl")
        self.btn_lang_en.connect("toggled", self._on_language_toggled, "en")

        self.lang_box.append(self.btn_lang_pl)
        self.lang_box.append(self.btn_lang_en)
        header_bar.pack_start(self.lang_box)

        self.build_btn = Gtk.Button()
        self.build_btn.add_css_class("suggested-action")
        self.build_btn.connect("clicked", self.on_button_clicked)
        header_bar.pack_end(self.build_btn)

    def _setup_layout(self) -> None:
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        self.set_child(main_box)

        # 1. LEWY PANEL (Ustawienia motywu)
        left_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        left_panel.set_size_request(300, -1)

        # Przyciski zarządzania projektem
        project_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.btn_new_theme = Gtk.Button()
        self.btn_new_theme.set_hexpand(True)
        self.btn_new_theme.connect("clicked", self.on_new_theme_clicked)

        self.btn_load_theme = Gtk.Button()
        self.btn_load_theme.set_hexpand(True)
        self.btn_load_theme.connect("clicked", self.on_load_theme_clicked)

        project_actions_box.append(self.btn_new_theme)
        project_actions_box.append(self.btn_load_theme)
        left_panel.append(project_actions_box)

        self.settings_title = Gtk.Label(use_markup=True)
        self.settings_title.set_halign(Gtk.Align.START)
        left_panel.append(self.settings_title)

        # Pola formularza
        self.name_label = Gtk.Label(halign=Gtk.Align.START)
        self.theme_name_entry = Gtk.Entry()

        self.comment_label = Gtk.Label(halign=Gtk.Align.START)
        self.theme_comment_entry = Gtk.Entry()

        left_panel.append(self.name_label)
        left_panel.append(self.theme_name_entry)
        left_panel.append(self.comment_label)
        left_panel.append(self.theme_comment_entry)

        main_box.append(left_panel)

        # Separator wizualny
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(separator)

        # 2. PRAWY PANEL (Lista ikon)
        right_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right_panel.set_hexpand(True)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.icons_title = Gtk.Label(use_markup=True)
        self.icons_title.set_hexpand(True)
        self.icons_title.set_halign(Gtk.Align.START)

        self.add_icon_btn = Gtk.Button()
        self.add_icon_btn.connect("clicked", self.on_add_svg_clicked)

        header_box.append(self.icons_title)
        header_box.append(self.add_icon_btn)
        right_panel.append(header_box)

        # Scrollowana lista dodanych ikon
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.icons_listbox = Gtk.ListBox()
        self.icons_listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        self.placeholder_label = Gtk.Label()
        self.placeholder_label.set_justify(Gtk.Justification.CENTER)
        self.placeholder_label.add_css_class("dim-label")
        self.icons_listbox.set_placeholder(self.placeholder_label)

        scrolled_window.set_child(self.icons_listbox)
        right_panel.append(scrolled_window)
        main_box.append(right_panel)

    def _on_language_toggled(self, button: Gtk.ToggleButton, lang: str) -> None:
        """Reaguje na przełączenie języka w pasku górnym i odświeża całe UI."""
        if not button.get_active():
            GLib.idle_add(self._ensure_one_language_active)
            return
        if not self._ui_ready or get_language() == lang:
            return
        set_language(lang)
        self.retranslate()

    def _ensure_one_language_active(self) -> bool:
        """Zapobiega odznaczeniu obu przycisków języka w grupie."""
        if not self.btn_lang_pl.get_active() and not self.btn_lang_en.get_active():
            if get_language() == "pl":
                self.btn_lang_pl.set_active(True)
            else:
                self.btn_lang_en.set_active(True)
        return GLib.SOURCE_REMOVE

    def retranslate(self) -> None:
        """Aktualizuje wszystkie etykiety, placeholdery i podpowiedzi po zmianie języka."""
        self.set_title(t("window.title"))
        self.about_btn.set_tooltip_text(t("header.about.tooltip"))
        self.lang_box.set_tooltip_text(t("header.lang.tooltip"))
        self.build_btn.set_label(t("header.build.label"))
        self.build_btn.set_tooltip_text(t("header.build.tooltip"))

        self.btn_new_theme.set_label(t("project.new.label"))
        self.btn_new_theme.set_tooltip_text(t("project.new.tooltip"))
        self.btn_load_theme.set_label(t("project.load.label"))
        self.btn_load_theme.set_tooltip_text(t("project.load.tooltip"))

        self.settings_title.set_markup(
            f"<b>{GLib.markup_escape_text(t('settings.title'))}</b>"
        )
        self.name_label.set_text(t("settings.name.label"))
        self.theme_name_entry.set_placeholder_text(t("settings.name.placeholder"))
        self.theme_name_entry.set_tooltip_text(t("settings.name.tooltip"))

        self.comment_label.set_text(t("settings.comment.label"))
        self.theme_comment_entry.set_placeholder_text(t("settings.comment.placeholder"))
        self.theme_comment_entry.set_tooltip_text(t("settings.comment.tooltip"))

        self.icons_title.set_markup(
            f"<b>{GLib.markup_escape_text(t('icons.title'))}</b>"
        )
        self.add_icon_btn.set_label(t("icons.add.label"))
        self.add_icon_btn.set_tooltip_text(t("icons.add.tooltip"))
        self.placeholder_label.set_text(t("icons.placeholder"))

        row = self.icons_listbox.get_first_child()
        while row is not None:
            if isinstance(row, IconRow):
                row.retranslate()
            row = row.get_next_sibling()

        # --- Obsługa zdarzeń ---

    def on_new_theme_clicked(self, button: Gtk.Button) -> None:
        print("cleanup_new_theme_clicked")
        logger.debug("cleanup_new_theme_clicked")
        self.theme_name_entry.set_text("")
        self.theme_comment_entry.set_text("")
        self._clear_icons_list()

    def _clear_icons_list(self):
        """Usuwa wszystkie wiersze ikon po prawej stronie"""
        while (child := self.icons_listbox.get_first_child()) is not None:
            self.icons_listbox.remove(child)

    def on_load_theme_clicked(self, button: Gtk.Button) -> None:
        logger.debug("file_manager_load_theme_clicked")
        dialog = Gtk.FileDialog()
        dialog.set_title(t("dialog.load.title"))
        dialog.set_initial_folder(Gio.File.new_for_path(str(DEFAULT_ICONS_DIR)))
        dialog.select_folder(self, None, self._on_theme_folder_selected)

    def _on_theme_folder_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        """Otwiera wybrany folder i ładuje projekt do interfejsu"""
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return # Anulowanie wyboru, zamknięcie okna

        folder_path = folder.get_path()
        if not folder_path:
            return

        try:
            project = load_theme_project(folder_path)
        except (ProjectNotFoundError, InvalidThemeError) as err:
            self._show_alert(
                t("dialog.load.error.title"),
                t("dialog.load.error.detail", err=err),
            )
            return

        # Uzupełnienie formularza w lewym oknie
        self.theme_name_entry.set_text(project.name)
        self.theme_comment_entry.set_text(project.comment)

        # Wyczyszczenie listy svg w prawym oknie
        self._clear_icons_list()

        # Odtworzenie listy IconRow dla ikon z projektu
        for icon in project.icons:
            row = IconRow.from_loaded_icon(icon, self.suggestions_map)
            row.btn_remove.connect("clicked", lambda btn, r=row: self.icons_listbox.remove(r))
            self.icons_listbox.append(row)


    def on_about_clicked(self, button: Gtk.Button) -> None:
        """Akcja po kliknięciu przycisku 'i' (O programie)."""
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(self)
        about_dialog.set_modal(True)
        about_dialog.set_program_name(APP_NAME_FULL)
        about_dialog.set_version(__version__)
        about_dialog.set_comments(t("about.comments"))
        about_dialog.set_authors([APP_AUTHOR])
        about_dialog.set_logo_icon_name("applications-graphics-symbolic")
        about_dialog.present()

    def _show_alert(self, title: str, detail: str) -> None:
        """Wyświetla natywne okno komunikatu"""
        dialog = Gtk.AlertDialog(
            message=title,
            detail=detail,
        )
        dialog.set_buttons(["OK"])
        dialog.show(self)

    def _collect_project_from_ui(self) -> tuple[ThemeProject, list[str], list[str]]:
        """Zbiera dane z lewego formularza oraz listy wierszy do obiektu ThemeProject.

        Returns:
            Krotka (ThemeProject, lista_duplikatów, lista_niekompletnych_wierszy).
        """
        name = self.theme_name_entry.get_text().strip()
        comment = self.theme_comment_entry.get_text().strip() or DEFAULT_COMMENT
        slug = name.replace(" ", "-")

        icons: list[LoadedIcon] = []
        seen_targets: set[tuple[str, str]] = set()
        duplicates: list[str] = []
        incomplete_files: list[str] = []

        row = self.icons_listbox.get_first_child()
        while row is not None:
            if isinstance(row, IconRow):
                loaded_icon = row.to_loaded_icon()
                if not loaded_icon.context or not loaded_icon.icon_name:
                    incomplete_files.append(loaded_icon.filepath.name)
                else:
                    target_key = (loaded_icon.context, loaded_icon.icon_name)
                    if target_key in seen_targets:
                        duplicates.append(f"{loaded_icon.context}/{loaded_icon.icon_name}")
                    else:
                        seen_targets.add(target_key)
                    icons.append(loaded_icon)
            row = row.get_next_sibling()

        project = ThemeProject(
            path=DEFAULT_ICONS_DIR / slug,
            name=name,
            comment=comment,
            inherits=DEFAULT_INHERITS,
            icons=icons,
        )
        return project, duplicates, incomplete_files


    def on_button_clicked(self, button: Gtk.Button) -> None:
        """Akcja po kliknięciu 'Zbuduj motyw': waliduje dane i kompiluje motyw na dysku."""
        logger.debug("build_theme_clicked_begin")
        project, duplicates, incomplete_files = self._collect_project_from_ui()

        if not project.name:
            self._show_alert(
                t("alert.no_name.title"),
                t("alert.no_name.detail"),
            )
            return

        if not project.icons and not incomplete_files:
            self._show_alert(
                t("alert.empty_list.title"),
                t("alert.empty_list.detail"),
            )
            return

        if incomplete_files:
            self._show_alert(
                t("alert.incomplete.title"),
                t("alert.incomplete.detail", files="\n• ".join(incomplete_files)),
            )
            return

        if duplicates:
            unique_duplicates = list(dict.fromkeys(duplicates))
            self._show_alert(
                t("alert.duplicates.title"),
                t("alert.duplicates.detail", duplicates="\n• ".join(unique_duplicates)),
            )
            return

        try:
            project_dir, saved_count = save_theme_project(project)
        except Exception as err:
            logger.exception("build_theme_failed")
            self._show_alert(
                t("alert.build_error.title"),
                t("alert.build_error.detail", err=err),
            )
            return

        logger.debug(f"build_theme_success: dir={project_dir} count={saved_count}")
        self._show_alert(
            t("alert.build_success.title"),
            t(
                "alert.build_success.detail",
                name=project.name,
                count=saved_count,
                path=project_dir,
            ),
        )

    def on_add_svg_clicked(self, button: Gtk.Button) -> None:
        """Akcja po kliknięciu 'Dodaj SVG'."""
        logger.debug("add_svg_button_clicked")

        dialog = Gtk.FileDialog()
        dialog.set_title(t("dialog.add_svg.title"))

        svg_filter = Gtk.FileFilter()
        svg_filter.set_name(t("dialog.add_svg.filter"))
        svg_filter.add_mime_type("image/svg+xml")
        svg_filter.add_pattern("*.svg")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(svg_filter)

        dialog.set_filters(filters)
        dialog.set_default_filter(svg_filter)
        dialog.open_multiple(self, None, self._on_files_selected)

    def _on_files_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        """Callback odbierający listę wybranych plików po zamknięciu okna dialogowego."""
        try:
            files = dialog.open_multiple_finish(result)
        except GLib.Error:
            return

        for i in range(files.get_n_items()):
            gfile = files.get_item(i)
            filepath = gfile.get_path()
            if filepath:
                self._add_svg_row(filepath)

    def _add_svg_row(self, filepath: str) -> None:
        try:
            valid_path = validate_svg(filepath)
        except (FileNotFoundError, InvalidSVGError) as e:
            logger.debug(f"invalid_file_skipped: {e}")
            return

        new_row = IconRow(
            filepath=str(valid_path),
            suggestions_map=self.suggestions_map,
        )
        new_row.btn_remove.connect("clicked", lambda btn: self.icons_listbox.remove(new_row))
        self.icons_listbox.append(new_row)

class IconBuilderApp(Gtk.Application):
    """Klasa aplikacji zarządzająca cyklem życia."""

    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(application=self)
        win.present()

def main() -> int:
    """Główny punkt wejścia aplikacji GTK 4."""
    app = IconBuilderApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())