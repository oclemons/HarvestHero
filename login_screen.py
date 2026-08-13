"""login_screen.py — Harvest Hero Login  ·  Responsive layout, no fixed pixel positions.

Enhanced with premium glass effects and theme-aware visual environments.
"""

import os
import tkinter as tk
import customtkinter as ctk

from auth import verify_password
from theme import FONT_FAMILY
from glass_effects import create_glass_entry, create_glass_button
from glass_effects_premium import GlassEffectManager
from theme_environments import get_theme_environment, get_glass_reflection_color

# ── Palette (Theme-Aware) ────────────────────────────────────────────────────
# Default colors for Harvest Day theme
_PAGE_BG  = "#2A2E14"

# Glass card (will be enhanced with Level 3 Hero Mirror)
_CARD_BG  = "#C0CAB8"
_CARD_BDR = "#E8F0E4"

# On-card text
_TITLE    = "#1A3820"
_SUB      = "#3A5832"
_LABEL    = "#344A2C"
_AI_DIM   = "#6A5820"
_AI_HOT   = "#C9A846"

# Input fields (slightly lighter than card)
_IN_BG    = "#E0EBD8"
_IN_BDR   = "#A8C0A0"
_IN_TXT   = "#1A3020"
_IN_PH    = "#7A9870"

# Sign In button
_BTN      = "#2A6E40"
_BTN_H    = "#348A50"
_BTN_TXT  = "#FFFFFF"

# Misc
_DIV      = "#94B088"
_ERR      = "#8A2020"

# Footer — subtle signature, folded into the card (no background box)
_BRASS    = "#CF9D7B"    # antique brass
_F_DIM    = "#8C9080"

_AI_MSGS = [
    "Organizing inventory with AI...",
    "Reducing food waste, one pantry at a time...",
    "Preparing your dashboard...",
    "Optimizing pantry operations...",
    "Helping communities thrive...",
    "Synchronizing inventory across locations...",
    "Tracking every item, every day...",
    "Connecting volunteers to resources...",
]

# Raw background render resolution (procedural fallback only — cached once)
_RAW_W, _RAW_H = 1920, 1200


