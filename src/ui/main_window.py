from gi.repository.Gio import file_parse_name
import sys
import gi
from src import __version__, APP_NAME_FULL, APP_AUTHOR, APP_ID
from src.core.icon_database import IconDatabase
from src.config import CONTEXTS

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio


class IconRow(Gtk.ListBoxRow):
    """Reprezentuje pojedynczy wiersz pliku SVG z wyborem kontekstu i autouzupełnianiem."""

    def __init__(self, filepath: str, suggestions_map: dict[str, list[str]], *args, **kwargs) -> None:
        """
        Args:
            filepath: Ścieżka do wczytanego pliku .svg.
            suggestions_map: Słownik zawierający listy podpowiedzi dla każdego kontekstu
                             (np. {'apps': ['firefox', ...], 'status': ['battery', ...]}).
        """
        super().__init__(*args, **kwargs)
        self.filepath = filepath
        self.filename = filepath.split('/')[-1]
        self.suggestions_map = suggestions_map

        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row_box.set_margin_top(8)
        row_box.set_margin_bottom(8)
        row_box.set_margin_start(10)
        row_box.set_margin_end(10)

        # 1. MINIATURKA DODAWANEGO PLIKU I NAZWA
        self.input_preview = Gtk.Image.new_from_file(self.filepath)
        self.input_preview.set_pixel_size(48)
        row_box.append(self.input_preview)

        filename_label = Gtk.Label(label=f"<b>{self.filename}</b>", use_markup=True)
        filename_label.set_halign(Gtk.Align.START)
        filename_label.set_width_chars(15)
        filename_label.set_ellipsize(3)
        row_box.append(filename_label)

        # Strzałka
        arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
        arrow.add_css_class("dim-label")
        row_box.append(arrow)

        # 2. MINIATURKA IKONY DOCELOWEJ
        self.target_preview = Gtk.Image.new_from_icon_name("image-missing")
        self.target_preview.set_pixel_size(48)
        row_box.append(self.target_preview)

        # 3. WYBÓR KONTEKSTU (Mały DropDown)
        context_keys = list(self.suggestions_map.keys())
        self.context_dropdown = Gtk.DropDown(model=Gtk.StringList.new(context_keys))
        self.context_dropdown.set_valign(Gtk.Align.CENTER)
        self.context_dropdown.connect("notify::selected-item", self.on_context_changed)
        row_box.append(self.context_dropdown)

        # 4. WYSZUKIWARKA NAZWY (Główny DropDown z autouzupełnianiem)
        self.name_dropdown = Gtk.DropDown()
        self.name_dropdown.set_hexpand(True)
        self.name_dropdown.set_enable_search(True)
        self.name_dropdown.set_valign(Gtk.Align.CENTER)
        self.name_dropdown.connect("notify::selected-item", self.on_name_changed)
        row_box.append(self.name_dropdown)

        # 5. PRZYCISK USUWANIA
        self.btn_remove = Gtk.Button(icon_name="user-trash-symbolic")
        self.btn_remove.add_css_class("destructive-action")
        self.btn_remove.add_css_class("flat")
        self.btn_remove.set_valign(Gtk.Align.CENTER)
        row_box.append(self.btn_remove)

        self.set_child(row_box)

        # Wymuszenie załadowania pierwszego kontekstu i podpowiedzi podczas startu
        self.on_context_changed(self.context_dropdown, None)

    def on_context_changed(self, dropdown: Gtk.DropDown, pspec) -> None:
        """Odświeża listę autouzupełniania po wybraniu nowej kategorii (kontekstu)."""
        selected_item = dropdown.get_selected_item()
        if not selected_item:
            return

        context = selected_item.get_string()
        new_suggestions = self.suggestions_map.get(context, [])

        # Podmiana modelu w drugim DropDown
        self.name_dropdown.set_model(Gtk.StringList.new(new_suggestions))

        # Ręczne odświeżenie miniaturki, by uniknąć starej ikony z poprzedniego kontekstu
        self.on_name_changed(self.name_dropdown, None)

    def on_name_changed(self, dropdown: Gtk.DropDown, pspec) -> None:
        """Odświeża miniaturkę ikony docelowej na podstawie wybranej nazwy z bazy."""
        selected_item = dropdown.get_selected_item()
        if selected_item:
            icon_name = selected_item.get_string()
            self.target_preview.set_from_icon_name(icon_name)
        else:
            self.target_preview.set_from_icon_name("image-missing")

    def get_selected_context(self) -> str:
        """Zwraca wybraną kategorię (np. 'apps')."""
        item = self.context_dropdown.get_selected_item()
        return item.get_string() if item else ""

    def get_selected_name(self) -> str:
        """Zwraca wybraną nazwę ikony systemowej."""
        item = self.name_dropdown.get_selected_item()
        return item.get_string() if item else ""

