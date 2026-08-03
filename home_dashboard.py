"""home_dashboard.py — Dashboard with stat cards and recent activity."""

import tkinter as tk
import threading

import customtkinter as ctk

from ai_client import get_insights
from theme import (
    BG_PRIMARY, BG_SECONDARY, BG_CARD,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR,
)


class _StatCard(ctk.CTkFrame):
    def __init__(self, parent, icon, title, value, subtitle, accent):
        super().__init__(
            parent, fg_color=BG_CARD, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        self.grid_columnconfigure(0, weight=1)

        # Top row: icon + accent line
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))

        ctk.CTkLabel(
            top, text=icon,
            font=ctk.CTkFont(family=FONT_FAMILY, size=22),
            text_color=accent,
        ).pack(side="left")

        # Colored right-edge bar
        ctk.CTkFrame(self, width=4, fg_color=accent, corner_radius=2).place(
            relx=1.0, rely=0, anchor="ne", relheight=1.0, x=-1)

        # Value
        self._val_lbl = ctk.CTkLabel(
            self, text=str(value),
            font=ctk.CTkFont(family=FONT_FAMILY, size=34, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        )
        self._val_lbl.grid(row=1, column=0, padx=18, sticky="w")

        # Title
        ctk.CTkLabel(
            self, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=2, column=0, padx=18, sticky="w")

        # Subtitle
        ctk.CTkLabel(
            self, text=subtitle,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=3, column=0, padx=18, pady=(2, 18), sticky="w")

    def update_value(self, value):
        self._val_lbl.configure(text=str(value))


class _AIInsightCard(ctk.CTkFrame):
    def __init__(self, parent, title, explanation, action, severity,
                 on_review=None):
        super().__init__(
            parent, fg_color=BG_CARD, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        self.grid_columnconfigure(0, weight=1)

        colors = {
            "critical": ACCENT_RED,
            "action":   ACCENT_AMBER,
            "monitor":  ACCENT_BLUE,
            "info":     TEXT_MUTED,
        }
        accent = colors.get(severity, TEXT_MUTED)

        ctk.CTkFrame(self, width=4, fg_color=accent, corner_radius=2).place(
            relx=1.0, rely=0, anchor="ne", relheight=1.0, x=-1)

        ctk.CTkLabel(
            self, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=0, column=0, padx=18, pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            self, text=explanation,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_SECONDARY, anchor="w", wraplength=420,
        ).grid(row=1, column=0, padx=18, sticky="w")

        ctk.CTkLabel(
            self, text=f"Suggested action: {action}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=ACCENT_GOLD, anchor="w", wraplength=420,
        ).grid(row=2, column=0, padx=18, pady=(6, 0), sticky="w")

        if on_review:
            ctk.CTkButton(
                self, text="Review Inventory", height=30, width=130,
                corner_radius=8, fg_color=BG_SECONDARY, hover_color=BG_ELEVATED,
                text_color=TEXT_PRIMARY, border_width=1, border_color=BORDER_COLOR,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
                command=on_review,
            ).grid(row=3, column=0, padx=18, pady=(10, 14), sticky="w")


class HomeDashboard(ctk.CTkFrame):
    def __init__(self, parent, db, user, navigate=None):
        super().__init__(parent, fg_color=BG_PRIMARY)
        self.db = db
        self.user = user
        self.navigate = navigate
        self._cards = {}
        self._activity_rows = []
        self._build()
        self._load()

    # ------------------------------------------------------------------

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self, fg_color=BG_PRIMARY, corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 4))

        ctk.CTkLabel(
            hdr, text="Dashboard",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(
            hdr, text="↻  Refresh", width=100, height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=BG_SECONDARY, hover_color=BG_CARD,
            text_color=TEXT_SECONDARY, corner_radius=8,
            command=self._load,
        ).pack(side="right")

        # Stat cards grid (3 columns)
        cards_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="ew", padx=32, pady=(16, 0))
        for c in range(3):
            cards_frame.grid_columnconfigure(c, weight=1)

        card_defs = [
            ("total_items",   "⊞", "Total Items",     0, ACCENT_BLUE,   "SKUs in inventory"),
            ("total_units",   "◧", "Total Units",      0, ACCENT_GOLD,   "Combined stock count"),
            ("low_stock",     "⚠", "Low Stock",        0, ACCENT_AMBER,  "Items below minimum"),
            ("out_of_stock",  "✕", "Out of Stock",     0, ACCENT_RED,    "Items at zero"),
            ("today_in",      "↓", "Today's Scan Ins", 0, ACCENT_GREEN,  "Units received today"),
            ("today_out",     "↑", "Today's Scan Outs",0, "#a78bfa",     "Units given out today"),
        ]
        for i, (key, icon, title, val, accent, sub) in enumerate(card_defs):
            row, col = divmod(i, 3)
            card = _StatCard(cards_frame, icon, title, val, sub, accent)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self._cards[key] = card

        # ---- Quick-action row ----
        qa = ctk.CTkFrame(scroll, fg_color="transparent")
        qa.grid(row=2, column=0, sticky="ew", padx=32, pady=(16, 0))

        for label, icon, page, color in [
            ("Scan Items",      "⬡", "scan",      ACCENT_GOLD),
            ("View Inventory",  "▤", "inventory", ACCENT_BLUE),
            ("Transaction Log", "≡", "history",   "#a78bfa"),
            ("Reports",         "◫", "reports",   ACCENT_GREEN),
        ]:
            ctk.CTkButton(
                qa, text=f"{icon}  {label}", height=44, corner_radius=10,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                fg_color=BG_CARD, hover_color=BG_SECONDARY,
                text_color=color, border_width=1, border_color=BORDER_COLOR,
                command=lambda p=page: self.navigate(p) if self.navigate else None,
            ).pack(side="left", padx=(0, 10), expand=True, fill="x")

        # ---- AI Insights ----
        self._ai_panel = self._build_ai_panel(scroll)
        self._ai_panel.grid(row=3, column=0, sticky="ew", padx=32, pady=(24, 0))

        # ---- Recent Activity ----
        act_hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        act_hdr.grid(row=4, column=0, sticky="ew", padx=32, pady=(24, 8))
        ctk.CTkLabel(
            act_hdr, text="Recent Activity",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        self._activity_frame = ctk.CTkFrame(
            scroll, fg_color=BG_CARD, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        self._activity_frame.grid(row=5, column=0, sticky="ew", padx=32, pady=(0, 32))
        self._activity_frame.grid_columnconfigure(2, weight=1)

    # ------------------------------------------------------------------

    def _build_ai_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        panel.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(panel, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(
            hdr, text="AI Insights",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(
            hdr, text="↻  Regenerate", width=120, height=32,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=BG_CARD, hover_color=BG_ELEVATED,
            text_color=TEXT_SECONDARY, corner_radius=8,
            command=self._load_ai_insights,
        ).pack(side="right")

        self._ai_status = ctk.CTkLabel(
            panel, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED, anchor="w",
        )
        self._ai_status.grid(row=1, column=0, sticky="w", pady=(0, 8))

        self._ai_cards_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self._ai_cards_frame.grid(row=2, column=0, sticky="ew")
        self._ai_cards_frame.grid_columnconfigure(0, weight=1)

        return panel

    def _load_ai_insights(self):
        for w in self._ai_cards_frame.winfo_children():
            w.destroy()
        self._ai_status.configure(text="Loading AI insights…")
        t = threading.Thread(target=self._fetch_ai_insights, daemon=True)
        t.start()

    def _fetch_ai_insights(self):
        try:
            insights = get_insights(self.db, limit=5)
        except Exception:
            insights = []
        self.after(0, lambda: self._render_ai_insights(insights))

    def _render_ai_insights(self, insights):
        for w in self._ai_cards_frame.winfo_children():
            w.destroy()
        if not insights:
            self._ai_status.configure(text="No AI insights available right now.")
            return
        self._ai_status.configure(text=f"{len(insights)} insight(s) generated")
        for i, ins in enumerate(insights):
            card = _AIInsightCard(
                self._ai_cards_frame,
                title=ins.get("title", "Insight"),
                explanation=ins.get("explanation", ""),
                action=ins.get("action", ""),
                severity=ins.get("severity", "info"),
                on_review=(lambda: self.navigate("inventory") if self.navigate else None),
            )
            card.grid(row=i, column=0, sticky="ew", pady=(0, 8))

    def _load(self):
        try:
            stats = self.db.get_stats()
        except Exception:
            return

        self._cards["total_items"].update_value(stats["total_items"])
        self._cards["total_units"].update_value(stats["total_units"])
        self._cards["low_stock"].update_value(stats["low_stock"])
        self._cards["out_of_stock"].update_value(stats["out_of_stock"])
        self._cards["today_in"].update_value(
            f"{stats['today_in_count']}  ({stats['today_in_qty']} units)")
        self._cards["today_out"].update_value(
            f"{stats['today_out_count']}  ({stats['today_out_qty']} units)")

        # Auto-sync low/out-of-stock items to the shopping list
        try:
            self.db.sync_shopping_list_from_stock()
        except Exception:
            pass

        self._load_ai_insights()

        # Activity feed
        for w in self._activity_frame.winfo_children():
            w.destroy()

        txns = self.db.get_recent_transactions(12)
        if not txns:
            ctk.CTkLabel(
                self._activity_frame, text="No transactions yet.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED,
            ).grid(row=0, column=0, padx=24, pady=24)
            return

        # Header row
        for col, text, w in [(0, "TYPE", 80), (1, "ITEM", 220),
                              (2, "QTY", 60), (3, "USER", 100), (4, "TIME", 160)]:
            ctk.CTkLabel(
                self._activity_frame, text=text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                text_color=TEXT_MUTED, width=w, anchor="w",
            ).grid(row=0, column=col, padx=(20 if col == 0 else 8, 8),
                   pady=(14, 4), sticky="w")

        ctk.CTkFrame(
            self._activity_frame, height=1, fg_color=BORDER_COLOR,
        ).grid(row=1, column=0, columnspan=5, sticky="ew", padx=16)

        for i, t in enumerate(txns):
            r = i + 2
            is_in = t["transaction_type"] == "SCAN_IN"
            type_color = ACCENT_GREEN if is_in else ACCENT_RED
            type_text  = "▼ IN" if is_in else "▲ OUT"

            ctk.CTkLabel(
                self._activity_frame, text=type_text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=type_color, anchor="w",
            ).grid(row=r, column=0, padx=(20, 8), pady=6, sticky="w")

            ctk.CTkLabel(
                self._activity_frame, text=t["item_name"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_PRIMARY, anchor="w",
            ).grid(row=r, column=1, padx=8, pady=6, sticky="w")

            ctk.CTkLabel(
                self._activity_frame, text=str(t["quantity"]),
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=TEXT_SECONDARY, anchor="w",
            ).grid(row=r, column=2, padx=8, pady=6, sticky="w")

            ctk.CTkLabel(
                self._activity_frame, text=t["username"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED, anchor="w",
            ).grid(row=r, column=3, padx=8, pady=6, sticky="w")

            ts = t["timestamp"][:16] if t["timestamp"] else ""
            ctk.CTkLabel(
                self._activity_frame, text=ts,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=TEXT_MUTED, anchor="w",
            ).grid(row=r, column=4, padx=(8, 20), pady=6, sticky="w")

    def on_shown(self):
        self._load()
