"""admin_dashboard.py — Admin KPI dashboard."""

import tkinter as tk

import customtkinter as ctk

from theme import (
    BG_BASE, BG_SURFACE, BG_ELEVATED, BG_OVERLAY, BG_HOVER,
    ACCENT, ACCENT_HOVER, ACCENT_GOLD,
    ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
    GREEN_DIM, RED_DIM, AMBER_DIM,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_FAMILY, BORDER_COLOR, BORDER_SUBTLE,
    BG_PRIMARY, BG_SECONDARY, BG_CARD,
)
from toast import Toast
from chart_widget import ChartWidget
from tooltip_helper import add_tooltip
from glass_effects import create_glass_card, create_glass_button


def _kpi(parent, title: str, value: str, sub: str = "", color: str = None,
         col: int = 0, row: int = 0):
    """Render a single KPI card with glass effect."""
    # Glass effect card
    card = ctk.CTkFrame(
        parent, fg_color=BG_ELEVATED, corner_radius=12,
        border_width=1, border_color=BORDER_SUBTLE,
    )
    card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
    card.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        card, text=title,
        font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
        text_color=TEXT_MUTED, anchor="w",
    ).pack(anchor="w", padx=16, pady=(14, 4))

    ctk.CTkLabel(
        card, text=value,
        font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
        text_color=color or TEXT_PRIMARY, anchor="w",
    ).pack(anchor="w", padx=16)

    if sub:
        ctk.CTkLabel(
            card, text=sub,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=TEXT_MUTED, anchor="w",
        ).pack(anchor="w", padx=16, pady=(2, 12))
    else:
        ctk.CTkFrame(card, height=14, fg_color="transparent").pack()

    return card


