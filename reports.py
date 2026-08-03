import csv
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from theme import (
    BG_PRIMARY, BG_SECONDARY, BG_CARD, BG_HOVER,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, FONT_FAMILY, BORDER_COLOR,
)
from toast import Toast


class Reports(ctk.CTkFrame):
    def __init__(self, parent, db, embedded=False):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.db = db
        self._headers = []
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ---- sidebar ----
        side = ctk.CTkFrame(
            self, width=210, fg_color=BG_SECONDARY, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            side, text="Reports",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(pady=(24, 16), padx=16, anchor="w")

        report_defs = [
            ("▤  Current Inventory",  self._rpt_inventory),
            ("⚠  Low Stock",          self._rpt_low_stock),
            ("✕  Out of Stock",       self._rpt_out_of_stock),
            ("↓  Scan In History",    lambda: self._rpt_transactions("SCAN_IN")),
            ("↑  Scan Out History",   lambda: self._rpt_transactions("SCAN_OUT")),
            ("◯  Recipient History",  self._rpt_recipients),
        ]
        for label, cmd in report_defs:
            ctk.CTkButton(
                side, text=label, width=186, height=40,
                anchor="w", corner_radius=8,
                fg_color="transparent", hover_color=BG_CARD,
                text_color=TEXT_SECONDARY,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                command=cmd,
            ).pack(pady=2, padx=12)

        ctk.CTkFrame(side, height=1, fg_color=BORDER_COLOR).pack(
            fill="x", padx=12, pady=16)

        ctk.CTkButton(
            side, text="Export CSV", width=186, height=38, corner_radius=8,
            fg_color=ACCENT_GREEN, hover_color="#16a34a",
            text_color="white", command=self.export_csv,
        ).pack(pady=3, padx=12)
        ctk.CTkButton(
            side, text="Export Excel", width=186, height=38, corner_radius=8,
            fg_color=ACCENT_BLUE, hover_color="#1d4ed8",
            text_color="white", command=self.export_excel,
        ).pack(pady=3, padx=12)

        # ---- main area ----
        main = ctk.CTkFrame(self, fg_color=BG_PRIMARY)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(
            main, text="← Select a report",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        )
        self.title_lbl.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 12))

        # ---- treeview ----
        tf = ctk.CTkFrame(main, fg_color=BG_CARD, corner_radius=12)
        tf.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 8))
        tf.grid_rowconfigure(0, weight=1)
        tf.grid_columnconfigure(0, weight=1)

        try:
            style = ttk.Style()
            style.configure("Rpt.Treeview",
                rowheight=28, font=(FONT_FAMILY, 10),
                background=BG_SECONDARY, fieldbackground=BG_SECONDARY,
                foreground=TEXT_PRIMARY, borderwidth=0)
            style.configure("Rpt.Treeview.Heading",
                font=(FONT_FAMILY, 10, "bold"),
                background=BG_CARD, foreground=ACCENT_GOLD,
                relief="flat", padding=6)
            style.map("Rpt.Treeview",
                background=[("selected", ACCENT_BLUE)],
                foreground=[("selected", "white")])
        except Exception:
            pass

        self.tree = ttk.Treeview(tf, show="headings", style="Rpt.Treeview")
        self.tree.tag_configure("low", background="#3b2f0e", foreground="#fcd34d")
        self.tree.tag_configure("out", background="#3b1515", foreground="#fca5a5")

        vsb = ttk.Scrollbar(tf, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.count_lbl = ctk.CTkLabel(
            main, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED, anchor="e",
        )
        self.count_lbl.grid(row=2, column=0, sticky="e", padx=24, pady=(0, 12))

    # ------------------------------------------------------------------
    # Tree helpers
    # ------------------------------------------------------------------

    def _setup_cols(self, headers: list, widths: list = None):
        self._headers = headers
        self.tree["columns"] = headers
        for i, h in enumerate(headers):
            w = widths[i] if widths and i < len(widths) else 120
            self.tree.heading(h, text=h)
            self.tree.column(h, width=w, minwidth=50)
        for r in self.tree.get_children():
            self.tree.delete(r)

    def _fill(self, rows: list, tag_fn=None):
        for row in rows:
            tag = tag_fn(row) if tag_fn else ""
            self.tree.insert("", "end", values=row,
                             tags=(tag,) if tag else ())
        self.count_lbl.configure(text=f"{len(rows)} row(s)")

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def _rpt_inventory(self):
        self.title_lbl.configure(text="Current Inventory")
        hdrs   = ["Barcode", "Item Name", "Category", "Current Qty", "Min Stock", "Status", "Notes"]
        widths = [120, 200, 120, 90, 80, 100, 160]
        self._setup_cols(hdrs, widths)

        def tag(row):
            qty = int(row[3]) if str(row[3]).isdigit() else 0
            mins = int(row[4]) if str(row[4]).isdigit() else 0
            if qty == 0:   return "out"
            if qty <= mins: return "low"
            return ""

        items = self.db.get_all_items()
        rows  = []
        for i in items:
            qty = i["current_quantity"]; mins = i["minimum_stock"]
            if qty == 0:        status = "OUT OF STOCK"
            elif qty <= mins:   status = "LOW STOCK"
            else:               status = "OK"
            rows.append((i["barcode"], i["item_name"], i["category"],
                         qty, mins, status, i["notes"]))
        self._fill(rows, tag)

    def _rpt_low_stock(self):
        self.title_lbl.configure(text="Low Stock Items")
        hdrs   = ["Barcode", "Item Name", "Category", "Current Qty", "Min Stock", "Notes"]
        widths = [120, 210, 120, 90, 80, 180]
        self._setup_cols(hdrs, widths)
        items = self.db.get_low_stock_items()
        rows  = [(i["barcode"], i["item_name"], i["category"],
                  i["current_quantity"], i["minimum_stock"], i["notes"])
                 for i in items]
        self._fill(rows, lambda _r: "low")

    def _rpt_out_of_stock(self):
        self.title_lbl.configure(text="Out of Stock Items")
        hdrs   = ["Barcode", "Item Name", "Category", "Min Stock", "Notes"]
        widths = [120, 210, 120, 80, 200]
        self._setup_cols(hdrs, widths)
        items = self.db.get_out_of_stock_items()
        rows  = [(i["barcode"], i["item_name"], i["category"],
                  i["minimum_stock"], i["notes"])
                 for i in items]
        self._fill(rows, lambda _r: "out")

    def _rpt_transactions(self, ttype: str):
        label = "Scan In History" if ttype == "SCAN_IN" else "Scan Out History"
        self.title_lbl.configure(text=label)
        hdrs   = ["Timestamp", "Barcode", "Item Name", "Category", "Qty", "Recipient", "User"]
        widths = [140, 110, 190, 110, 50, 140, 90]
        self._setup_cols(hdrs, widths)
        txns = self.db.get_transactions(trans_type=ttype)
        rows = [(t["timestamp"], t["barcode"], t["item_name"], t["category"],
                 t["quantity"], t["recipient"], t["username"])
                for t in txns]
        self._fill(rows)

    def _rpt_recipients(self):
        self.title_lbl.configure(text="Recipient Giveaway History")
        hdrs   = ["Timestamp", "Recipient", "Barcode", "Item Name", "Category", "Qty", "User"]
        widths = [140, 140, 110, 190, 110, 50, 90]
        self._setup_cols(hdrs, widths)
        txns = self.db.get_transactions(trans_type="SCAN_OUT")
        rows = [(t["timestamp"], t["recipient"], t["barcode"], t["item_name"],
                 t["category"], t["quantity"], t["username"])
                for t in txns]
        self._fill(rows)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _tree_rows(self):
        return [self.tree.item(r)["values"] for r in self.tree.get_children()]

    def export_csv(self):
        if not self._headers:
            messagebox.showwarning("No Report", "Please select a report first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="report.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(self._headers)
            w.writerows(self._tree_rows())
        Toast.show(self, f"CSV saved: {path}", kind="success")

    def export_excel(self):
        if not self._headers:
            Toast.show(self, "Select a report first", kind="warning")
            return
        try:
            import openpyxl
            from openpyxl.styles import Font
        except ImportError:
            messagebox.showerror("Missing Library", "Run:  pip install openpyxl")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="report.xlsx",
        )
        if not path:
            return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(self._headers)
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for row in self._tree_rows():
            ws.append(list(row))
        wb.save(path)
        Toast.show(self, f"Excel saved: {path}", kind="success")