class LoginScreen(ctk.CTkFrame):

    def __init__(self, parent, on_success):
        super().__init__(parent, fg_color=_PAGE_BG)
        self.on_success  = on_success
        self.db          = parent.db
        self._msg_idx    = 0
        self._logo_ref   = None
        self._bg_photo   = None
        self._shadow_photo = None
        self._show_pw    = False
        self._raw_farm   = None
        self._last_wh    = (0, 0)
        self._shadow_wh  = (0, 0)
        
        # Initialize glass effect manager with theme tokens
        self._glass_manager = GlassEffectManager({
            "name": "Harvest Day",
            "BG_ELEVATED": _CARD_BG,
            "BORDER_SUBTLE": _CARD_BDR,
            "BORDER_COLOR": _DIV,
            "TEXT_PRIMARY": _TITLE,
            "TEXT_SECONDARY": _SUB,
        })
        
        self._build()
        self.after(900, self._start_rotation)

    # ── Responsive layout ────────────────────────────────────────────────────
    # No fixed X/Y anywhere: background fills window (CSS `cover` style),
    # card + shadow are centered purely via relx/rely=0.5, sized by content.

    def _build(self):
        # Background — fills the entire window, rescaled on every resize
        self._bg_label = tk.Label(self, bd=0, highlightthickness=0, bg=_PAGE_BG)
        self._bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.bind("<Configure>",
                  lambda e: self.after(120, self._on_resize) if e.widget is self else None)

        # Soft drop shadow — sits behind the card, also perfectly centered
        self._shadow_label = tk.Label(self, bd=0, highlightthickness=0, bg=_PAGE_BG)
        self._shadow_label.place(relx=0.5, rely=0.5, anchor="center")

        # Glass card — ALWAYS centered, regardless of window size
        self._card_wrap = ctk.CTkFrame(self, fg_color=_CARD_BG)
        self._card_wrap.place(relx=0.5, rely=0.5, anchor="center")
        self._build_card(self._card_wrap)

        self.after(60, self._on_resize)
        self.after(140, self._animate_in)

    def _on_resize(self):
        self._draw_bg()
        self.after(30, self._draw_shadow)

    # ── Background — CSS `cover`-style: fills window, crops excess, no stretch ──

    def _draw_bg(self):
        w = self.winfo_width()  or 1200
        h = self.winfo_height() or 800
        if w < 10 or h < 10 or (w, h) == self._last_wh:
            return
        self._last_wh = (w, h)
        try:
            from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageTk

            if self._raw_farm is None:
                self._raw_farm = self._make_farm()
            raw = self._raw_farm
            iw, ih = raw.size

            # Cover-fit: scale to fully cover w×h, then center-crop excess
            scale = max(w / iw, h / ih)
            nw, nh = max(1, int(iw * scale) + 1), max(1, int(ih * scale) + 1)
            resized = raw.resize((nw, nh), Image.LANCZOS)
            left = (nw - w) // 2
            top  = (nh - h) // 2
            cropped = resized.crop((left, top, left + w, top + h))

            bg = cropped.filter(ImageFilter.GaussianBlur(radius=10))
            bg = ImageEnhance.Color(bg).enhance(0.92)
            bg = bg.convert("RGBA")
            bg = Image.alpha_composite(bg, Image.new("RGBA", (w, h), (4, 8, 3, 46)))

            # Subtle edge vignette
            vig = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            vd  = ImageDraw.Draw(vig)
            for i in range(45):
                a = int(22 * (i / 45) ** 2)
                vd.rectangle([i, i, w - i, h - i], outline=(0, 0, 0, a))
            bg = Image.alpha_composite(bg, vig)

            self._bg_photo = ImageTk.PhotoImage(bg.convert("RGB"))
            self._bg_label.configure(image=self._bg_photo)
        except Exception:
            pass

    def _draw_shadow(self):
        """Soft blurred rounded shadow, sized to the card's actual rendered size."""
        try:
            from PIL import Image, ImageDraw, ImageFilter, ImageTk
            self.update_idletasks()
            cw = self._card_wrap.winfo_width()
            ch = self._card_wrap.winfo_height()
            if cw < 10 or ch < 10 or (cw, ch) == self._shadow_wh:
                return
            self._shadow_wh = (cw, ch)
            pad = 22
            sw, sh = cw + pad * 2, ch + pad * 2
            shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).rounded_rectangle(
                [pad, pad, pad + cw, pad + ch], radius=28, fill=(0, 0, 0, 95))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=16))
            self._shadow_photo = ImageTk.PhotoImage(shadow)
            self._shadow_label.configure(image=self._shadow_photo)
            self._shadow_label.lower(self._card_wrap)
        except Exception:
            pass

    @staticmethod
    def _make_farm():
        """Warm pumpkin-field sunrise, cached at a fixed raw resolution.
        Uses a real asset if present; else a procedural fallback."""
        from PIL import Image, ImageDraw, ImageFilter
        try:
            import paths
            for name in ("bg_farm.jpg", "bg_farm.png", "pumpkin_field.jpg"):
                p = os.path.join(paths.APP_DIR, "assets", name)
                if os.path.exists(p):
                    return Image.open(p).convert("RGB")
        except Exception:
            pass

        w, h = _RAW_W, _RAW_H
        img  = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(img)
        for y in range(h):
            t = y / h
            if t < 0.35:
                s = t / 0.35
                r = int(250 - 35 * s); g = int(185 - 25 * s); b = int(110 - 30 * s)
            elif t < 0.50:
                s = (t - 0.35) / 0.15
                r = int(215 + 15 * s); g = int(160 + 15 * s); b = int(80 - 10 * s)
            elif t < 0.62:
                s = (t - 0.50) / 0.12
                r = int(230 - 110 * s); g = int(175 - 65 * s); b = int(70 - 20 * s)
            else:
                s = min(1.0, (t - 0.62) / 0.38)
                r = int(120 - 15 * s); g = int(110 + 10 * s); b = int(50 + 20 * s)
            draw.line([(0, y), (w, y)], fill=(
                max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))))

        glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        gd   = ImageDraw.Draw(glow)
        sx, sy = int(w * 0.15), int(h * 0.20)
        for rad in range(260, 0, -4):
            a  = int(55 * (1 - rad / 260) ** 1.4)
            rc = (255, min(255, 215 + rad // 8), max(0, 90 - rad // 3))
            gd.ellipse([sx - rad, sy - rad, sx + rad, sy + rad], fill=rc)

        import random
        rng = random.Random(7)
        for _ in range(60):
            px = rng.randint(0, w); py = rng.randint(int(h * 0.63), int(h * 0.96))
            pr = rng.randint(10, 30)
            oc = (rng.randint(175, 225), rng.randint(85, 125), rng.randint(10, 35))
            gd.ellipse([px - pr, py - pr // 2, px + pr, py + pr // 2], fill=oc)

        img = img.convert("RGBA")
        img = Image.alpha_composite(img, glow)
        img = img.convert("RGB")
        img = img.filter(ImageFilter.GaussianBlur(radius=1.0))
        return img

    # ── Glass Card (Level 3 Hero Mirror) ──────────────────────────────────────

    def _build_card(self, parent):
        # Create Level 3 Hero Mirror glass card for premium appearance
        card = self._glass_manager.create_hero_mirror_panel(
            parent,
            fg_color=_CARD_BG,
            corner_radius=28,
        )
        card.pack()

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=34, pady=(30, 36))

        self._build_header(inner)
        self._build_form(inner)
        self._build_signature(inner)

    # ── Header (logo + title + AI status) ────────────────────────────────────

    def _build_header(self, parent):
        sec = ctk.CTkFrame(parent, fg_color="transparent")
        sec.pack(fill="x")

        # Logo — shrunk ~18% for better proportion, soft warm golden glow behind it
        logo_size = 148
        try:
            from PIL import Image, ImageDraw
            import paths
            path = os.path.join(paths.APP_DIR, "assets", "HarvestHeroIcon.png")
            if os.path.exists(path):
                logo_pil = Image.open(path).resize(
                    (logo_size, logo_size), Image.LANCZOS).convert("RGBA")
                # Composite golden radial glow + logo onto card-colour background
                sz = logo_size + 28
                base = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
                gd   = ImageDraw.Draw(base)
                cx2, cy2 = sz // 2, sz // 2
                for r in range(sz // 2, 0, -1):
                    a = int(38 * (1 - r / (sz // 2)) ** 1.8)
                    gd.ellipse([cx2 - r, cy2 - r, cx2 + r, cy2 + r],
                               fill=(215, 170, 45, a))
                off = (sz - logo_size) // 2
                base.paste(logo_pil, (off, off), logo_pil)
                # Composite onto card colour so glow blends into card surface
                card_base = Image.new("RGBA", (sz, sz), (192, 202, 184, 255))
                final = Image.alpha_composite(card_base, base)
                self._logo_ref = ctk.CTkImage(
                    light_image=final.convert("RGB"),
                    dark_image=final.convert("RGB"), size=(sz, sz))
                ctk.CTkLabel(sec, image=self._logo_ref, text="",
                             fg_color="transparent").pack(pady=(0, 10))
            else:
                raise FileNotFoundError
        except Exception:
            ctk.CTkLabel(sec, text="✶",
                         font=ctk.CTkFont(family=FONT_FAMILY, size=60, weight="bold"),
                         text_color=_AI_HOT, fg_color="transparent").pack(pady=(0, 10))

        ctk.CTkLabel(sec, text="HARVEST HERO",
                     font=ctk.CTkFont(family="Times New Roman", size=32, weight="bold"),
                     text_color=_TITLE).pack()

        ctk.CTkLabel(sec, text="Welcome Back",
                     font=ctk.CTkFont(family="Times New Roman", size=18, weight="bold"),
                     text_color=_SUB).pack(pady=(8, 0))

        ctk.CTkLabel(sec, text="Helping our community grow, one harvest at a time.",
                     font=ctk.CTkFont(family="Times New Roman", size=13, weight="bold"),
                     text_color=_AI_DIM, wraplength=350).pack(pady=(6, 0))

        msg_row = ctk.CTkFrame(sec, fg_color="transparent")
        msg_row.pack(pady=(12, 0))
        self._dot_lbl = ctk.CTkLabel(msg_row, text="✦",
                                     font=ctk.CTkFont(size=12),
                                     text_color=_AI_HOT, fg_color="transparent")
        self._dot_lbl.pack(side="left", padx=(0, 6))
        self._msg_lbl = ctk.CTkLabel(msg_row, text=_AI_MSGS[0],
                                     font=ctk.CTkFont(family="Times New Roman", size=12, weight="bold"),
                                     text_color=_AI_DIM, wraplength=300)
        self._msg_lbl.pack(side="left")

        ctk.CTkFrame(sec, fg_color=_DIV, height=1).pack(fill="x", pady=(16, 0))

    # ── Form ──────────────────────────────────────────────────────────────────

    def _build_form(self, parent):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=(18, 0))

        # USERNAME
        ctk.CTkLabel(f, text="USERNAME",
                     font=ctk.CTkFont(family="Times New Roman", size=12, weight="bold"),
                     text_color=_LABEL).pack(anchor="w", pady=(0, 6))
        u = ctk.CTkFrame(f, fg_color=_IN_BG, corner_radius=10,
                         border_width=1, border_color=_IN_BDR)
        u.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(u, text=" 👤", font=ctk.CTkFont(size=15),
                     text_color=_IN_PH, fg_color="transparent").pack(side="left", padx=(12, 0))
        self.username_entry = ctk.CTkEntry(
            u, width=340, height=44,
            placeholder_text="Enter your username",
            fg_color="transparent", border_width=0,
            text_color=_IN_TXT, placeholder_text_color=_IN_PH,
            font=ctk.CTkFont(family="Times New Roman", size=13))
        self.username_entry.pack(side="left", padx=(6, 12), pady=5)

        # PASSWORD
        ctk.CTkLabel(f, text="PASSWORD",
                     font=ctk.CTkFont(family="Times New Roman", size=12, weight="bold"),
                     text_color=_LABEL).pack(anchor="w", pady=(0, 6))
        p = ctk.CTkFrame(f, fg_color=_IN_BG, corner_radius=10,
                         border_width=1, border_color=_IN_BDR)
        p.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(p, text=" 🔒", font=ctk.CTkFont(size=15),
                     text_color=_IN_PH, fg_color="transparent").pack(side="left", padx=(12, 0))
        self.password_entry = ctk.CTkEntry(
            p, width=300, height=44,
            placeholder_text="Enter your password",
            show="●", fg_color="transparent", border_width=0,
            text_color=_IN_TXT, placeholder_text_color=_IN_PH,
            font=ctk.CTkFont(family="Times New Roman", size=13))
        self.password_entry.pack(side="left", padx=(6, 2), pady=5)
        
        # Eye button to toggle password visibility
        self._eye_btn = ctk.CTkButton(
            p, text="👁‍🗨", width=36, height=36,
            fg_color="transparent", hover_color=_IN_BDR,
            text_color=_IN_PH, corner_radius=6, font=ctk.CTkFont(size=14),
            command=self._toggle_pw)
        self._eye_btn.pack(side="right", padx=(0, 6))

        # Status
        self.status_label = ctk.CTkLabel(
            f, text="", text_color=_ERR, height=20,
            font=ctk.CTkFont(family="Times New Roman", size=11, weight="bold"))
        self.status_label.pack(pady=(6, 4))

        # Remember / Forgot
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", pady=(0, 16))
        self._remember_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(row, text="Remember me", variable=self._remember_var,
                        font=ctk.CTkFont(family="Times New Roman", size=11, weight="bold"),
                        text_color=_SUB, fg_color=_BTN, hover_color=_BTN_H,
                        border_color=_IN_BDR, checkmark_color="#FFFFFF",
                        corner_radius=4, width=16, height=16).pack(side="left")
        ctk.CTkButton(row, text="Forgot password?",
                      fg_color="transparent", hover_color=_IN_BG, text_color=_LABEL,
                      font=ctk.CTkFont(family="Times New Roman", size=11, weight="bold"),
                      corner_radius=6, height=24, width=0,
                      command=self._open_forgot_password).pack(side="right")

        # Sign In
        self.login_btn = ctk.CTkButton(
            f, text="SIGN IN  →", height=54,
            font=ctk.CTkFont(family="Times New Roman", size=16, weight="bold"),
            fg_color=_BTN, hover_color=_BTN_H,
            text_color=_BTN_TXT, corner_radius=12,
            command=self.login)
        self.login_btn.pack(fill="x", pady=(0, 6))

        self.username_entry.bind("<Return>", lambda _e: self.login())
        self.password_entry.bind("<Return>", lambda _e: self.login())

    # ── Signature — subtle brand mark folded into the card, no background box ──

    def _build_signature(self, parent):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=(24, 8))

        # Thin understated divider with a small centered crescent moon
        div_row = ctk.CTkFrame(f, fg_color="transparent")
        div_row.pack(pady=(0, 12))
        ctk.CTkFrame(div_row, fg_color=_IN_BDR, height=1, width=64,
                     corner_radius=0).pack(side="left", padx=(0, 8), pady=5)
        ctk.CTkLabel(div_row, text="☾",
                     font=ctk.CTkFont(family="Times New Roman", size=13),
                     text_color=_BRASS, fg_color="transparent").pack(side="left")
        ctk.CTkFrame(div_row, fg_color=_IN_BDR, height=1, width=64,
                     corner_radius=0).pack(side="left", padx=(8, 0), pady=5)

        ctk.CTkLabel(f, text="Powered by The Clemons Collective",
                     font=ctk.CTkFont(family="Times New Roman", size=12, weight="bold"),
                     text_color=_BRASS).pack()
        ctk.CTkLabel(f, text="Building Intelligent Community Solutions",
                     font=ctk.CTkFont(family="Times New Roman", size=10, weight="bold"),
                     text_color=_F_DIM).pack(pady=(3, 0))
        ctk.CTkLabel(f, text="© 2026 All Rights Reserved",
                     font=ctk.CTkFont(family="Times New Roman", size=10, weight="bold"),
                     text_color=_F_DIM).pack(pady=(3, 0))

    # ── Animations & helpers ──────────────────────────────────────────────────

    def _animate_in(self):
        """Card is always centered (relx=0.5, rely=0.5); animate a brief
        upward settle purely via padding so centering is never disturbed."""
        frames, ms = 14, 18
        for i in range(frames + 1):
            ease = 1 - (1 - i / frames) ** 2
            pad = int(14 * (1 - ease))
            self.after(i * ms, lambda p=pad: self._card_wrap.place(
                relx=0.5, rely=0.5, anchor="center", y=p))

    def _toggle_pw(self):
        """Toggle password visibility and update eye icon accordingly."""
        self._show_pw = not self._show_pw
        
        # Show plaintext when eye is open, hide when closed
        if self._show_pw:
            self.password_entry.configure(show="")  # Show plaintext
            self._eye_btn.configure(text="👁")  # Open eye = plaintext visible
        else:
            self.password_entry.configure(show="●")  # Hide with dots
            self._eye_btn.configure(text="👁‍🗨")  # Closed eye = encrypted

    def _start_rotation(self):
        self._rotate_msg()

    def _rotate_msg(self):
        try:
            self._msg_lbl.configure(text_color=_CARD_BG)
            self._dot_lbl.configure(text_color=_CARD_BG)
            self._msg_idx = (self._msg_idx + 1) % len(_AI_MSGS)
            self.after(180, lambda: (
                self._msg_lbl.configure(
                    text=_AI_MSGS[self._msg_idx], text_color=_AI_HOT),
                self._dot_lbl.configure(text_color=_AI_HOT),
            ))
            self.after(2800, lambda: self._msg_lbl.configure(text_color=_AI_DIM))
            self.after(4200, self._rotate_msg)
        except Exception:
            pass

    # ── Login logic ───────────────────────────────────────────────────────────

    def login(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self._set_status("Please enter your username and password.")
            return

        import login_throttle
        wait = login_throttle.locked_seconds(username)
        if wait > 0:
            self._set_status(
                f"Too many failed attempts. Try again in {wait} seconds."
            )
            return

        self.login_btn.configure(text="Signing in...  ", state="disabled")
        self.after(400, lambda: self._do_login(username, password))

    def _do_login(self, username: str, password: str) -> None:
        import login_throttle

        def _fail(msg: str) -> None:
            lock_for = login_throttle.record_failure(username)
            self.login_btn.configure(text="SIGN IN  →", state="normal")
            if lock_for > 0:
                self._set_status(
                    f"Too many failed attempts. Try again in {lock_for} seconds."
                )
            else:
                self._set_status(msg)
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus()

        def _succeed(user: dict) -> None:
            login_throttle.record_success(username)
            self.on_success(user)

        # ── LDAP authentication (if enabled) ──────────────────────────
        try:
            from ldap_auth import is_ldap_enabled, verify_ldap_credentials, get_ldap_config
            if is_ldap_enabled():
                ok, display_name, err = verify_ldap_credentials(username, password)
                if ok:
                    user = self._provision_ldap_user(username, display_name)
                    if user:
                        _succeed(user)
                        return
                    self.login_btn.configure(text="SIGN IN  →", state="normal")
                    self._set_status("Account is disabled. Contact an administrator.")
                    return
                else:
                    cfg = get_ldap_config()
                    if not cfg.get("fallback_to_local", True):
                        _fail(f"LDAP: {err or 'Authentication failed.'}")
                        return
        except Exception:
            pass  # ldap_auth unavailable or LDAP disabled — fall through

        # ── Local authentication ────────────────────────────────────
        user = self.db.get_user(username)
        if user and user.get("is_active") and \
                verify_password(password, user["password_hash"], user["salt"]):
            self._upgrade_hash_if_needed(user, password)
            _succeed(user)
        else:
            if user and not user.get("is_active"):
                # Account deactivated — count as a failure so a stolen
                # username still eats attempts against the lockout.
                _fail("This account has been deactivated.")
            else:
                _fail("Invalid username or password.")

    def _upgrade_hash_if_needed(self, user: dict, plaintext_password: str) -> None:
        """After a successful local login, transparently re-hash the
        password at the current PBKDF2 work factor if the stored record
        was generated with a weaker one. Silent no-op on failure — we
        don't want a background upgrade to block or reveal itself to
        the user."""
        try:
            from auth import hash_password as _hp, needs_rehash
            if needs_rehash(user["password_hash"]):
                new_hash, new_salt = _hp(plaintext_password)
                self.db.update_user_password(user["id"], new_hash, new_salt)
        except Exception:
            pass

    def _provision_ldap_user(self, username: str, display_name) -> dict | None:
        """Return the local user record for an LDAP-authenticated user,
        auto-creating a staff account on first login if one doesn't exist."""
        user = self.db.get_user(username)
        if user:
            return user if user.get("is_active") else None
        from auth import hash_password as _hp
        ph, salt = _hp(f"__ldap_managed__{username}__")
        ok, _msg = self.db.create_user_full(
            username, ph, salt, "staff", display_name or "",
            created_by="LDAP",
        )
        if ok:
            new_user = self.db.get_user(username)
            if new_user:
                self.db.set_user_active(new_user["id"], True)
                return self.db.get_user(username)
        return None

    def _open_forgot_password(self) -> None:
        from forgot_password_dialog import ForgotPasswordDialog
        ForgotPasswordDialog(self.winfo_toplevel(), self.db)

    def _set_status(self, msg: str) -> None:
        self.status_label.configure(text=msg)
