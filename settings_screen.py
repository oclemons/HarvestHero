"""settings_screen.py — Luxury settings with sections."""

import tkinter as tk

import customtkinter as ctk

from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_OVERLAY, BG_HOVER,
    ACCENT, ACCENT_HOVER, ACCENT_GOLD, SECONDARY_ACCENT, SECONDARY_ACCENT_HOVER,
    ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR, BORDER_SUBTLE,
    BG_PRIMARY, BG_CARD,
)
from toast import Toast


class SettingsScreen(ctk.CTkFrame):
    def __init__(self, parent, db):
        super().__init__(parent, fg_color=BG_SURFACE)
        self.db = db
        self._vars: dict = {}
        self._adv_visible = False
        self._build()
        self._load()

    # ------------------------------------------------------------------
    # Build helpers
    # ------------------------------------------------------------------

    def _section_header(self, scroll, title: str, subtitle: str, row: int):
        f = ctk.CTkFrame(scroll, fg_color="transparent")
        f.grid(row=row, column=0, sticky="ew", padx=40, pady=(24, 6))
        ctk.CTkLabel(
            f, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                f, text=subtitle,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=TEXT_MUTED,
            ).pack(anchor="w")

    def _card(self, scroll, row: int):
        f = ctk.CTkFrame(
            scroll, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        f.grid(row=row, column=0, sticky="ew", padx=40)
        f.grid_columnconfigure(1, weight=1)
        return f

    def _field_row(self, card, label: str, key: str, row: int,
                   placeholder: str = "", show: str = "", readonly: bool = False):
        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=row, column=0, padx=20, pady=12, sticky="w")
        var = tk.StringVar()
        self._vars[key] = var
        e = ctk.CTkEntry(
            card, textvariable=var, height=38,
            placeholder_text=placeholder,
            fg_color=BG_OVERLAY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
            corner_radius=8, show=show,
            state="readonly" if readonly else "normal",
        )
        e.grid(row=row, column=1, padx=(0, 20), pady=12, sticky="ew")

    def _select_row(self, card, label: str, key: str, row: int,
                    options: list, default: str = None):
        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=row, column=0, padx=20, pady=12, sticky="w")
        var = tk.StringVar(value=default or options[0])
        self._vars[key] = var
        ctk.CTkOptionMenu(
            card, variable=var, values=options,
            height=38, corner_radius=8,
            fg_color=BG_OVERLAY, button_color=SECONDARY_ACCENT,
            button_hover_color=SECONDARY_ACCENT_HOVER,
            text_color=TEXT_PRIMARY,
        ).grid(row=row, column=1, padx=(0, 20), pady=12, sticky="e")

    def _info_row(self, card, label: str, value: str, row: int,
                  value_color: str = None):
        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=row, column=0, padx=20, pady=12, sticky="w")
        ctk.CTkLabel(
            card, text=value,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=value_color or TEXT_PRIMARY, anchor="e",
        ).grid(row=row, column=1, padx=(0, 20), pady=12, sticky="e")

    def _divider(self, card, row: int):
        ctk.CTkFrame(
            card, height=1, fg_color=BORDER_COLOR,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=20)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # Title
        hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=40, pady=(28, 0))
        ctk.CTkLabel(
            hdr, text="Settings",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        r = 1  # rolling row counter

        # ── 1. Organization Profile ─────────────────────────────────
        self._section_header(scroll, "Organization Profile",
                              "Your organization's identity within the app.", r)
        r += 1
        org = self._card(scroll, r); r += 1
        self._field_row(org, "Organization Name", "org_name", 0,
                        "e.g. Acme Corp")

        # ── 2. AI Assistant ─────────────────────────────────────────
        self._section_header(scroll, "AI Assistant — Ava",
                              "Ava is your built-in inventory intelligence assistant.", r)
        r += 1
        ai = self._card(scroll, r); r += 1
        self._info_row(ai, "Status",  "Enabled",            0, ACCENT_GREEN)
        self._divider(ai, 1)
        self._info_row(ai, "Mode",    "Built-in Local AI",  2, ACCENT)
        self._divider(ai, 3)

        ctk.CTkLabel(
            ai,
            text="Ava provides local inventory insights, onboarding help, low-stock\n"
                 "recommendations, and trend summaries — no API key required.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED, anchor="w", justify="left",
        ).grid(row=4, column=0, columnspan=2, padx=20, pady=(12, 16), sticky="w")

        # ── 3. Onboarding Tour ──────────────────────────────────────
        self._section_header(scroll, "Onboarding Tour",
                              "Guide new users through the app on first login.", r)
        r += 1
        tour = self._card(scroll, r); r += 1
        self._select_row(tour, "Show tour for new users", "tour_enabled",
                         0, ["Yes", "No"], "Yes")
        self._divider(tour, 1)
        btn_row = ctk.CTkFrame(tour, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=2, padx=20, pady=(8, 16), sticky="w")
        ctk.CTkButton(
            btn_row, text="Reset Tour for All Users",
            height=36, corner_radius=8,
            fg_color=SECONDARY_ACCENT, hover_color=SECONDARY_ACCENT_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._reset_all_tours,
        ).pack(side="left")

        # ── 4. Appearance ───────────────────────────────────────────
        self._section_header(scroll, "Appearance",
                              "Choose a color theme — restart the app to apply.", r)
        r += 1
        app = self._card(scroll, r); r += 1
        self._build_theme_picker(app)

        # ── 5. Data Import ───────────────────────────────────────────
        self._section_header(scroll, "Data Import",
                              "Drop CSV files into the input/ folder, then import here.", r)
        r += 1
        imp = self._card(scroll, r); r += 1
        self._build_import_section(imp)

        # ── 5b. Backup & Export ──────────────────────────────────────
        self._section_header(scroll, "Backup & Export",
                              "Keep your data safe and portable.", r)
        r += 1
        bk = self._card(scroll, r); r += 1
        bk_btns = ctk.CTkFrame(bk, fg_color="transparent")
        bk_btns.grid(row=0, column=0, columnspan=2, padx=20, pady=16, sticky="w")
        ctk.CTkButton(
            bk_btns, text="Backup Database Now",
            height=38, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=BG_BASE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._backup_now,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            bk_btns, text="Export Transactions (CSV)",
            height=38, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._export_csv,
        ).pack(side="left")
        self._last_backup_lbl = ctk.CTkLabel(
            bk, text="Last backup: —",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED, anchor="w",
        )
        self._last_backup_lbl.grid(
            row=1, column=0, columnspan=2, padx=20, pady=(0, 14), sticky="w")

        # ── 6. LDAP / Active Directory ───────────────────────────────
        self._section_header(scroll, "LDAP / Active Directory Authentication",
                              "Authenticate users against your organization's directory server.", r)
        r += 1
        ldap_card = self._card(scroll, r); r += 1
        self._build_ldap_section(ldap_card)

        # ── 7. Advanced Developer Settings ──────────────────────────
        self._section_header(scroll, "Advanced Developer Settings",
                              "OpenAI / external AI provider, API keys, model selection.", r)
        r += 1

        # Toggle button for advanced section
        self._adv_toggle_btn = ctk.CTkButton(
            scroll, text="Show Advanced Settings",
            height=34, corner_radius=8, width=200,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_MUTED,
            border_width=1, border_color=BORDER_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=self._toggle_advanced,
        )
        self._adv_toggle_btn.grid(
            row=r, column=0, padx=40, pady=(0, 8), sticky="w")
        r += 1

        self._adv_frame = ctk.CTkFrame(
            scroll, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        self._adv_frame.grid(row=r, column=0, sticky="ew", padx=40)
        self._adv_frame.grid_columnconfigure(1, weight=1)
        r += 1

        self._select_row(self._adv_frame, "AI Provider", "ai_provider",
                         0, ["Local (Built-in)", "OpenAI", "Ollama"], "Local (Built-in)")
        self._divider(self._adv_frame, 1)
        self._field_row(self._adv_frame, "API Key", "ai_api_key",
                        2, "sk-… (OpenAI only)", show="●")
        self._field_row(self._adv_frame, "Model",   "ai_model",
                        3, "gpt-4o-mini")

        ctk.CTkLabel(
            self._adv_frame,
            text="API keys are stored locally and never sent anywhere except the selected provider.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=4, column=0, columnspan=2, padx=20, pady=(4, 16), sticky="w")

        self._adv_frame.grid_remove()   # hidden by default

        # ── Save ────────────────────────────────────────────────────
        save_row = ctk.CTkFrame(scroll, fg_color="transparent")
        save_row.grid(row=r, column=0, padx=40, pady=28, sticky="w")
        ctk.CTkButton(
            save_row, text="Save Settings",
            height=46, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=BG_BASE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._save,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            save_row, text="Cancel",
            height=46, corner_radius=10,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            command=self._load,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # LDAP section
    # ------------------------------------------------------------------

    def _build_ldap_section(self, card):
        from ldap_auth import get_ldap_config
        cfg = get_ldap_config()
        self._lv = {
            "enabled":          tk.BooleanVar(value=bool(cfg.get("enabled", False))),
            "server_url":       tk.StringVar(value=cfg.get("server_url", "")),
            "port":             tk.StringVar(value=str(cfg.get("port", "389"))),
            "use_ssl":          tk.BooleanVar(value=bool(cfg.get("use_ssl", False))),
            "use_tls":          tk.BooleanVar(value=bool(cfg.get("use_tls", False))),
            "dn_format":        tk.StringVar(value=cfg.get("dn_format", "{username}@company.com")),
            "base_dn":          tk.StringVar(value=cfg.get("base_dn", "")),
            "search_attr":      tk.StringVar(value=cfg.get("search_attr", "sAMAccountName")),
            "service_dn":       tk.StringVar(value=cfg.get("service_dn", "")),
            "service_password": tk.StringVar(value=cfg.get("service_password", "")),
            "fallback_to_local": tk.BooleanVar(value=bool(cfg.get("fallback_to_local", True))),
        }
        card.grid_columnconfigure(1, weight=1)

        def _lbl(text, row, col=0, span=1):
            ctk.CTkLabel(
                card, text=text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_SECONDARY, anchor="w",
            ).grid(row=row, column=col, columnspan=span, padx=20, pady=(10, 2), sticky="w")

        def _entry(key, row, placeholder="", show=""):
            ctk.CTkEntry(
                card, textvariable=self._lv[key],
                placeholder_text=placeholder, height=36, show=show,
                fg_color=BG_OVERLAY, border_color=BORDER_COLOR,
                text_color=TEXT_PRIMARY, corner_radius=8,
            ).grid(row=row, column=0, columnspan=2, padx=20, pady=(0, 4), sticky="ew")

        def _check(key, label, row):
            ctk.CTkCheckBox(
                card, text=label, variable=self._lv[key],
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_SECONDARY,
                fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=BORDER_COLOR,
            ).grid(row=row, column=0, columnspan=2, padx=20, pady=4, sticky="w")

        # Enable toggle
        ctk.CTkCheckBox(
            card, text="Enable LDAP / Active Directory authentication",
            variable=self._lv["enabled"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=BORDER_COLOR,
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(16, 4), sticky="w")

        # Server
        _lbl("Server URL", 1)
        _entry("server_url", 2, "ldap://192.168.1.10  or  ldaps://dc.company.com")

        # Port + SSL/TLS
        _lbl("Port", 3)
        port_row = ctk.CTkFrame(card, fg_color="transparent")
        port_row.grid(row=4, column=0, columnspan=2, padx=20, pady=(0, 4), sticky="w")
        ctk.CTkEntry(
            port_row, textvariable=self._lv["port"], width=80, height=36,
            fg_color=BG_OVERLAY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack(side="left", padx=(0, 16))
        ctk.CTkCheckBox(
            port_row, text="Use SSL (LDAPS, port 636)",
            variable=self._lv["use_ssl"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=BORDER_COLOR,
        ).pack(side="left", padx=(0, 16))
        ctk.CTkCheckBox(
            port_row, text="Use STARTTLS",
            variable=self._lv["use_tls"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=TEXT_SECONDARY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=BORDER_COLOR,
        ).pack(side="left")

        # DN format
        _lbl("Bind / DN Format  ({username} is replaced at login)", 5)
        _entry("dn_format", 6, "{username}@company.com")
        ctk.CTkLabel(
            card,
            text="Examples:  {username}@company.com  ·  uid={username},ou=users,dc=co,dc=com  ·  CN={username},OU=Users,DC=co,DC=com",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=7, column=0, columnspan=2, padx=20, pady=(0, 4), sticky="w")

        # Base DN + search
        _lbl("Base DN  (for display-name lookup, optional)", 8)
        _entry("base_dn", 9, "DC=company,DC=com")
        _lbl("Search Attribute  (AD: sAMAccountName  /  OpenLDAP: uid)", 10)
        _entry("search_attr", 11, "sAMAccountName")

        # Service account
        _lbl("Service Account DN  (optional, for search-then-bind)", 12)
        _entry("service_dn", 13, "CN=svc_ldap,OU=ServiceAccounts,DC=company,DC=com")
        _lbl("Service Account Password", 14)
        _entry("service_password", 15, "", show="\u25cf")

        # Fallback
        _check("fallback_to_local",
               "Fall back to local account if LDAP fails (recommended)", 16)

        # Buttons
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=17, column=0, columnspan=2, padx=20, pady=(12, 16), sticky="w")
        ctk.CTkButton(
            btn_row, text="Save LDAP Settings",
            height=38, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=BG_OVERLAY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._save_ldap_config,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_row, text="Test Connection",
            height=38, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._test_ldap_connection,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Data import
    # ------------------------------------------------------------------

    def _build_import_section(self, card):
        from paths import INPUT_DIR
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text="Place a CSV file in the input/ folder using the template format,\n"
                 "then click Import to load items into inventory.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED, anchor="w", justify="left",
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(14, 8), sticky="w")

        ctk.CTkLabel(
            card,
            text=f"Input folder:  {INPUT_DIR}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 8), sticky="w")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 14), sticky="w")

        ctk.CTkButton(
            btn_row, text="Import Inventory CSV",
            height=38, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=BG_BASE,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._import_csv,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row, text="Open Input Folder",
            height=38, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._open_folder(INPUT_DIR),
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row, text="Open Output Folder",
            height=38, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._open_folder(__import__("paths").OUTPUT_DIR),
        ).pack(side="left")

    def _open_folder(self, path: str):
        import subprocess, sys
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", path])
            elif sys.platform == "win32":
                subprocess.Popen(["explorer", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            Toast.show(self, f"Could not open folder: {e}", kind="error")

    _CSV_MAX_BYTES = 50 * 1024 * 1024   # 50 MB
    _CSV_MAX_ROWS  = 100_000

    def _import_csv(self):
        import csv, os
        from tkinter import filedialog
        from paths import INPUT_DIR

        path = filedialog.askopenfilename(
            title="Select inventory CSV",
            initialdir=INPUT_DIR,
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return

        # File-extension guard: only accept .csv. Belt-and-suspenders on
        # top of the filedialog filter, which the user can bypass on Mac.
        if not path.lower().endswith(".csv"):
            Toast.show(self, "Only .csv files are supported for import.",
                       kind="error")
            return

        # Size cap: refuse pathologically large files before we read
        # anything into memory.
        try:
            size = os.path.getsize(path)
        except OSError as exc:
            Toast.show(self, f"Cannot read file: {exc}", kind="error")
            return
        if size > self._CSV_MAX_BYTES:
            Toast.show(self,
                f"CSV is {size // (1024*1024)} MB — max is "
                f"{self._CSV_MAX_BYTES // (1024*1024)} MB.",
                kind="error")
            return

        required = {"barcode", "item_name"}
        added = updated = skipped = 0
        errors = []

        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                cols = set(reader.fieldnames or [])
                if not required.issubset(cols):
                    Toast.show(self,
                        f"CSV must have columns: {', '.join(required)}",
                        kind="error")
                    return

                for i, row in enumerate(reader, start=2):
                    if (i - 1) > self._CSV_MAX_ROWS:
                        errors.append(
                            f"Stopped at row {self._CSV_MAX_ROWS + 1}: "
                            f"max import size is {self._CSV_MAX_ROWS} rows."
                        )
                        break
                    try:
                        barcode  = row.get("barcode", "").strip()
                        name     = row.get("item_name", "").strip()
                        if not barcode or not name:
                            skipped += 1
                            continue

                        existing = self.db.get_item_by_barcode(barcode)
                        qty   = int(row.get("current_quantity", 0) or 0)
                        mstk  = int(row.get("minimum_stock", 0) or 0)
                        cat   = row.get("category", "")
                        notes = row.get("notes", "")
                        brand = row.get("brand", "")
                        loc   = row.get("storage_location", "")
                        exp   = row.get("expiration_date", "")
                        has_bout = "barcode_out" in cols

                        if existing:
                            b_out = (row["barcode_out"].strip() if has_bout
                                     else (existing.get("barcode_out") or ""))
                            self.db.update_item(
                                existing["id"],
                                item_name=name, category=cat,
                                minimum_stock=mstk, notes=notes,
                                barcode_out=b_out,
                            )
                            # Preserve AI-populated fields the CSV doesn't
                            # carry; without this, re-importing an existing
                            # inventory wipes shelf_life_days and nutrition_data.
                            self.db.update_item_extended(
                                existing["id"],
                                brand=brand, storage_location=loc,
                                expiration_date=exp,
                                shelf_life_days=int(existing.get("shelf_life_days") or 0),
                                nutrition_data=existing.get("nutrition_data") or "{}",
                            )
                            if qty > 0:
                                self.db.set_stock(existing["id"], qty)
                            updated += 1
                        else:
                            b_out = row["barcode_out"].strip() if has_bout else ""
                            self.db.add_item(
                                barcode=barcode, barcode_out=b_out,
                                item_name=name,
                                category=cat, quantity=qty,
                                minimum_stock=mstk, notes=notes,
                                brand=brand, storage_location=loc,
                                expiration_date=exp,
                            )
                            added += 1
                    except Exception as row_err:
                        errors.append(f"Row {i}: {row_err}")

            msg = f"Import complete — {added} added, {updated} updated, {skipped} skipped."
            if errors:
                msg += f"  ({len(errors)} row errors)"
            Toast.show(self, msg, kind="success" if not errors else "warning")

        except Exception as e:
            Toast.show(self, f"Import failed: {e}", kind="error")

    def _save_ldap_config(self):
        from ldap_auth import save_ldap_config
        try:
            cfg = {
                k: (v.get() if isinstance(v, (tk.StringVar,)) else bool(v.get()))
                for k, v in self._lv.items()
            }
            cfg["port"] = int(cfg.get("port") or 389)
            save_ldap_config(cfg)
            Toast.show(self, "LDAP settings saved.", kind="success")
        except Exception as exc:
            Toast.show(self, f"Save failed: {exc}", kind="error")

    def _test_ldap_connection(self):
        from ldap_auth import test_ldap_connection
        try:
            cfg = {
                k: (v.get() if isinstance(v, (tk.StringVar,)) else bool(v.get()))
                for k, v in self._lv.items()
            }
            cfg["port"] = int(cfg.get("port") or 389)
            ok, msg = test_ldap_connection(cfg)
            if ok:
                Toast.show(self, msg, kind="success")
            else:
                Toast.show(self, msg, kind="error")
        except Exception as exc:
            Toast.show(self, f"Test error: {exc}", kind="error")

    # ------------------------------------------------------------------
    # Theme picker
    # ------------------------------------------------------------------

    def _build_theme_picker(self, card):
        from theme import get_preset_names, get_preset_swatches, get_active_theme_name
        names = get_preset_names()
        current = get_active_theme_name()

        ctk.CTkLabel(
            card, text="Color Theme",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 16), sticky="w")

        self._theme_selected = tk.StringVar(value=current)
        self._theme_btns: dict = {}

        def _pick(name):
            self._theme_selected.set(name)
            for n, (box, lbl) in self._theme_btns.items():
                active = (n == name)
                box.configure(border_color=ACCENT if active else BORDER_COLOR,
                               border_width=2 if active else 1)
                lbl.configure(text_color=ACCENT if active else TEXT_MUTED)

        cols_per_row = 5
        row_i = col = 0
        for name in names:
            swatches = get_preset_swatches(name)
            box = ctk.CTkFrame(
                grid, fg_color=swatches[0] if swatches else BG_ELEVATED,
                corner_radius=10, border_width=2 if name == current else 1,
                border_color=ACCENT if name == current else BORDER_COLOR,
                width=110, height=80,
                cursor="hand2",
            )
            box.grid(row=row_i, column=col, padx=(0, 10), pady=(0, 10), sticky="nw")
            box.grid_propagate(False)

            swatch_row = ctk.CTkFrame(box, fg_color="transparent")
            swatch_row.place(relx=0.5, rely=0.35, anchor="center")
            for i, sw in enumerate(swatches[1:4]):
                dot = ctk.CTkFrame(swatch_row, fg_color=sw,
                                   width=14, height=14, corner_radius=7)
                dot.grid(row=0, column=i, padx=2)
                dot.grid_propagate(False)

            lbl = ctk.CTkLabel(
                box, text=name,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                text_color=ACCENT if name == current else TEXT_MUTED,
            )
            lbl.place(relx=0.5, rely=0.78, anchor="center")

            self._theme_btns[name] = (box, lbl)
            box.bind("<Button-1>", lambda e, n=name: _pick(n))
            for child in box.winfo_children():
                child.bind("<Button-1>", lambda e, n=name: _pick(n))

            col += 1
            if col >= cols_per_row:
                col = 0
                row_i += 1

        self._restart_lbl = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=ACCENT_AMBER, anchor="w",
        )
        self._restart_lbl.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 4), sticky="w")

        self._apply_theme_btn = ctk.CTkButton(
            card, text="Apply Theme & Restart",
            height=38, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=BG_PRIMARY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._apply_theme,
        )
        self._apply_theme_btn.grid(row=3, column=0, columnspan=2, padx=20, pady=(0, 16), sticky="w")

    def _apply_theme(self):
        from theme import set_theme_name
        chosen = self._theme_selected.get()
        set_theme_name(chosen)
        self._restart_lbl.configure(text="Restarting…")
        self.update()
        import os, sys
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # ------------------------------------------------------------------
    # Advanced toggle
    # ------------------------------------------------------------------

    def _toggle_advanced(self):
        self._adv_visible = not self._adv_visible
        if self._adv_visible:
            self._adv_frame.grid()
            self._adv_toggle_btn.configure(text="Hide Advanced Settings")
        else:
            self._adv_frame.grid_remove()
            self._adv_toggle_btn.configure(text="Show Advanced Settings")

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load(self):
        for key, var in self._vars.items():
            val = self.db.get_app_setting(key)
            if val:
                var.set(val)
        # Last backup timestamp
        last = self.db.get_app_setting("last_backup")
        if last and hasattr(self, "_last_backup_lbl"):
            self._last_backup_lbl.configure(text=f"Last backup: {last}")

    def _save(self):
        for key, var in self._vars.items():
            self.db.set_app_setting(key, var.get())
        Toast.show(self, "Settings saved", kind="success")

    def _reset_all_tours(self):
        try:
            conn = self.db._connect()
            conn.execute("UPDATE users SET has_completed_tour=0")
            conn.commit()
            conn.close()
            Toast.show(self, "Tour reset for all users", kind="info")
        except Exception as e:
            Toast.show(self, f"Error: {e}", kind="error")

    def _backup_now(self):
        import shutil, os, datetime
        from paths import BACKUP_DIR
        ts_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        src = self.db.db_path
        dst = os.path.join(BACKUP_DIR, f"inventory_backup_{ts_file}.db")
        try:
            shutil.copy2(src, dst)
            # The backup contains password hashes, salts, and all
            # inventory data. Lock it to owner-only.
            try:
                os.chmod(dst, 0o600)
            except OSError:
                pass
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            self.db.set_app_setting("last_backup", ts)
            self._last_backup_lbl.configure(text=f"Last backup: {ts}")
            Toast.show(self, f"Backup saved → output/backups/{os.path.basename(dst)}", kind="success")
        except Exception as e:
            Toast.show(self, f"Backup failed: {e}", kind="error")

    def _export_csv(self):
        import csv, os, datetime
        from tkinter import filedialog
        from paths import EXPORT_DIR
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=EXPORT_DIR,
            initialfile=f"transactions_{datetime.date.today()}.csv",
        )
        if not path:
            return
        try:
            txns = self.db.get_transactions()
            with open(path, "w", newline="", encoding="utf-8") as f:
                if txns:
                    writer = csv.DictWriter(f, fieldnames=txns[0].keys())
                    writer.writeheader()
                    writer.writerows(txns)
            Toast.show(self, f"Exported {len(txns)} rows to {os.path.basename(path)}", kind="success")
        except Exception as e:
            Toast.show(self, f"Export failed: {e}", kind="error")

    def on_shown(self):
        self._load()
