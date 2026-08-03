import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from theme import (
    BG_PRIMARY, BG_SECONDARY, BG_CARD, BG_HOVER,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED, ACCENT_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, FONT_FAMILY, BORDER_COLOR,
)
from toast import Toast


class TransactionHistory(ctk.CTkFrame):
    def __init__(self, parent, db, embedded=False):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.db = db
        self._build()
        self.load()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ---- title ----
        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 2))
        ctk.CTkLabel(
            title_row, text="Transaction History",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            self,
            text="Narrow results by keyword, scan type, date range, or "
                 "recipient — then click Filter to apply.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 10))

        # ---- filter bar ----
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))

        def _field(label_text):
            """A small vertical group: caption label above the widget."""
            box = ctk.CTkFrame(f, fg_color="transparent")
            box.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                box, text=label_text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                text_color=TEXT_MUTED,
            ).pack(anchor="w", pady=(0, 3))
            return box

        search_box = _field("SEARCH ITEM / BARCODE")
        self.search_var = tk.StringVar()
        ctk.CTkEntry(
            search_box, textvariable=self.search_var, width=170, height=36,
            placeholder_text="e.g. Toothpaste or 123142",
            placeholder_text_color=TEXT_MUTED,
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack()

        type_box = _field("TYPE")
        self.type_var = tk.StringVar(value="All")
        ctk.CTkOptionMenu(
            type_box, variable=self.type_var,
            values=["All", "SCAN_IN", "SCAN_OUT"],
            width=120, height=36, corner_radius=8,
            fg_color=BG_SECONDARY, button_color=BG_HOVER,
            text_color=TEXT_PRIMARY,
        ).pack()

        from_box = _field("FROM DATE")
        self.from_var = tk.StringVar()
        ctk.CTkEntry(
            from_box, textvariable=self.from_var, width=110, height=36,
            placeholder_text="YYYY-MM-DD",
            placeholder_text_color=TEXT_MUTED,
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack()

        to_box = _field("TO DATE")
        self.to_var = tk.StringVar()
        ctk.CTkEntry(
            to_box, textvariable=self.to_var, width=110, height=36,
            placeholder_text="YYYY-MM-DD",
            placeholder_text_color=TEXT_MUTED,
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack()

        recip_box = _field("RECIPIENT")
        self.recip_var = tk.StringVar()
        ctk.CTkEntry(
            recip_box, textvariable=self.recip_var, width=120, height=36,
            placeholder_text="e.g. mom, dad",
            placeholder_text_color=TEXT_MUTED,
            fg_color=BG_SECONDARY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8,
        ).pack()

        btn_box = ctk.CTkFrame(f, fg_color="transparent")
        btn_box.pack(side="left", padx=(4, 0), pady=(15, 0))
        ctk.CTkButton(
            btn_box, text="Filter", width=72, height=36, corner_radius=8,
            fg_color=ACCENT_GOLD, hover_color=BG_HOVER,
            text_color="#1B1F24", command=self.load,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            btn_box, text="Clear", width=60, height=36, corner_radius=8,
            fg_color=BG_SECONDARY, hover_color=BG_CARD,
            text_color=TEXT_MUTED, command=self._clear_filters,
        ).pack(side="left")

        export_box = ctk.CTkFrame(f, fg_color="transparent")
        export_box.pack(side="right", pady=(15, 0))
        ctk.CTkButton(
            export_box, text="Export Excel", width=110, height=36, corner_radius=8,
            fg_color=ACCENT_BLUE, hover_color="#1d4ed8",
            text_color="white", command=self.export_excel,
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            export_box, text="Export CSV", width=100, height=36, corner_radius=8,
            fg_color=ACCENT_GREEN, hover_color="#16a34a",
            text_color="white", command=self.export_csv,
        ).pack(side="right", padx=(0, 6))

        # ---- treeview ----
        tf = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        tf.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 8))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        try:
            style = ttk.Style()
            style.configure("Hist.Treeview",
                rowheight=28, font=(FONT_FAMILY, 10),
                background=BG_SECONDARY, fieldbackground=BG_SECONDARY,
                foreground=TEXT_PRIMARY, borderwidth=0)
            style.configure("Hist.Treeview.Heading",
                font=(FONT_FAMILY, 10, "bold"),
                background=BG_CARD, foreground=ACCENT_GOLD,
                relief="flat", padding=6)
            style.map("Hist.Treeview",
                background=[("selected", ACCENT_BLUE)],
                foreground=[("selected", "white")])
        except Exception:
            pass

        cols = ("id", "timestamp", "type", "barcode", "item_name",
                "category", "qty", "recipient", "user", "notes")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings",
                                 style="Hist.Treeview")

        col_defs = [
            ("id",        "ID",         40),
            ("timestamp", "Timestamp", 140),
            ("type",      "Type",       90),
            ("barcode",   "Barcode",   110),
            ("item_name", "Item Name", 170),
            ("category",  "Category",  100),
            ("qty",       "Qty",        50),
            ("recipient", "Recipient", 130),
            ("user",      "User",       90),
            ("notes",     "Notes",     120),
        ]
        for col, heading, width in col_defs:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, minwidth=40)

        self.tree.tag_configure("in",  background="#152c1f", foreground="#86efac")
        self.tree.tag_configure("out", background="#2c1515", foreground="#fca5a5")

        vsb = ttk.Scrollbar(tf, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.count_lbl = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        )
        self.count_lbl.grid(row=4, column=0, pady=(0, 10))

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def on_shown(self):
        self.load()

    def load(self):
        search    = self.search_var.get().strip()
        ttype     = self.type_var.get() if self.type_var.get() != "All" else ""
        date_from = self.from_var.get().strip()
        date_to   = self.to_var.get().strip()
        recipient = self.recip_var.get().strip()

        rows = self.db.get_transactions(search, ttype, date_from, date_to, recipient)

        for r in self.tree.get_children():
            self.tree.delete(r)

        for t in rows:
            tag = "in" if t["transaction_type"] == "SCAN_IN" else "out"
            self.tree.insert("", "end", tags=(tag,), values=(
                t["id"], t["timestamp"], t["transaction_type"],
                t["barcode"], t["item_name"], t["category"],
                t["quantity"], t["recipient"], t["username"], t["notes"],
            ))

        self.count_lbl.configure(text=f"{len(rows)} transaction(s)")

    def _clear_filters(self):
        for var in (self.search_var, self.from_var, self.to_var, self.recip_var):
            var.set("")
        self.type_var.set("All")
        self.load()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    HEADERS = ["ID", "Timestamp", "Type", "Barcode", "Item Name",
               "Category", "Qty", "Recipient", "User", "Notes"]

    def _rows(self):
        return [self.tree.item(r)["values"] for r in self.tree.get_children()]

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="transaction_history.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(self.HEADERS)
            w.writerows(self._rows())
        Toast.show(self, f"CSV saved: {path}", kind="success")

    def export_excel(self):
        try:
            import openpyxl
            from openpyxl.styles import Font
        except ImportError:
            messagebox.showerror(
                "Missing Library",
                "openpyxl is not installed.\nRun:  pip install openpyxl",
            )
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="transaction_history.xlsx",
        )
        if not path:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"
        ws.append(self.HEADERS)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in self._rows():
            ws.append(list(row))
        wb.save(path)
        Toast.show(self, f"Excel saved: {path}", kind="success")