class AdminDashboard(ctk.CTkFrame):
    def __init__(self, parent, db, user: dict, navigate=None):
        super().__init__(parent, fg_color=BG_SURFACE)
        self.db       = db
        self.user     = user
        self._navigate = navigate  # callable(page_key) from AppWindow
        self._kpi_refs: dict = {}
        self._build()

    # ------------------------------------------------------------------
    # Build
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

        # Track row number for proper layout
        self._row = 0
        
        self._build_header(wrap)
        self._build_quick_actions(wrap)  # At top, right after header
        self._build_monthly_weight_stats(wrap)  # Monthly weight statistics
        self._build_alerts(wrap)
        self._build_ava_insights(wrap)
        self._build_activity(wrap)
        self._build_charts(wrap)
        # KPIs moved to reports tab - see reports.py

    def _get_briefing_bullets(self):
        bullets = []
        try:
            s = self.db.get_stats()
            if s["out_of_stock"] > 0:
                bullets.append(("\u2715", f"{s['out_of_stock']} item(s) are out of stock.", ACCENT_RED))
            if s["low_stock"] > 0:
                bullets.append(("\u25bc", f"{s['low_stock']} item(s) need restocking.", ACCENT_AMBER))
        except Exception:
            pass
        try:
            exp14 = self.db.get_expiring_items(14)
            if exp14:
                bullets.append(("\u23f0", f"{len(exp14)} item(s) expiring within 14 days \u2014 rotate to front.", ACCENT_AMBER))
        except Exception:
            pass
        try:
            from ai_assistant import _PatternEngine
            preds = _PatternEngine(self.db).stockout_predictions(7)
            if preds:
                p1 = preds[0]
                bullets.append(("\u23f1", f"{p1['item_name']} will run out in ~{p1['days_until_zero']} days.", ACCENT_AMBER))
        except Exception:
            pass
        if not bullets:
            bullets.append(("\u2713", "Pantry operations are running smoothly \u2014 no immediate issues.", ACCENT_GREEN))
        return bullets[:4]

    def _build_header(self, p):
        import datetime as _dt
        hour  = _dt.datetime.now().hour
        greet = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
        name  = self.user.get("full_name") or self.user.get("username", "")
        today = _dt.datetime.now().strftime("%A, %B %d")

        # ── Title bar ──
        hdr_wrap = ctk.CTkFrame(p, fg_color="transparent")
        hdr_wrap.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        hdr_wrap.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(hdr_wrap, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        bar.grid_columnconfigure(1, weight=1)
        title_col = ctk.CTkFrame(bar, fg_color="transparent")
        title_col.grid(row=0, column=0, sticky="w")
        
        # Title with harvest emoji
        title_row = ctk.CTkFrame(title_col, fg_color="transparent")
        title_row.pack(anchor="w")
        ctk.CTkLabel(
            title_row, text="🌾",
            font=ctk.CTkFont(family=FONT_FAMILY, size=24),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            title_row, text="Command Center",
            font=ctk.CTkFont(family=FONT_FAMILY, size=26, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")
        
        # Greeting and date
        ctk.CTkLabel(
            title_col, text=f"{greet}, {name}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(
            title_col, text=today,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
        ).pack(anchor="w")
        # Glass effect refresh button
        create_glass_button(
            bar, text="🔄 Refresh", width=90,
            command=self.on_shown,
            fg_color=BG_ELEVATED,
            hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            border_color=BORDER_SUBTLE,
        ).grid(row=0, column=2, sticky="e")

        # ── AI Greeting Card with glass effect ──
        ai_card = ctk.CTkFrame(
            hdr_wrap, fg_color=BG_ELEVATED, corner_radius=14,
            border_width=1, border_color=BORDER_SUBTLE,
        )
        ai_card.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        ai_card.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(ai_card, fg_color="transparent")
        body.grid(row=0, column=0, sticky="ew", padx=24, pady=20)
        body.grid_columnconfigure(0, weight=1)

        badge_row = ctk.CTkFrame(body, fg_color="transparent")
        badge_row.grid(row=0, column=0, sticky="w", pady=(0, 10))
        badge = ctk.CTkFrame(badge_row, fg_color=ACCENT, corner_radius=5)
        badge.pack(side="left")
        ctk.CTkLabel(
            badge, text="  AI Command  ",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
            text_color=BG_ELEVATED,
        ).pack(padx=2, pady=3)

        ctk.CTkLabel(
            body, text=f"{greet}, {name}.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_PRIMARY, anchor="w",
        ).grid(row=1, column=0, sticky="w")

        bullets = self._get_briefing_bullets()
        for i, (icon, text, color) in enumerate(bullets):
            brow = ctk.CTkFrame(body, fg_color="transparent")
            brow.grid(row=2 + i, column=0, sticky="w", pady=2)
            ctk.CTkLabel(
                brow, text=icon, width=20,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=color,
            ).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                brow, text=text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_SECONDARY,
            ).pack(side="left")

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.grid(row=2 + len(bullets), column=0, sticky="w", pady=(14, 0))
        ctk.CTkButton(
            btn_row, text="Open AI Command \u2192",
            height=36, corner_radius=8, width=180,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=BG_ELEVATED,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=lambda: self._navigate("ai") if self._navigate else None,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            btn_row, text="Shopping List",
            height=36, corner_radius=8, width=130,
            fg_color="transparent", hover_color=BG_HOVER,
            text_color=TEXT_MUTED,
            border_width=1, border_color=BORDER_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=lambda: self._navigate("shopping") if self._navigate else None,
        ).pack(side="left")

    # KPIs moved to Reports tab - see reports.py
    # This method is kept for reference but not called
    def _build_kpis(self, p):
        pass

    # KPIs moved to Reports tab - see reports.py
    def _populate_kpis(self):
        pass

    def _build_monthly_weight_stats(self, p):
        """Build monthly weight statistics widgets."""
        ctk.CTkLabel(
            p, text="MONTHLY WEIGHT SUMMARY",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(20, 4))

        stats_row = ctk.CTkFrame(p, fg_color="transparent")
        stats_row.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        stats_row.grid_columnconfigure(0, weight=1)
        stats_row.grid_columnconfigure(1, weight=1)
        stats_row.grid_columnconfigure(2, weight=1)
        stats_row.grid_columnconfigure(3, weight=1)

        try:
            # Get current month data
            current_month = self.db.get_current_month_year()
            
            # Get client visits for this month
            conn = self.db._connect()
            cursor = conn.cursor()
            
            # Count visits this month
            cursor.execute("""
                SELECT COUNT(*) as visit_count,
                       SUM(pounds_received) as total_pounds_received
                FROM pantry_visits
                WHERE strftime('%Y-%m', visit_date) = strftime('%Y-%m', 'now', 'localtime')
            """)
            visit_data = cursor.fetchone()
            visit_count = visit_data[0] or 0
            pounds_received = visit_data[1] or 0.0
            
            # Get weight summary - use COALESCE to handle missing columns
            try:
                cursor.execute("""
                    SELECT SUM(COALESCE(current_pounds, 0)) as total_current,
                           SUM(COALESCE(donated_pounds, 0)) as total_donated,
                           SUM(COALESCE(discarded_pounds, 0)) as total_discarded
                    FROM inventory_items
                """)
                weight_data = cursor.fetchone()
                current_pounds = weight_data[0] or 0.0
                donated_pounds = weight_data[1] or 0.0
                discarded_pounds = weight_data[2] or 0.0
            except Exception as weight_error:
                print(f"[DEBUG] Weight columns not available: {weight_error}")
                # Fallback to 0 if columns don't exist
                current_pounds = 0.0
                donated_pounds = 0.0
                discarded_pounds = 0.0
            
            conn.close()
            
            # Create widgets
            _kpi(stats_row, "📊 Client Visits", str(visit_count), 
                 f"this month", ACCENT_BLUE, col=0, row=0)
            
            _kpi(stats_row, "📥 Pounds Received", f"{pounds_received:.1f} lbs",
                 f"from clients", ACCENT_GREEN, col=1, row=0)
            
            _kpi(stats_row, "📦 Current Inventory", f"{current_pounds:.1f} lbs",
                 f"in stock", ACCENT_GOLD, col=2, row=0)
            
            _kpi(stats_row, "♻️ Discarded", f"{discarded_pounds:.1f} lbs",
                 f"removed", ACCENT_RED, col=3, row=0)
            
        except Exception as e:
            print(f"Error building monthly weight stats: {e}")

    def _build_alerts(self, p):
        ctk.CTkLabel(
            p, text="ALERTS",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=3, column=0, sticky="w", pady=(20, 4))

        row = ctk.CTkFrame(p, fg_color="transparent")
        row.grid(row=4, column=0, sticky="ew", pady=(0, 20))  # Updated row number
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)

        # Out of stock
        self._oos_frame = ctk.CTkFrame(
            row, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        self._oos_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._oos_frame.grid_columnconfigure(0, weight=1)

        # Low stock
        self._low_frame = ctk.CTkFrame(
            row, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        self._low_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._low_frame.grid_columnconfigure(0, weight=1)

        self._populate_alerts()

    def _populate_alerts(self):
        for w in self._oos_frame.winfo_children():
            w.destroy()
        for w in self._low_frame.winfo_children():
            w.destroy()

        # Get current low stock items
        low_stock_items = self.db.get_low_stock_items()
        
        # Get predictive warnings (items that will run out soon)
        try:
            from ai_assistant import _PatternEngine
            predictions = _PatternEngine(self.db).stockout_predictions(7)
            # Filter out items already in low stock
            low_stock_names = {item["item_name"] for item in low_stock_items}
            predictive_items = [p for p in predictions if p["item_name"] not in low_stock_names]
        except Exception:
            predictive_items = []
        
        # Combine for display (current low stock + predictive warnings)
        combined_low_stock = low_stock_items + predictive_items
        
        # Out of stock section
        self._alert_section(self._oos_frame, "OUT OF STOCK", ACCENT_RED,
                            self.db.get_out_of_stock_items())
        
        # Low stock section (with predictive warnings)
        self._alert_section(self._low_frame, "LOW STOCK & PREDICTIONS", ACCENT_AMBER,
                            combined_low_stock, show_predictions=True)

    def _alert_section(self, parent, title, color, items, show_predictions=False):
        ctk.CTkLabel(
            parent, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=color, anchor="w",
        ).pack(anchor="w", padx=16, pady=(14, 8))

        if not items:
            ctk.CTkLabel(
                parent, text="All clear",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED,
            ).pack(anchor="w", padx=16, pady=(0, 14))
            return

        for item in items[:8]:
            r = ctk.CTkFrame(parent, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=2)
            r.grid_columnconfigure(0, weight=1)
            
            # Item name
            item_name = item["item_name"]
            # Add prediction indicator if this is a predictive item
            if show_predictions and "days_until_zero" in item:
                item_name += f" (⏱ {item['days_until_zero']}d)"
            
            ctk.CTkLabel(
                r, text=item_name,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_PRIMARY, anchor="w",
            ).grid(row=0, column=0, sticky="w")
            
            # Quantity display
            if "days_until_zero" in item:
                qty_text = f"{item['current_quantity']} units"
            else:
                qty_text = f"{item['current_quantity']} / {item['minimum_stock']}"
            
            ctk.CTkLabel(
                r, text=qty_text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=color, anchor="e",
            ).grid(row=0, column=1, sticky="e")

        if len(items) > 8:
            ctk.CTkLabel(
                parent, text=f"+ {len(items)-8} more",
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=TEXT_MUTED,
            ).pack(anchor="w", padx=16, pady=(4, 0))

        ctk.CTkFrame(parent, height=12, fg_color="transparent").pack()

    def _build_ava_insights(self, p):
        ctk.CTkLabel(
            p, text="AI INSIGHTS",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=5, column=0, sticky="w", pady=(0, 4))

        self._ava_frame = ctk.CTkFrame(
            p, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        self._ava_frame.grid(row=6, column=0, sticky="ew", pady=(0, 20))
        self._ava_frame.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self._ava_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        hdr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            hdr, text="Harvest Hero AI  ·  Pattern Analysis",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=ACCENT,
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            hdr, text="AI Command →", width=100, height=26,
            fg_color="transparent", hover_color=BG_HOVER,
            text_color=TEXT_MUTED, corner_radius=6,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            command=lambda: self._navigate("ai") if self._navigate else None,
        ).grid(row=0, column=2, sticky="e")

        self._ava_inner = ctk.CTkFrame(self._ava_frame, fg_color="transparent")
        self._ava_inner.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        self._ava_inner.grid_columnconfigure(0, weight=1)
        self._populate_ava_insights()

    def _populate_ava_insights(self):
        for w in self._ava_inner.winfo_children():
            w.destroy()
        from ai_assistant import _LocalAI
        _COLORS = {"error": ACCENT_RED, "warning": ACCENT_AMBER,
                   "info": ACCENT, "success": ACCENT_GREEN}
        insights = _LocalAI(self.db).insights()[:4]
        if not insights:
            ctk.CTkLabel(
                self._ava_inner, text="No issues detected — inventory is healthy.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_MUTED,
            ).grid(row=0, column=0, sticky="w", pady=6)
            return
        for i, ins in enumerate(insights):
            color = _COLORS.get(ins["kind"], ACCENT)
            row_f = ctk.CTkFrame(self._ava_inner, fg_color="transparent")
            row_f.grid(row=i, column=0, sticky="ew", pady=3)
            row_f.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                row_f, text=ins["icon"], width=28,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=color,
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                row_f,
                text=f"{ins['title']}  —  {ins['body']}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_PRIMARY, anchor="w", wraplength=680,
            ).grid(row=0, column=1, sticky="w", padx=(6, 0))

    def _build_activity(self, p):
        ctk.CTkLabel(
            p, text="RECENT ACTIVITY",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=7, column=0, sticky="w", pady=(0, 4))

        self._activity_frame = ctk.CTkFrame(
            p, fg_color=BG_ELEVATED, corner_radius=12,
            border_width=1, border_color=BORDER_COLOR,
        )
        self._activity_frame.grid(row=8, column=0, sticky="ew", pady=(0, 20))
        self._activity_frame.grid_columnconfigure(1, weight=1)
        self._populate_activity()

    def _populate_activity(self):
        for w in self._activity_frame.winfo_children():
            w.destroy()

        txns = self.db.get_recent_transactions(limit=10)
        if not txns:
            ctk.CTkLabel(
                self._activity_frame, text="No transactions yet",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED,
            ).pack(pady=20)
            return

        for i, tx in enumerate(txns):
            is_in  = tx["transaction_type"] == "SCAN_IN"
            color  = ACCENT_GREEN if is_in else ACCENT_RED
            sym    = f"+{tx['quantity']}" if is_in else f"-{tx['quantity']}"
            bg     = BG_ELEVATED if i % 2 == 0 else BG_OVERLAY

            r = ctk.CTkFrame(self._activity_frame, fg_color=bg, corner_radius=0)
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

            ts = tx["timestamp"].split(" ")[1][:5] if " " in tx["timestamp"] else ""
            recip = tx.get("recipient") or ""
            meta  = f"{ts}  ·  {tx['username']}"
            if recip and recip not in ("Not Provided", ""):
                meta += f"  →  {recip}"
            ctk.CTkLabel(
                r, text=meta,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=TEXT_MUTED, anchor="e",
            ).grid(row=0, column=2, padx=(0, 16), pady=9, sticky="e")

    def _build_quick_actions(self, p):
        ctk.CTkLabel(
            p, text="QUICK ACTIONS",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(20, 4))

        qa = ctk.CTkFrame(p, fg_color="transparent")
        qa.grid(row=2, column=0, sticky="ew", pady=(0, 28))

        actions = [
            ("Add Item",        ACCENT,       self._qa_add_item),
            ("Create User",     ACCENT_GREEN, self._qa_create_user),
            ("Review Barcodes", BG_ELEVATED,  self._qa_review_barcodes),
            ("Archive Manager", BG_ELEVATED,  self._qa_archive),
            ("Export Report",   BG_ELEVATED,  self._qa_export),
            ("Backup Database", BG_ELEVATED,  self._qa_backup),
        ]
        for label, color, cmd in actions:
            is_accent = color not in (BG_ELEVATED,)
            ctk.CTkButton(
                qa, text=label, height=42, corner_radius=10,
                fg_color=color, hover_color=ACCENT_HOVER if color == ACCENT else BG_HOVER,
                text_color="white" if is_accent else TEXT_SECONDARY,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                border_width=0 if is_accent else 1,
                border_color=BORDER_COLOR,
                command=cmd,
            ).pack(side="left", padx=(0, 10))

    # ------------------------------------------------------------------
    # Quick action stubs (delegate to parent nav via event or direct call)
    # ------------------------------------------------------------------

    def _qa_add_item(self):
        if self._navigate:
            self._navigate("inventory")
        else:
            Toast.show(self, "Navigate to Inventory to add items", kind="info")

    def _qa_create_user(self):
        from user_management import _UserModal
        _UserModal(
            self.winfo_toplevel(), self.db,
            current_admin=self.user.get("username", ""),
            on_save=lambda action, uname: Toast.show(
                self,
                f"User '{uname}' created — they can now log in.",
                kind="success",
            ),
        )

    def _qa_archive(self):
        if self._navigate:
            self._navigate("archive")
        else:
            Toast.show(self, "Navigate to Archive Manager", kind="info")

    def _qa_export(self):
        if self._navigate:
            self._navigate("reports")
        else:
            Toast.show(self, "Navigate to Reports page", kind="info")

    def _qa_backup(self):
        import shutil, os, datetime
        from paths import BACKUP_DIR
        ts_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        src = self.db.db_path
        dst = os.path.join(BACKUP_DIR, f"inventory_backup_{ts_file}.db")
        try:
            shutil.copy2(src, dst)
            # Backups carry password hashes and full inventory — lock to owner.
            try:
                os.chmod(dst, 0o600)
            except OSError:
                pass
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            self.db.set_app_setting("last_backup", ts)
            Toast.show(self, f"Backup saved \u2192 output/backups/{os.path.basename(dst)}", kind="success")
        except Exception as e:
            Toast.show(self, f"Backup failed: {e}", kind="error")

    def _qa_review_barcodes(self):
        if self._navigate:
            self._navigate("barcodes")
        else:
            Toast.show(self, "Navigate to Barcode Review", kind="info")

    def _build_charts(self, p):
        ctk.CTkLabel(
            p, text="VISUAL INSIGHTS",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=11, column=0, sticky="w", pady=(0, 4))

        self._charts_frame = ctk.CTkFrame(p, fg_color="transparent")
        self._charts_frame.grid(row=12, column=0, sticky="ew", pady=(0, 28))
        self._charts_frame.grid_columnconfigure(0, weight=1)
        self._charts_frame.grid_columnconfigure(1, weight=1)
        self._populate_charts()

    def _populate_charts(self):
        for w in self._charts_frame.winfo_children():
            w.destroy()

        # 7-day scan trend
        trend = ChartWidget(self._charts_frame, width=440, height=230,
                            title="7-Day Scan Trend", corner_radius=12)
        trend.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 12))
        data = self.db.get_scan_trend(7)
        trend.draw_line(data if data else
                        [{"label": "—", "in": 0, "out": 0}])

        # Inventory by category
        cat = ChartWidget(self._charts_frame, width=440, height=230,
                          title="Inventory by Category", corner_radius=12)
        cat.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 12))
        cat_data = self.db.get_inventory_by_category()
        palette = [ACCENT, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
                   "#8B5CF6", "#06B6D4", "#EC4899"]
        if cat_data:
            for i, d in enumerate(cat_data):
                d.setdefault("color", palette[i % len(palette)])
        else:
            cat_data = [{"label": "No items", "value": 1, "color": TEXT_MUTED}]
        cat.draw_donut(cat_data)

        # Top low-stock gaps
        low = ChartWidget(self._charts_frame, width=440, height=230,
                          title="Top Low / Out of Stock Gaps", corner_radius=12)
        low.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 12))
        low_data = self.db.get_top_low_stock()
        bar_data = []
        for item in low_data:
            gap = max(item["minimum_stock"] - item["current_quantity"], 0)
            color = ACCENT_AMBER if item["current_quantity"] > 0 else ACCENT_RED
            bar_data.append({"label": item["item_name"], "value": gap, "color": color})
        low.draw_bar(bar_data if bar_data else
                     [{"label": "All stocked", "value": 0, "color": ACCENT_GREEN}],
                     y_label="needed")

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def on_shown(self):
        self._populate_kpis()
        self._populate_alerts()
        self._populate_ava_insights()
        self._populate_activity()
        self._populate_charts()