class MainWindow(Gtk.ApplicationWindow):
    """Klasa głównego okna aplikacji"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.set_title(f"{APP_NAME_FULL} - Main Window")
        self.set_default_size(1200, 800)
        self.set_resizable(True)

        print("Rozpoczęcie skanowania dysku w poszukiwaniu ikon")
        self.icon_db = IconDatabase(fallback_theme="Adwaita")
        self.icon_db.build_database()

        self.suggestions_map = {ctx: self.icon_db.get_suggestions(ctx) for ctx in CONTEXTS}
        print("Zakończono ładowanie bazy ikon.")

        self._setup_header_bar()
        self._setup_layout()

    def _setup_header_bar(self) -> None:
        """Tworzy natywny pasek tytułowy GNOME"""
        header_bar = Gtk.HeaderBar()
        self.set_titlebar(header_bar)

        self.about_btn = Gtk.Button(icon_name="dialog-information-symbolic")
        self.about_btn.add_css_class("flat")
        self.about_btn.connect("clicked", self.on_about_clicked)
        header_bar.pack_start(self.about_btn)

        self.build_btn = Gtk.Button(label="Zbuduj motyw")
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
        left_panel.set_size_request(300, -1)  # Stała minimalna szerokość 300px

        # Przyciski zarządzania projektem
        project_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.btn_new_theme = Gtk.Button(label="Nowy motyw")
        self.btn_new_theme.set_hexpand(True)
        self.btn_new_theme.connect("clicked", self.on_new_theme_clicked)

        self.btn_load_theme = Gtk.Button(label="Wczytaj motyw")
        self.btn_load_theme.set_hexpand(True)
        self.btn_load_theme.connect("clicked", self.on_load_theme_clicked)

        project_actions_box.append(self.btn_new_theme)
        project_actions_box.append(self.btn_load_theme)

        left_panel.append(project_actions_box)

        settings_title = Gtk.Label(label="<b>Ustawienia Projektu</b>", use_markup=True)
        settings_title.set_halign(Gtk.Align.START)
        left_panel.append(settings_title)

        # Pola formularza
        self.theme_name_entry = Gtk.Entry(placeholder_text="Np. Material-Expressive")
        self.theme_comment_entry = Gtk.Entry(placeholder_text="Opis motywu")

        left_panel.append(Gtk.Label(label="Nazwa motywu:", halign=Gtk.Align.START))
        left_panel.append(self.theme_name_entry)

        left_panel.append(Gtk.Label(label="Opis:", halign=Gtk.Align.START))
        left_panel.append(self.theme_comment_entry)

        main_box.append(left_panel)

        # Separator wizualny
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(separator)

        # 2. PRAWY PANEL (Lista ikon)
        right_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right_panel.set_hexpand(True)  # Zajmuje całą pozostałą przestrzeń (dobrze dla szerokich monitorów)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        icons_title = Gtk.Label(label="<b>Pliki SVG w motywie</b>", use_markup=True)
        icons_title.set_hexpand(True)
        icons_title.set_halign(Gtk.Align.START)

        self.add_icon_btn = Gtk.Button(label="+ Dodaj SVG")
        self.add_icon_btn.connect("clicked", self.on_add_svg_clicked)

        header_box.append(icons_title)
        header_box.append(self.add_icon_btn)
        right_panel.append(header_box)

        # Scrollowana lista dodanych ikon
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)  # Wypełnia miejsce w pionie
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.icons_listbox = Gtk.ListBox()
        self.icons_listbox.set_selection_mode(Gtk.SelectionMode.NONE)  # Wyłączamy zaznaczanie całych wierszy

        # Dodajemy placeholder widoczny, gdy lista jest pusta
        placeholder_label = Gtk.Label(label="Brak dodanych ikon.\nKliknij '+ Dodaj SVG', aby rozpocząć.")
        placeholder_label.set_justify(Gtk.Justification.CENTER)
        placeholder_label.add_css_class("dim-label")
        self.icons_listbox.set_placeholder(placeholder_label)

        scrolled_window.set_child(self.icons_listbox)
        right_panel.append(scrolled_window)

        main_box.append(right_panel)

        # --- Obsługa zdarzeń ---

    def on_new_theme_clicked(self, button: Gtk.Button) -> None:
        print("Czyszczenie formularza dla nowego motywu")
        self.theme_name_entry.set_text("")
        self.theme_comment_entry.set_text("")

    def on_load_theme_clicked(self, button: Gtk.Button) -> None:
        print("Otwarcie okna wyboru folderu")

    def on_about_clicked(self, button: Gtk.Button) -> None:
        """Akcja po kliknięciu przycisku 'i' (O programie)."""
        about_dialog = Gtk.AboutDialog()
        about_dialog.set_transient_for(self)  # Przypina okienko do głównego okna aplikacji
        about_dialog.set_modal(True)  # Blokuje główne okno do czasu zamknięcia informacji

        # Konfiguracja wyświetlanych danych
        about_dialog.set_program_name(APP_NAME_FULL)
        about_dialog.set_version(__version__)
        about_dialog.set_comments(
            "Narzędzie automatyzujące proces tworzenia i budowania motywów ikon dla systemów Linux.\n\n"
            "Pozwala na łatwe mapowanie plików SVG na systemowe nazwy w standardzie Freedesktop, "
            "buduje prawidłową strukturę katalogów oraz generuje plik konfiguracyjny index.theme."
        )
        about_dialog.set_authors([APP_AUTHOR])
        about_dialog.set_logo_icon_name("applications-graphics-symbolic")  # Ikona nad tytułem

        about_dialog.present()

    def on_button_clicked(self, button: Gtk.Button) -> None:
            """Akcja po kliknięciu 'Zbuduj motyw'."""
            name = self.theme_name_entry.get_text()
            print(f"Rozpoczynam budowanie motywu: {name}")
            # Tutaj w przyszłości podepniemy funkcję create_icon_theme_project()

    def on_add_svg_clicked(self, button: Gtk.Button) -> None:
        """Akcja po kliknięciu 'Dodaj SVG'."""
        print("Dodaję nowy plik z prawdziwymi systemowymi podpowiedziami...")

        # Tworzymy wiersz przekazując prawdziwy słownik z IconDatabase
        new_row = IconRow(
            filepath="/home/mzych/Obrazy/test_ikony.svg",
            suggestions_map=self.suggestions_map
        )

        # Obsługa usuwania wiersza po kliknięciu ikony kosza
        new_row.btn_remove.connect("clicked", lambda btn: self.icons_listbox.remove(new_row))

        # Dodajemy wiersz na koniec listy w interfejsie
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


if __name__ == "__main__":
    app = IconBuilderApp()
    sys.exit(app.run(sys.argv))