"""scan_screen.py — AI-first scanning workflow.

Workflow:
  Scan barcode
    → found in DB        → show enriched item card (velocity, expiration) → Scan In / Out
    → not in DB          → query Open Food Facts in background
        → product found  → AI Confirm card (pre-filled) → Confirm & Add
        → not found      → manual add prompt
"""

import datetime
import threading
import tkinter as tk

import customtkinter as ctk

from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_OVERLAY, BG_HOVER,
    ACCENT, ACCENT_HOVER, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
    GREEN_DIM, RED_DIM, AMBER_DIM,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
    BG_PRIMARY, BG_SECONDARY, BG_CARD,
)
from toast import Toast


class ScanScreen(ctk.CTkFrame):
    def __init__(self, parent, db, user):
        super().__init__(parent, fg_color=BG_SURFACE)
        self.db = db
        self.user = user
        self._lookup_timer  = None
        self._current_item  = None
        self._current_direction = None
        self._pending_barcode  = None
        self._pending_product  = None
        self._storage_var   = None
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        wrap = ctk.CTkFrame(scroll, fg_color="transparent")
        wrap.grid(row=0, column=0, sticky="ew", padx=40, pady=28)
        wrap.grid_columnconfigure(0, weight=1)

        self._build_header(wrap)
        self._build_input(wrap)
        self._build_state_area(wrap)
        self._build_controls(wrap)
        self._build_actions(wrap)
        self._build_recent(wrap)

        self.after(200, self._bind_keys)

    def _bind_keys(self):
        try:
            root = self.winfo_toplevel()
            root.bind("<F1>", lambda _e: self.scan_in())
            root.bind("<F2>", lambda _e: self.scan_out())
            root.bind("<Escape>", lambda _e: self.clear_form())
        except Exception:
            pass

    def _build_header(self, p):
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            row, text="Smart Scanner",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            row, text="AI identifies unknown products automatically",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, sticky="w")
        ctk.CTkLabel(
            row, text="F1 Scan In   F2 Scan Out   Esc Clear",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=2, sticky="e")

    def _build_input(self, p):
        self.barcode_var = tk.StringVar()
        self.barcode_var.trace_add("write", self._on_barcode_change)
        frame = ctk.CTkFrame(
            p, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            frame, text="BARCODE",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=20, pady=(14, 4))
        self.barcode_entry = ctk.CTkEntry(
            frame,
            textvariable=self.barcode_var,
            placeholder_text="Scan or type a barcode here…",
            height=52,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16),
            fg_color=BG_OVERLAY,
            border_color=ACCENT,
            border_width=2,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8,
        )
        self.barcode_entry.pack(fill="x", padx=20, pady=(0, 14))
        self.barcode_entry.bind("<Return>", lambda _: self._auto_scan())

    def _build_state_area(self, p):
        self._state_frame = ctk.CTkFrame(p, fg_color="transparent")
        self._state_frame.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        self._state_frame.grid_columnconfigure(0, weight=1)
        self._show_idle()

    # ── state cards ──────────────────────────────────────────────────

    def _clear_state(self):
        for w in self._state_frame.winfo_children():
            w.destroy()
        self._current_item = None
        self._current_direction = None
        self._pending_barcode = None
        self._pending_product = None
        self._storage_var = None

    def _show_idle(self):
        self._clear_state()
        idle = ctk.CTkFrame(
            self._state_frame, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR, height=100,
        )
        idle.grid(row=0, column=0, sticky="ew")
        idle.grid_propagate(False)
        idle.grid_rowconfigure(0, weight=1)
        idle.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            idle, text="Ready to scan  —  point scanner at a barcode or type it above",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0)

    def _show_item_card(self, item: dict, direction: str):
        self._clear_state()
        self._current_item = item
        self._current_direction = direction

        card = ctk.CTkFrame(
            self._state_frame, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # ── left: item details ──
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)
        info.grid_columnconfigure(0, weight=1)

        name_row = ctk.CTkFrame(info, fg_color="transparent")
        name_row.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            name_row, text=item["item_name"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).pack(side="left")
        if item.get("brand"):
            ctk.CTkLabel(
                name_row, text=f"  ·  {item['brand']}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED,
            ).pack(side="left")

        cat_row = ctk.CTkFrame(info, fg_color="transparent")
        cat_row.grid(row=1, column=0, sticky="ew", pady=(2, 8))
        ctk.CTkLabel(
            cat_row, text=item.get("category") or "No category",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED, anchor="w",
        ).pack(side="left")
        if item.get("storage_location"):
            ctk.CTkLabel(
                cat_row,
                text=f"  ·  {item['storage_location']}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=ACCENT_BLUE,
            ).pack(side="left")

        stock = item["current_quantity"]
        min_s = item["minimum_stock"]
        if stock == 0:
            sc, sb, sl = ACCENT_RED,   RED_DIM,   "Out of stock"
        elif stock <= min_s:
            sc, sb, sl = ACCENT_AMBER, AMBER_DIM, "Low stock"
        else:
            sc, sb, sl = ACCENT_GREEN, GREEN_DIM, "In stock"

        sr = ctk.CTkFrame(info, fg_color="transparent")
        sr.grid(row=2, column=0, sticky="w")
        ctk.CTkLabel(
            sr, text=f"{stock} units",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=sc,
        ).pack(side="left", padx=(0, 10))
        bf = ctk.CTkFrame(sr, fg_color=sb, corner_radius=6)
        bf.pack(side="left")
        ctk.CTkLabel(
            bf, text=f"  {sl}  ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=sc,
        ).pack(padx=4, pady=3)

        # ── intelligence row ──
        intel = self._get_item_intelligence(item)
        if intel:
            ir = ctk.CTkFrame(info, fg_color="transparent")
            ir.grid(row=3, column=0, sticky="ew", pady=(8, 0))
            for label, value, color in intel:
                chip = ctk.CTkFrame(ir, fg_color=BG_OVERLAY, corner_radius=6)
                chip.pack(side="left", padx=(0, 8))
                ctk.CTkLabel(
                    chip, text=f"{label}: {value}",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=color,
                ).pack(padx=8, pady=4)

        # ── right: direction badge ──
        if direction == "SCAN_IN":
            dc, db2, dt = ACCENT_GREEN, GREEN_DIM, "⬆  Scan In"
        else:
            dc, db2, dt = ACCENT_RED,   RED_DIM,   "⬇  Scan Out"
        df = ctk.CTkFrame(card, fg_color=db2, corner_radius=8)
        df.grid(row=0, column=1, padx=(0, 20), pady=16, sticky="e")
        ctk.CTkLabel(
            df, text=dt,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=dc,
        ).pack(padx=16, pady=10)

    def _get_item_intelligence(self, item: dict) -> list:
        """Returns [(label, value, color), ...] chips for the item card."""
        chips = []
        try:
            from ai_assistant import _PatternEngine
            pe = _PatternEngine(self.db)
            v = pe.velocity(item["barcode"])
            if v and v > 0:
                weekly = round(v * 7, 1)
                if item["current_quantity"] > 0 and v > 0:
                    days_left = int(item["current_quantity"] / v)
                    color = ACCENT_RED if days_left < 7 else (
                        ACCENT_AMBER if days_left < 14 else ACCENT_GREEN)
                    chips.append(("Days left", str(days_left), color))
                chips.append(("Weekly use", f"{weekly}/wk", TEXT_MUTED))
        except Exception:
            pass

        exp = item.get("expiration_date", "")
        if exp:
            try:
                exp_date = datetime.date.fromisoformat(exp)
                days_to_exp = (exp_date - datetime.date.today()).days
                if days_to_exp < 0:
                    chips.append(("EXPIRED", exp, ACCENT_RED))
                elif days_to_exp <= 14:
                    chips.append(("Expires", f"{days_to_exp}d", ACCENT_RED))
                elif days_to_exp <= 30:
                    chips.append(("Expires", f"{days_to_exp}d", ACCENT_AMBER))
                else:
                    chips.append(("Expires", exp, TEXT_MUTED))
            except Exception:
                pass

        return chips

    def _show_searching(self, barcode: str):
        """Shown while the Open Food Facts API call is in flight."""
        self._clear_state()
        searching = ctk.CTkFrame(
            self._state_frame, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR, height=90,
        )
        searching.grid(row=0, column=0, sticky="ew")
        searching.grid_propagate(False)
        searching.grid_rowconfigure(0, weight=1)
        searching.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            searching,
            text="⟳  AI is searching the product database…",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=ACCENT,
        ).grid(row=0, column=0)

    def _show_ai_identified(self, barcode: str, product: dict):
        """Confirmation card shown when Open Food Facts returns a match."""
        self._clear_state()
        self._pending_barcode = barcode
        self._pending_product = product

        card = ctk.CTkFrame(
            self._state_frame, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=ACCENT,
        )
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=0, column=0, sticky="ew", padx=20, pady=16)
        body.grid_columnconfigure(0, weight=1)

        # AI badge
        badge_row = ctk.CTkFrame(body, fg_color="transparent")
        badge_row.grid(row=0, column=0, sticky="w", pady=(0, 8))
        badge = ctk.CTkFrame(badge_row, fg_color=ACCENT, corner_radius=6)
        badge.pack(side="left")
        ctk.CTkLabel(
            badge, text="  AI Identified  ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=BG_PRIMARY,
        ).pack(padx=4, pady=3)
        ctk.CTkLabel(
            badge_row,
            text="  Confirm the details below before adding to inventory",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED,
        ).pack(side="left")

        # Product name + brand
        ctk.CTkLabel(
            body, text=product["name"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=1, column=0, sticky="w")

        meta_row = ctk.CTkFrame(body, fg_color="transparent")
        meta_row.grid(row=2, column=0, sticky="w", pady=(2, 10))
        if product.get("brand"):
            ctk.CTkLabel(
                meta_row, text=product["brand"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_SECONDARY,
            ).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(
            meta_row, text=product["category"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).pack(side="left")

        # Details row
        det = ctk.CTkFrame(body, fg_color="transparent")
        det.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        det.grid_columnconfigure(0, weight=1)
        det.grid_columnconfigure(1, weight=1)

        exp_days = product.get("shelf_life_days", 365)
        exp_date = (
            datetime.date.today() + datetime.timedelta(days=exp_days)
        ).strftime("%b %Y")
        for col, (label, value, color) in enumerate([
            ("Storage",     product.get("storage_suggestion", "Shelf"), ACCENT_BLUE),
            ("Est. Expiry",  exp_date,                                    TEXT_MUTED),
        ]):
            chip_f = ctk.CTkFrame(det, fg_color=BG_OVERLAY, corner_radius=8)
            chip_f.grid(row=0, column=col, sticky="w", padx=(0, 10))
            ctk.CTkLabel(
                chip_f, text=label,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                text_color=TEXT_MUTED,
            ).grid(row=0, column=0, padx=(10, 4), pady=(6, 2), sticky="w")
            ctk.CTkLabel(
                chip_f, text=value,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=color,
            ).grid(row=1, column=0, padx=(10, 10), pady=(0, 6), sticky="w")

        # Storage location override
        loc_row = ctk.CTkFrame(body, fg_color="transparent")
        loc_row.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        ctk.CTkLabel(
            loc_row, text="Storage Location",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 10))
        self._storage_var = tk.StringVar(value=product.get("storage_suggestion", "Shelf"))
        ctk.CTkEntry(
            loc_row, textvariable=self._storage_var,
            width=160, height=34,
            fg_color=BG_OVERLAY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
            corner_radius=8,
            placeholder_text="e.g. Shelf A3",
        ).pack(side="left")

        # Action buttons
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.grid(row=5, column=0, sticky="w")
        ctk.CTkButton(
            btn_row, text="✓  Confirm & Scan In",
            height=40, corner_radius=10, width=190,
            fg_color=ACCENT_GREEN, hover_color="#20B890",
            text_color="#071A10",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._confirm_ai_item,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_row, text="✗  Skip",
            height=40, corner_radius=10, width=90,
            fg_color=BG_HOVER, hover_color=BG_OVERLAY,
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self.clear_form,
        ).pack(side="left")

    def _show_not_found_manual(self, barcode: str):
        """Shown when barcode isn't in DB AND Open Food Facts has no match."""
        self._clear_state()
        self._pending_barcode = barcode

        err = ctk.CTkFrame(
            self._state_frame, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        err.grid(row=0, column=0, sticky="ew")
        err.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(err, fg_color="transparent")
        body.grid(row=0, column=0, padx=20, pady=16, sticky="ew")
        ctk.CTkLabel(
            body,
            text="Product not found in any database",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            body,
            text=f"Barcode: {barcode}  —  Add it manually to register in inventory.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=(3, 10))
        ctk.CTkButton(
            body, text="+ Add to Inventory Manually",
            height=36, corner_radius=8, width=220,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=BG_PRIMARY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._open_manual_add,
        ).pack(anchor="w")

    # ------------------------------------------------------------------
    # Controls + Actions
    # ------------------------------------------------------------------

    def _build_controls(self, p):
        ctrl = ctk.CTkFrame(p, fg_color="transparent")
        ctrl.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        ctrl.grid_columnconfigure(1, weight=1)
        qw = ctk.CTkFrame(ctrl, fg_color="transparent")
        qw.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            qw, text="Quantity",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))
        qr = ctk.CTkFrame(qw, fg_color="transparent")
        qr.pack(anchor="w")
        ctk.CTkButton(
            qr, text="-", width=38, height=38, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16),
            border_width=1, border_color=BORDER_COLOR,
            command=lambda: self._adjust_qty(-1),
        ).pack(side="left")
        self.qty_var = tk.StringVar(value="1")
        self.qty_entry = ctk.CTkEntry(
            qr, textvariable=self.qty_var, width=64, height=38,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            fg_color=BG_OVERLAY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, corner_radius=8, justify="center",
        )
        self.qty_entry.pack(side="left", padx=6)
        ctk.CTkButton(
            qr, text="+", width=38, height=38, corner_radius=8,
            fg_color=BG_ELEVATED, hover_color=BG_HOVER,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=16),
            border_width=1, border_color=BORDER_COLOR,
            command=lambda: self._adjust_qty(1),
        ).pack(side="left")
        rw = ctk.CTkFrame(ctrl, fg_color="transparent")
        rw.grid(row=0, column=1, sticky="e", padx=(24, 0))
        ctk.CTkLabel(
            rw, text="Recipient / Notes  (optional)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, 4))
        self.recip_var = tk.StringVar()
        ctk.CTkEntry(
            rw, textvariable=self.recip_var,
            placeholder_text="Who is receiving this?",
            width=280, height=38,
            fg_color=BG_OVERLAY, border_color=BORDER_COLOR,
            text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED,
            corner_radius=8,
        ).pack()

    def _build_actions(self, p):
        act = ctk.CTkFrame(p, fg_color="transparent")
        act.grid(row=4, column=0, sticky="ew", pady=(0, 28))
        act.grid_columnconfigure(0, weight=1)
        act.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            act, text="⬆  Scan In",
            height=50, corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            fg_color=ACCENT_GREEN, hover_color="#20B890",
            text_color="#071A10",
            command=self.scan_in,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            act, text="⬇  Scan Out",
            height=50, corner_radius=10,
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            fg_color=ACCENT_RED, hover_color="#E05555",
            text_color="white",
            command=self.scan_out,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def _build_recent(self, p):
        ctk.CTkLabel(
            p, text="Recent Scans",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=5, column=0, sticky="w", pady=(0, 8))
        self._recent_frame = ctk.CTkFrame(
            p, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        self._recent_frame.grid(row=6, column=0, sticky="ew", pady=(0, 20))
        self._recent_frame.grid_columnconfigure(1, weight=1)
        self._refresh_recent()

    def _refresh_recent(self):
        for w in self._recent_frame.winfo_children():
            w.destroy()
        rows = self.db.get_recent_transactions(limit=8)
        if not rows:
            ctk.CTkLabel(
                self._recent_frame, text="No scans yet",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED,
            ).pack(pady=20)
            return
        for i, tx in enumerate(rows):
            is_in = tx["transaction_type"] == "SCAN_IN"
            color = ACCENT_GREEN if is_in else ACCENT_RED
            sym   = f"+{tx['quantity']}" if is_in else f"-{tx['quantity']}"
            bg    = BG_ELEVATED if i % 2 == 0 else BG_OVERLAY
            r = ctk.CTkFrame(self._recent_frame, fg_color=bg, corner_radius=0)
            r.pack(fill="x")
            r.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                r, text=sym, width=60,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=color,
            ).grid(row=0, column=0, padx=(16, 8), pady=9, sticky="w")
            ctk.CTkLabel(
                r, text=tx["item_name"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_PRIMARY, anchor="w",
            ).grid(row=0, column=1, pady=9, sticky="w")
            ts = tx["timestamp"].split(" ")[1][:5] if " " in tx["timestamp"] else ""
            ctk.CTkLabel(
                r, text=f"{ts}  {tx['username']}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=TEXT_MUTED, anchor="e",
            ).grid(row=0, column=2, padx=(0, 16), pady=9, sticky="e")

    # ------------------------------------------------------------------
    # Barcode logic
    # ------------------------------------------------------------------

    def on_shown(self):
        self.after(150, self.barcode_entry.focus)

    def _on_barcode_change(self, *_):
        if self._lookup_timer:
            self.after_cancel(self._lookup_timer)
        bc = self.barcode_var.get().strip()
        if len(bc) >= 3:
            self._lookup_timer = self.after(350, self._lookup_now)
        elif not bc:
            self._show_idle()

    def _lookup_now(self):
        bc = self.barcode_var.get().strip()
        if not bc:
            return
        item, direction = self.db.get_item_by_any_barcode(bc)
        if item:
            self._show_item_card(item, direction)
        else:
            self._start_ai_lookup(bc)

    def _start_ai_lookup(self, barcode: str):
        """Show searching state, then hit Open Food Facts in a background thread."""
        self._show_searching(barcode)
        t = threading.Thread(target=self._do_api_lookup, args=(barcode,), daemon=True)
        t.start()

    def _do_api_lookup(self, barcode: str):
        from barcode_lookup import lookup_barcode
        product = lookup_barcode(barcode)
        def _deliver():
            try:
                if self.winfo_exists():
                    self._on_api_result(barcode, product)
            except Exception:
                pass
        try:
            self.after(0, _deliver)
        except Exception:
            pass

    def _on_api_result(self, barcode: str, product):
        if product:
            self._show_ai_identified(barcode, product)
        else:
            self._show_not_found_manual(barcode)

    def _auto_scan(self):
        bc = self.barcode_var.get().strip()
        if not bc:
            return
        item, direction = self.db.get_item_by_any_barcode(bc)
        if not item:
            self._start_ai_lookup(bc)
            return
        if direction == "SCAN_IN":
            self.scan_in()
        else:
            self.scan_out()

    # ------------------------------------------------------------------
    # AI confirm: add new product and scan it in
    # ------------------------------------------------------------------

    def _confirm_ai_item(self):
        product = self._pending_product
        barcode = self._pending_barcode
        if not product or not barcode:
            return

        qty = self._get_qty()
        if qty is None:
            return

        storage = (self._storage_var.get().strip()
                   if self._storage_var else "") or product.get("storage_suggestion", "Shelf")
        shelf_life = product.get("shelf_life_days", 365)
        exp_date = (
            datetime.date.today() + datetime.timedelta(days=shelf_life)
        ).isoformat()
        import json as _json
        nutrition_str = _json.dumps(product.get("nutrition", {}))

        ok, msg = self.db.add_item(
            barcode=barcode,
            item_name=product["name"],
            category=product["category"],
            quantity=qty,
            minimum_stock=6,
            notes="Added via AI scan",
            brand=product.get("brand", ""),
            storage_location=storage,
            shelf_life_days=shelf_life,
            expiration_date=exp_date,
            nutrition_data=nutrition_str,
        )

        if ok:
            self.db.add_transaction(
                "SCAN_IN", barcode, product["name"], product["category"],
                qty, "", self.user["username"],
            )
            try:
                self.db.log_activity(
                    self.user["username"], "AI_ADD",
                    f"Added & scanned in: {product['name']} x{qty}",
                )
            except Exception:
                pass
            Toast.show(
                self, f"✓  Added & scanned in: {product['name']}  +{qty}", kind="success"
            )
            self.after(1400, self.clear_form)
        else:
            Toast.show(self, msg, kind="error")

    def _open_manual_add(self):
        """Navigate to inventory → add item form with barcode pre-filled."""
        Toast.show(
            self,
            "Go to Inventory → Add Item to register this barcode manually.",
            kind="info",
        )

    # ------------------------------------------------------------------
    # Scan In / Out
    # ------------------------------------------------------------------

    def _get_qty(self):
        try:
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
            return qty
        except ValueError:
            Toast.show(self, "Quantity must be a positive whole number", kind="error")
            return None

    def scan_in(self):
        bc = self.barcode_var.get().strip()
        if not bc:
            Toast.show(self, "Please scan or enter a barcode first", kind="warning")
            return
        qty = self._get_qty()
        if qty is None:
            return
        item, _ = self.db.get_item_by_any_barcode(bc)
        if not item:
            Toast.show(self, "Item not found — let AI identify it first", kind="error")
            self._start_ai_lookup(bc)
            return
        self.db.adjust_stock(item["barcode"], qty)
        self.db.add_transaction(
            "SCAN_IN", item["barcode"], item["item_name"],
            item["category"], qty, "", self.user["username"],
        )
        try:
            self.db.log_activity(self.user["username"], "SCAN_IN",
                                 f"{item['item_name']} +{qty}")
        except Exception:
            pass
        Toast.show(self, f"Scan In  {item['item_name']}  +{qty}", kind="success")
        self.after(1200, self.clear_form)

    def scan_out(self):
        bc = self.barcode_var.get().strip()
        if not bc:
            Toast.show(self, "Please scan or enter a barcode first", kind="warning")
            return
        qty = self._get_qty()
        if qty is None:
            return
        recipient = self.recip_var.get().strip() or "Not Provided"
        item, _ = self.db.get_item_by_any_barcode(bc)
        if not item:
            Toast.show(self, "Item not found in inventory", kind="error")
            return
        if item["current_quantity"] < qty:
            Toast.show(
                self,
                f"Not enough stock — have {item['current_quantity']}, need {qty}",
                kind="error",
            )
            return
        self.db.adjust_stock(item["barcode"], -qty)
        self.db.add_transaction(
            "SCAN_OUT", item["barcode"], item["item_name"],
            item["category"], qty, recipient, self.user["username"],
        )
        try:
            self.db.log_activity(self.user["username"], "SCAN_OUT",
                                 f"{item['item_name']} -{qty} to {recipient}")
        except Exception:
            pass
        Toast.show(
            self,
            f"Scan Out  {item['item_name']}  -{qty}  →  {recipient}",
            kind="success",
        )
        self.after(1200, self.clear_form)

    def clear_form(self):
        self.barcode_var.set("")
        self.qty_var.set("1")
        self.recip_var.set("")
        self._show_idle()
        self._refresh_recent()
        self.after(80, self.barcode_entry.focus)

    def _adjust_qty(self, delta: int):
        try:
            v = max(1, int(self.qty_var.get()) + delta)
            self.qty_var.set(str(v))
        except ValueError:
            self.qty_var.set("1")
