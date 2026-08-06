"""staff_dashboard.py — Staff workspace dashboard."""

import datetime
import customtkinter as ctk

from theme import (
    BG_SURFACE, BG_ELEVATED, BG_OVERLAY, BG_HOVER,
    ACCENT, ACCENT_HOVER, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_GOLD, ACCENT_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
    BG_PRIMARY, BG_SECONDARY, BG_CARD,
)
from chart_widget import ChartWidget


class StaffDashboard(ctk.CTkFrame):
    def __init__(self, parent, db, user: dict, navigate=None):
        super().__init__(parent, fg_color=BG_SURFACE)
        self.db       = db
        self.user     = user
        self._navigate = navigate
        self._build()

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        wrap = ctk.CTkFrame(scroll, fg_color="transparent")
        wrap.grid(row=0, column=0, sticky="ew", padx=40, pady=28)
        wrap.grid_columnconfigure(0, weight=1)

        # ── Header ──────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(wrap, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        hdr.grid_columnconfigure(1, weight=1)

        name = self.user.get("full_name") or self.user.get("username", "")
        ctk.CTkLabel(
            hdr, text=f"Welcome, {name}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            hdr, text="Staff",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=ACCENT_GREEN,
        ).grid(row=0, column=2, sticky="e")

        ctk.CTkLabel(
            wrap, text=f"Today is {datetime.date.today().strftime('%A, %B %d, %Y')}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(0, 20))

        # ── Scan Now CTA ─────────────────────────────────────────────────
        cta = ctk.CTkFrame(
            wrap, fg_color=BG_ELEVATED, corner_radius=14,
            border_width=1, border_color=BORDER_COLOR,
        )
        cta.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        cta.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(cta, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=18)
        inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            inner, text="Ready to scan?",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            inner, text="Tap the button to open the scanner and process inventory.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 12))
        ctk.CTkButton(
            inner, text="⬡  Open Scanner", height=44, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=BG_PRIMARY,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=lambda: self._navigate("scan") if self._navigate else None,
        ).grid(row=2, column=0, sticky="w")

        # ── KPI row ──────────────────────────────────────────────────────
        s  = self.db.get_stats()
        cg = ctk.CTkFrame(wrap, fg_color="transparent")
        cg.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        for c in range(4):
            cg.grid_columnconfigure(c, weight=1, uniform="ksc")

        cards = [
            ("MY SCAN-INS",  str(self._my_count("SCAN_IN")),  "today", ACCENT_GREEN, 0),
            ("MY SCAN-OUTS", str(self._my_count("SCAN_OUT")), "today", ACCENT_RED,   1),
            ("TOTAL ITEMS",  str(s["total_items"]),            "available", None,     2),
            ("LOW STOCK",    str(s["low_stock"]),              "need restock", ACCENT_AMBER, 3),
        ]
        for title, val, sub, color, col in cards:
            card = ctk.CTkFrame(
                cg, fg_color=BG_ELEVATED, corner_radius=12,
                border_width=1, border_color=BORDER_COLOR,
            )
            card.grid(row=0, column=col, sticky="nsew", padx=5)
            ctk.CTkLabel(
                card, text=title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                text_color=TEXT_MUTED, anchor="w",
            ).pack(anchor="w", padx=14, pady=(12, 3))
            ctk.CTkLabel(
                card, text=val,
                font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
                text_color=color or TEXT_PRIMARY,
            ).pack(anchor="w", padx=14)
            ctk.CTkLabel(
                card, text=sub,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                text_color=TEXT_MUTED,
            ).pack(anchor="w", padx=14, pady=(2, 12))

        # ── Low stock alert ──────────────────────────────────────────────
        low = self.db.get_low_stock_items()
        if low:
            alert = ctk.CTkFrame(
                wrap, fg_color=BG_ELEVATED, corner_radius=12,
                border_width=1, border_color=BORDER_COLOR,
            )
            alert.grid(row=4, column=0, sticky="ew", pady=(0, 20))
            alert.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                alert, text="⚠  Items running low — notify your manager",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=ACCENT_AMBER, anchor="w",
            ).pack(anchor="w", padx=16, pady=(12, 6))
            for item in low[:5]:
                ctk.CTkLabel(
                    alert,
                    text=f"  • {item['item_name']}  "
                         f"({item['current_quantity']} left, min {item['minimum_stock']})",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                    text_color=TEXT_MUTED, anchor="w",
                ).pack(anchor="w", padx=16)
            ctk.CTkFrame(alert, height=12, fg_color="transparent").pack()

        # ── Visual insights ──────────────────────────────────────────────
        self._build_charts(wrap)

        # ── My recent scans ──────────────────────────────────────────────
        ctk.CTkLabel(
            wrap, text="My Recent Scans",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_SECONDARY, anchor="w",
        ).grid(row=7, column=0, sticky="w", pady=(0, 8))

        feed = ctk.CTkFrame(
            wrap, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        feed.grid(row=8, column=0, sticky="ew", pady=(0, 28))
        feed.grid_columnconfigure(1, weight=1)

        txns = [t for t in self.db.get_recent_transactions(limit=100)
                if t["username"] == self.user["username"]][:12]

        if not txns:
            ctk.CTkLabel(
                feed, text="No scans recorded yet — use the scanner to get started.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED,
            ).pack(pady=20)
        else:
            for i, tx in enumerate(txns):
                is_in = tx["transaction_type"] == "SCAN_IN"
                color = ACCENT_GREEN if is_in else ACCENT_RED
                sym   = f"+{tx['quantity']}" if is_in else f"-{tx['quantity']}"
                bg    = BG_ELEVATED if i % 2 == 0 else BG_OVERLAY
                r = ctk.CTkFrame(feed, fg_color=bg, corner_radius=0)
                r.pack(fill="x")
                r.grid_columnconfigure(1, weight=1)
                ctk.CTkLabel(
                    r, text=sym, width=56,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                    text_color=color,
                ).grid(row=0, column=0, padx=(16, 8), pady=9, sticky="w")
                ctk.CTkLabel(
                    r, text=tx["item_name"],
                    font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                    text_color=TEXT_PRIMARY, anchor="w",
                ).grid(row=0, column=1, pady=9, sticky="w")
                ts  = tx["timestamp"].split(" ")[1][:5] if " " in tx["timestamp"] else ""
                rec = tx.get("recipient") or ""
                meta = ts
                if rec and rec not in ("Not Provided", ""):
                    meta += f"  →  {rec}"
                ctk.CTkLabel(
                    r, text=meta,
                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                    text_color=TEXT_MUTED, anchor="e",
                ).grid(row=0, column=2, padx=(0, 16), pady=9, sticky="e")

    def _build_charts(self, p):
        ctk.CTkLabel(
            p, text="MY VISUAL INSIGHTS",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=5, column=0, sticky="w", pady=(0, 4))

        charts = ctk.CTkFrame(p, fg_color="transparent")
        charts.grid(row=6, column=0, sticky="ew", pady=(0, 20))
        charts.grid_columnconfigure(0, weight=1)
        charts.grid_columnconfigure(1, weight=1)

        trend = ChartWidget(charts, width=400, height=220,
                            title="My 7-Day Scan Trend", corner_radius=12)
        trend.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        data = self.db.get_scan_trend(7, username=self.user["username"])
        trend.draw_line(data if data else
                        [{"label": "—", "in": 0, "out": 0}])

        cat = ChartWidget(charts, width=400, height=220,
                          title="Inventory by Category", corner_radius=12)
        cat.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        cat_data = self.db.get_inventory_by_category()
        palette = [ACCENT, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
                   "#8B5CF6", "#06B6D4", "#EC4899"]
        if cat_data:
            for i, d in enumerate(cat_data):
                d.setdefault("color", palette[i % len(palette)])
        else:
            cat_data = [{"label": "No items", "value": 1, "color": TEXT_MUTED}]
        cat.draw_donut(cat_data)

    def _my_count(self, txn_type: str) -> int:
        today = datetime.date.today().isoformat()
        txns  = self.db.get_transactions(trans_type=txn_type)
        return sum(1 for t in txns
                   if t["username"] == self.user["username"]
                   and t["timestamp"].startswith(today))

    def on_shown(self):
        pass
