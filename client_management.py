"""client_management.py — Pantry client (student) profiles + visit tracking.

Staff and admins can create/view student profiles (semester, full-time vs.
part-time status, contact info) and log each pantry visit (pounds of food
received). Weekly visit limits are enforced per enrollment status, and the
limit values themselves are only editable by admins.
"""

import datetime
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_OVERLAY, BG_HOVER,
    ACCENT, ACCENT_HOVER, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_GOLD,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, FONT_FAMILY, BORDER_COLOR,
    BG_PRIMARY, BG_SECONDARY, BG_CARD,
)
from toast import Toast

_DEFAULT_LIMIT_FULL_TIME = "2"   # visits per week
_DEFAULT_LIMIT_PART_TIME = "1"   # visits per week


def _week_start_iso() -> str:
    """ISO date (YYYY-MM-DD) for the Monday of the current week."""
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    return monday.isoformat()


# ---------------------------------------------------------------------------
# Create / Edit Client Modal
# ---------------------------------------------------------------------------

class _ClientModal(ctk.CTkToplevel):
    def __init__(self, parent, db, client_data: dict = None, on_save=None):
        super().__init__(parent)
        self.db          = db
        self.client_data = client_data  # None = create mode
        self.on_save     = on_save
        self._edit_mode  = client_data is not None

        self.title("Edit Client" if self._edit_mode else "Add Client")
        self.geometry("460x740")
        self.minsize(440, 640)
        self.resizable(False, False)
        self.after(50, self._deferred_init)

    def _deferred_init(self):
        self.configure(fg_color=BG_SURFACE)
        self._build()
        self.update_idletasks()
        self.lift()
        self.focus_force()
        self.grab_set()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Edit Client" if self._edit_mode else "Add New Client",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=28, pady=(24, 4))

        ctk.CTkLabel(
            self, text="Student profile used to track pantry visits and limits.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 20))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=28)
        form.grid_columnconfigure(0, weight=1)

        d = self.client_data or {}

        def _field(label, var, row, placeholder=""):
            ctk.CTkLabel(
                form, text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=TEXT_SECONDARY,
            ).grid(row=row * 2, column=0, sticky="w", pady=(10, 3))
            e = ctk.CTkEntry(
                form, textvariable=var, placeholder_text=placeholder,
                height=38, fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
                text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
                corner_radius=8,
            )
            e.grid(row=row * 2 + 1, column=0, sticky="ew")
            return e

        self._fn = tk.StringVar(value=d.get("first_name", ""))
        self._ln = tk.StringVar(value=d.get("last_name", ""))
        self._sid = tk.StringVar(value=d.get("student_id", ""))
        self._em = tk.StringVar(value=d.get("email", ""))
        self._ph = tk.StringVar(value=d.get("phone", ""))
        self._sem = tk.StringVar(value=d.get("semester", ""))
        self._status = tk.StringVar(value=d.get("enrollment_status", "full_time"))
        self._hh = tk.StringVar(value=str(d.get("household_size", 1)))
        self._notes = tk.StringVar(value=d.get("notes", ""))
        self._waiver = tk.IntVar(value=int(d.get("waiver_signed") or 0))
        self._locker_waiver = tk.IntVar(value=int(d.get("locker_waiver_signed") or 0))

        _field("First Name", self._fn, 0, "e.g. Jane")
        _field("Last Name", self._ln, 1, "e.g. Doe")
        _field("Student ID  (optional)", self._sid, 2, "e.g. 900123456")
        _field("Email  (optional)", self._em, 3, "e.g. jdoe@university.edu")
        _field("Phone  (optional)", self._ph, 4, "e.g. 555-123-4567")
        _field("Semester", self._sem, 5, "e.g. Fall 2026")

        ctk.CTkLabel(
            form, text="Enrollment Status",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=12, column=0, sticky="w", pady=(10, 3))
        ctk.CTkOptionMenu(
            form, variable=self._status,
            values=["full_time", "part_time"],
            height=38, corner_radius=8,
            fg_color=BG_ELEVATED, button_color=BG_HOVER,
            text_color=TEXT_PRIMARY,
        ).grid(row=13, column=0, sticky="ew")

        ctk.CTkLabel(
            form, text="Household Size",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=14, column=0, sticky="w", pady=(10, 3))
        ctk.CTkEntry(
            form, textvariable=self._hh, height=38,
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=15, column=0, sticky="ew")

        ctk.CTkLabel(
            form, text="Notes  (optional)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=16, column=0, sticky="w", pady=(10, 3))
        ctk.CTkEntry(
            form, textvariable=self._notes, height=38,
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=17, column=0, sticky="ew")

        ctk.CTkCheckBox(
            form, text="Waiver signed",
            variable=self._waiver,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            border_color=BORDER_COLOR, corner_radius=6,
        ).grid(row=18, column=0, sticky="w", pady=(18, 4))

        ctk.CTkCheckBox(
            form, text="Locker waiver signed",
            variable=self._locker_waiver,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_PRIMARY,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            border_color=BORDER_COLOR, corner_radius=6,
        ).grid(row=19, column=0, sticky="w", pady=(0, 4))

        self._err_var = tk.StringVar()
        ctk.CTkLabel(
            self, textvariable=self._err_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=ACCENT_RED,
        ).grid(row=3, column=0, sticky="w", padx=28, pady=(8, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=28, pady=(20, 24))
        ctk.CTkButton(
            btn_row, text="Save" if self._edit_mode else "Add Client",
            height=42, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._submit,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_row, text="Cancel",
            height=42, corner_radius=10,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            command=self.destroy,
        ).pack(side="left")

    def _submit(self):
        first_name = self._fn.get().strip()
        last_name  = self._ln.get().strip()
        if not first_name or not last_name:
            self._err_var.set("First and last name are required.")
            return
        try:
            household_size = max(1, int(self._hh.get().strip() or 1))
        except ValueError:
            self._err_var.set("Household size must be a whole number.")
            return

        kwargs = dict(
            student_id=self._sid.get().strip(),
            email=self._em.get().strip(),
            phone=self._ph.get().strip(),
            semester=self._sem.get().strip(),
            enrollment_status=self._status.get(),
            household_size=household_size,
            notes=self._notes.get().strip(),
            waiver_signed=self._waiver.get(),
            locker_waiver_signed=self._locker_waiver.get(),
        )

        if self._edit_mode:
            self.db.update_pantry_client(
                self.client_data["id"], first_name, last_name, **kwargs)
        else:
            self.db.create_pantry_client(first_name, last_name, **kwargs)

        if self.on_save:
            self.on_save()
        self.destroy()


# ---------------------------------------------------------------------------
# Record Visit Modal
# ---------------------------------------------------------------------------

class _VisitModal(ctk.CTkToplevel):
    def __init__(self, parent, db, client: dict, username: str, on_save=None):
        super().__init__(parent)
        self.db       = db
        self.client   = client
        self.username = username
        self.on_save  = on_save

        self.title("Record Visit")
        self.geometry("420x360")
        self.minsize(400, 340)
        self.resizable(False, False)
        self.after(50, self._deferred_init)

    def _deferred_init(self):
        self.configure(fg_color=BG_SURFACE)
        self._build()
        self.update_idletasks()
        self.lift()
        self.focus_force()
        self.grab_set()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text=f"Record Visit",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=28, pady=(24, 2))
        ctk.CTkLabel(
            self,
            text=f"{self.client['first_name']} {self.client['last_name']}  "
                 f"({'Full-time' if self.client['enrollment_status']=='full_time' else 'Part-time'})",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 18))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=28)
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form, text="Pounds of Food Received",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=0, column=0, sticky="w", pady=(0, 3))
        self._lbs = tk.StringVar()
        ctk.CTkEntry(
            form, textvariable=self._lbs, placeholder_text="e.g. 12.5",
            height=38, fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
            corner_radius=8,
        ).grid(row=1, column=0, sticky="ew")

        ctk.CTkLabel(
            form, text="Notes  (optional)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).grid(row=2, column=0, sticky="w", pady=(14, 3))
        self._notes = tk.StringVar()
        ctk.CTkEntry(
            form, textvariable=self._notes, height=38,
            fg_color=BG_ELEVATED, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=3, column=0, sticky="ew")

        self._err_var = tk.StringVar()
        ctk.CTkLabel(
            self, textvariable=self._err_var,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=ACCENT_RED,
        ).grid(row=3, column=0, sticky="w", padx=28, pady=(8, 0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=28, pady=(20, 24))
        ctk.CTkButton(
            btn_row, text="Record Visit",
            height=42, corner_radius=10,
            fg_color=ACCENT_GREEN, hover_color="#16a34a",
            text_color="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._submit,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_row, text="Cancel",
            height=42, corner_radius=10,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_width=1, border_color=BORDER_COLOR,
            command=self.destroy,
        ).pack(side="left")

    def _submit(self):
        try:
            lbs = float(self._lbs.get().strip())
            if lbs < 0:
                raise ValueError
        except ValueError:
            self._err_var.set("Enter a valid, non-negative number of pounds.")
            return

        # ── Weekly limit check ──
        status = self.client["enrollment_status"]
        limit_key = ("pantry_limit_full_time_per_week" if status == "full_time"
                     else "pantry_limit_part_time_per_week")
        default = (_DEFAULT_LIMIT_FULL_TIME if status == "full_time"
                   else _DEFAULT_LIMIT_PART_TIME)
        try:
            limit = int(self.db.get_app_setting(limit_key, default))
        except (TypeError, ValueError):
            limit = int(default)

        visits_this_week = self.db.get_visit_count_since(
            self.client["id"], _week_start_iso())

        if visits_this_week >= limit:
            status_label = "full-time" if status == "full_time" else "part-time"
            if not messagebox.askyesno(
                "Weekly Limit Reached",
                f"{self.client['first_name']} {self.client['last_name']} has "
                f"already visited {visits_this_week} time(s) this week "
                f"(limit: {limit} for {status_label} students).\n\n"
                "Record this visit anyway?",
                icon="warning",
            ):
                return

        self.db.record_pantry_visit(
            self.client["id"], lbs, self.username, self._notes.get().strip())
        if self.on_save:
            self.on_save()
        self.destroy()


# ---------------------------------------------------------------------------
# Main ClientManagement frame
# ---------------------------------------------------------------------------

class ClientManagement(ctk.CTkFrame):
    def __init__(self, parent, db, user: dict = None, embedded=False):
        super().__init__(parent, fg_color=BG_SURFACE)
        self.db        = db
        self.user      = user or {}
        self._is_admin = self.user.get("role") == "admin"
        self._build()
        self._load_clients()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=40, pady=(28, 0))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="Clients",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            hdr, text="Student profiles, visit history, and pantry limits",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w")

        ctk.CTkButton(
            hdr, text="+ Add Client", height=38, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._open_create,
        ).grid(row=0, column=2, sticky="e")

        # Tab bar
        tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        tab_bar.grid(row=1, column=0, sticky="ew", padx=40, pady=(16, 0))
        self._tab_btns: dict = {}
        self._active_tab = tk.StringVar(value="clients")

        tabs = [("clients", "Clients"), ("visits", "Visit History")]
        if self._is_admin:
            tabs.append(("limits", "Pantry Limits"))

        for key, label in tabs:
            b = ctk.CTkButton(
                tab_bar, text=label, width=140, height=34, corner_radius=8,
                fg_color=BG_ELEVATED if key == "clients" else "transparent",
                hover_color=BG_ELEVATED,
                text_color=TEXT_PRIMARY if key == "clients" else TEXT_MUTED,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                command=lambda k=key: self._switch_tab(k),
            )
            b.pack(side="left", padx=(0, 4))
            self._tab_btns[key] = b

        # Panels
        self._clients_panel = self._build_clients_panel()
        self._clients_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=8)

        self._visits_panel = self._build_visits_panel()
        self._visits_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=8)
        self._visits_panel.grid_remove()

        if self._is_admin:
            self._limits_panel = self._build_limits_panel()
            self._limits_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=8)
            self._limits_panel.grid_remove()

    def _build_clients_panel(self):
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Search + actions
        toolbar = ctk.CTkFrame(panel, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=40, pady=(0, 8))

        self.search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(
            toolbar, textvariable=self.search_var, width=220, height=36,
            placeholder_text="Search by name, student ID, or email…",
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        )
        search_entry.pack(side="left", padx=(0, 6))
        search_entry.bind("<Return>", lambda _e: self._load_clients())

        ctk.CTkButton(
            toolbar, text="Search", width=80, height=36, corner_radius=8,
            fg_color=ACCENT_GOLD, hover_color=BG_HOVER,
            text_color="#1B1F24", command=self._load_clients,
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            toolbar, text="Record Visit", height=36, width=120, corner_radius=8,
            fg_color=ACCENT_GREEN, hover_color="#16a34a",
            text_color="white", command=self._open_record_visit,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            toolbar, text="View History", height=36, width=110, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_PRIMARY, border_width=1, border_color=BORDER_COLOR,
            command=self._open_client_history,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            toolbar, text="Edit", height=36, width=80, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_PRIMARY, border_width=1, border_color=BORDER_COLOR,
            command=self._open_edit,
        ).pack(side="left", padx=(0, 6))
        self._toggle_btn = ctk.CTkButton(
            toolbar, text="Deactivate", height=36, width=100, corner_radius=8,
            fg_color=BG_SECONDARY, hover_color=ACCENT_RED,
            text_color=TEXT_MUTED, command=self._toggle_active,
        )
        self._toggle_btn.pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            toolbar, text="Archive", height=36, width=80, corner_radius=8,
            fg_color=ACCENT_RED, hover_color="#b91c1c",
            text_color="white", command=self._archive_client,
        ).pack(side="left")

        # Treeview card
        card = ctk.CTkFrame(
            panel, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        card.grid(row=1, column=0, sticky="nsew", padx=40, pady=(0, 8))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        try:
            style = ttk.Style()
            style.configure("Clients.Treeview",
                rowheight=28, font=(FONT_FAMILY, 10),
                background=BG_ELEVATED, fieldbackground=BG_ELEVATED,
                foreground=TEXT_PRIMARY, borderwidth=0)
            style.configure("Clients.Treeview.Heading",
                font=(FONT_FAMILY, 10, "bold"),
                background=BG_ELEVATED, foreground=ACCENT_GOLD,
                relief="flat", padding=6)
            style.map("Clients.Treeview",
                background=[("selected", ACCENT)],
                foreground=[("selected", "white")])
        except Exception:
            pass

        cols = ("name", "student_id", "semester", "status", "household",
                "visits_week", "total_visits", "total_lbs", "last_visit",
                "waivers", "active")
        self.tree = ttk.Treeview(
            card, columns=cols, show="headings", style="Clients.Treeview")
        for col, heading, width in [
            ("name",         "Name",         160),
            ("student_id",   "Student ID",   100),
            ("semester",     "Semester",     110),
            ("status",       "Status",        90),
            ("household",    "Household",     80),
            ("visits_week",  "This Week",     80),
            ("total_visits", "Total Visits",  90),
            ("total_lbs",    "Total Lbs",     90),
            ("last_visit",   "Last Visit",   150),
            ("waivers",      "Waivers",       80),
            ("active",       "Active",        70),
        ]:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=50)

        self.tree.tag_configure("inactive", foreground=TEXT_MUTED)
        self.tree.tag_configure("full_time", foreground="#93c5fd")
        self.tree.tag_configure("part_time", foreground="#fbbf24")

        vsb = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        return panel

    def _build_visits_panel(self):
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(
            panel, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        card.grid(row=0, column=0, sticky="nsew", padx=40, pady=(0, 12))
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        try:
            style = ttk.Style()
            style.configure("Visits.Treeview",
                rowheight=28, font=(FONT_FAMILY, 10),
                background=BG_ELEVATED, fieldbackground=BG_ELEVATED,
                foreground=TEXT_PRIMARY, borderwidth=0)
            style.configure("Visits.Treeview.Heading",
                font=(FONT_FAMILY, 10, "bold"),
                background=BG_ELEVATED, foreground=ACCENT_GOLD,
                relief="flat", padding=6)
            style.map("Visits.Treeview",
                background=[("selected", ACCENT)],
                foreground=[("selected", "white")])
        except Exception:
            pass

        cols = ("visit_date", "name", "status", "pounds", "recorded_by", "notes")
        self.visits_tree = ttk.Treeview(
            card, columns=cols, show="headings", style="Visits.Treeview")
        for col, heading, width in [
            ("visit_date",  "Timestamp",   160),
            ("name",        "Client",      160),
            ("status",      "Status",       90),
            ("pounds",      "Lbs",           70),
            ("recorded_by", "Recorded By",  110),
            ("notes",       "Notes",        220),
        ]:
            self.visits_tree.heading(col, text=heading)
            self.visits_tree.column(col, width=width, minwidth=50)

        vsb = ttk.Scrollbar(card, orient="vertical", command=self.visits_tree.yview)
        self.visits_tree.configure(yscrollcommand=vsb.set)
        self.visits_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        return panel

    def _build_limits_panel(self):
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(
            panel, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        card.grid(row=0, column=0, sticky="new", padx=40, pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Weekly Visit Limits",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 2))
        ctk.CTkLabel(
            card,
            text="Admin only. Staff recording a visit past this limit will "
                 "see a warning and can choose to override it.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 16))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            form, text="Full-time students (visits / week):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY,
        ).grid(row=0, column=0, sticky="w", pady=(0, 10), padx=(0, 12))
        self._ft_limit = tk.StringVar(value=self.db.get_app_setting(
            "pantry_limit_full_time_per_week", _DEFAULT_LIMIT_FULL_TIME))
        ctk.CTkEntry(
            form, textvariable=self._ft_limit, width=80, height=34,
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=0, column=1, pady=(0, 10))

        ctk.CTkLabel(
            form, text="Part-time students (visits / week):",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY,
        ).grid(row=1, column=0, sticky="w", padx=(0, 12))
        self._pt_limit = tk.StringVar(value=self.db.get_app_setting(
            "pantry_limit_part_time_per_week", _DEFAULT_LIMIT_PART_TIME))
        ctk.CTkEntry(
            form, textvariable=self._pt_limit, width=80, height=34,
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).grid(row=1, column=1)

        ctk.CTkButton(
            card, text="Save Limits", height=38, width=130, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="white",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._save_limits,
        ).grid(row=3, column=0, sticky="w", padx=20, pady=(0, 20))

        return panel

    # ------------------------------------------------------------------
    # Tab switching
    # ------------------------------------------------------------------

    def _switch_tab(self, key: str):
        self._active_tab.set(key)
        for k, btn in self._tab_btns.items():
            if k == key:
                btn.configure(fg_color=BG_ELEVATED, text_color=TEXT_PRIMARY)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_MUTED)

        self._clients_panel.grid_remove()
        self._visits_panel.grid_remove()
        if self._is_admin:
            self._limits_panel.grid_remove()

        if key == "clients":
            self._clients_panel.grid()
        elif key == "visits":
            self._visits_panel.grid()
            self._load_visits()
        elif key == "limits" and self._is_admin:
            self._limits_panel.grid()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def on_shown(self):
        self._load_clients()

    def _load_clients(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        search = getattr(self, "search_var", None)
        search_text = search.get().strip() if search else ""
        clients = self.db.get_all_pantry_clients(search_text)
        week_start = _week_start_iso()
        for c in clients:
            stats = self.db.get_client_visit_stats(c["id"])
            visits_week = self.db.get_visit_count_since(c["id"], week_start)
            tags = ["inactive"] if not c["is_active"] else [c["enrollment_status"]]
            status_label = "Full-time" if c["enrollment_status"] == "full_time" else "Part-time"
            waivers = []
            if c.get("waiver_signed"):
                waivers.append("W")
            if c.get("locker_waiver_signed"):
                waivers.append("L")
            waivers_str = ", ".join(waivers) or "—"
            self.tree.insert(
                "", "end", iid=str(c["id"]), tags=tags,
                values=(
                    f"{c['first_name']} {c['last_name']}",
                    c.get("student_id") or "—",
                    c.get("semester") or "—",
                    status_label,
                    c.get("household_size", 1),
                    visits_week,
                    stats["total_visits"],
                    round(stats["total_pounds"] or 0, 1),
                    (stats["last_visit"] or "Never")[:16],
                    waivers_str,
                    "Yes" if c["is_active"] else "No",
                ),
            )

    def _load_visits(self):
        for r in self.visits_tree.get_children():
            self.visits_tree.delete(r)
        for v in self.db.get_recent_pantry_visits(200):
            status_label = "Full-time" if v["enrollment_status"] == "full_time" else "Part-time"
            self.visits_tree.insert("", "end", values=(
                v["visit_date"], f"{v['first_name']} {v['last_name']}",
                status_label, v["pounds_received"], v["recorded_by"],
                v.get("notes") or "",
            ))

    # ------------------------------------------------------------------
    # Selection helper
    # ------------------------------------------------------------------

    def _selected_client(self):
        sel = self.tree.selection()
        if not sel:
            Toast.show(self, "Select a client first", kind="warning")
            return None
        return self.db.get_pantry_client(int(sel[0]))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_create(self):
        _ClientModal(self, self.db, on_save=self._load_clients)

    def _open_edit(self):
        client = self._selected_client()
        if client is None:
            return
        _ClientModal(self, self.db, client_data=client, on_save=self._load_clients)

    def _open_record_visit(self):
        client = self._selected_client()
        if client is None:
            return
        username = self.user.get("username", "")
        _VisitModal(self, self.db, client, username, on_save=self._load_clients)

    def _open_client_history(self):
        client = self._selected_client()
        if client is None:
            return
        _ClientHistoryModal(self, self.db, client)

    def _toggle_active(self):
        client = self._selected_client()
        if client is None:
            return
        new_state = not bool(client["is_active"])
        self.db.set_pantry_client_active(client["id"], new_state)
        self._load_clients()
        verb = "Reactivated" if new_state else "Deactivated"
        Toast.show(self, f"{verb} {client['first_name']} {client['last_name']}",
                   kind="success")

    def _archive_client(self):
        client = self._selected_client()
        if client is None:
            return
        name = f"{client['first_name']} {client['last_name']}"
        if messagebox.askyesno(
            "Confirm Archive",
            f"Archive client '{name}'?\n\nThey will be removed from active clients "
            "and can be restored from the Archive Manager.",
        ):
            self.db.archive_pantry_client(
                client["id"], archived_by=self.user.get("username", ""))
            self._load_clients()
            Toast.show(self, f"Archived '{name}'", kind="success")

    def _save_limits(self):
        try:
            ft = int(self._ft_limit.get().strip())
            pt = int(self._pt_limit.get().strip())
            if ft < 0 or pt < 0:
                raise ValueError
        except ValueError:
            Toast.show(self, "Limits must be non-negative whole numbers", kind="warning")
            return
        self.db.set_app_setting("pantry_limit_full_time_per_week", str(ft))
        self.db.set_app_setting("pantry_limit_part_time_per_week", str(pt))
        Toast.show(self, "Pantry limits updated", kind="success")


# ---------------------------------------------------------------------------
# Client visit history modal
# ---------------------------------------------------------------------------

class _ClientHistoryModal(ctk.CTkToplevel):
    def __init__(self, parent, db, client: dict):
        super().__init__(parent)
        self.db = db
        self.client = client
        self.title(f"Visit History — {client['first_name']} {client['last_name']}")
        self.geometry("560x460")
        self.minsize(480, 400)
        self.after(50, self._deferred_init)

    def _deferred_init(self):
        self.configure(fg_color=BG_SURFACE)
        self._build()
        self.update_idletasks()
        self.lift()
        self.focus_force()
        self.grab_set()

    def _build(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        stats = self.db.get_client_visit_stats(self.client["id"])
        ctk.CTkLabel(
            self,
            text=f"{self.client['first_name']} {self.client['last_name']}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 0))

        ctk.CTkLabel(
            self,
            text=f"{stats['total_visits']} total visit(s)  ·  "
                 f"{round(stats['total_pounds'] or 0, 1)} lbs total  ·  "
                 f"Last visit: {(stats['last_visit'] or 'Never')[:16]}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(4, 0))

        card = ctk.CTkFrame(
            self, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        card.grid(row=2, column=0, sticky="nsew", padx=24, pady=16)
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        cols = ("visit_date", "pounds", "recorded_by", "notes")
        tree = ttk.Treeview(card, columns=cols, show="headings")
        for col, heading, width in [
            ("visit_date",  "Timestamp",   160),
            ("pounds",      "Lbs",          70),
            ("recorded_by", "Recorded By", 120),
            ("notes",       "Notes",       200),
        ]:
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=50)

        vsb = ttk.Scrollbar(card, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        for v in self.db.get_client_visits(self.client["id"]):
            tree.insert("", "end", values=(
                v["visit_date"], v["pounds_received"],
                v["recorded_by"], v.get("notes") or ""))

        ctk.CTkButton(
            self, text="Close", height=38, width=100, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, border_width=1, border_color=BORDER_COLOR,
            command=self.destroy,
        ).grid(row=3, column=0, sticky="w", padx=24, pady=(0, 20))
