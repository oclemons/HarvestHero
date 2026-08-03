"""chart_widget.py — Lightweight Pillow chart widgets for CustomTkinter."""

from PIL import Image, ImageDraw, ImageFont
import customtkinter as ctk

from theme import (
    BG_CARD, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    ACCENT, ACCENT_GREEN, ACCENT_RED, ACCENT_AMBER, ACCENT_BLUE,
    FONT_FAMILY,
)


def _to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _font(size: int = 12):
    for name in ["Arial.ttf", "Helvetica.ttc", "SFPro.ttf", "Verdana.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


class ChartWidget(ctk.CTkFrame):
    """A reusable chart card drawn with Pillow."""

    def __init__(self, parent, width: int = 460, height: int = 240,
                 title: str = "", fg_color=None, corner_radius=12):
        super().__init__(parent, fg_color=fg_color or BG_CARD, corner_radius=corner_radius,
                         border_width=1, border_color=TEXT_MUTED)
        self.width = width
        self.height = height
        self.title = title
        self._img = None

        self._label = ctk.CTkLabel(self, text="")
        self._label.pack(expand=True, fill="both", padx=12, pady=12)

    def _set_image(self, pil_img):
        self._img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img,
                                 size=(self.width, self.height))
        self._label.configure(image=self._img)

    def _base(self):
        bg = _to_rgb(BG_CARD)
        img = Image.new("RGB", (self.width, self.height), bg)
        draw = ImageDraw.Draw(img)
        title_font = _font(14)
        draw.text((18, 12), self.title, fill=_to_rgb(TEXT_PRIMARY), font=title_font)
        return img, draw

    def draw_bar(self, data, y_label: str = ""):
        """data: list of {'label', 'value', 'color'}."""
        img, draw = self._base()
        if not data:
            self._set_image(img)
            return

        top_pad = 44
        btm_pad = 36
        left_pad = 52
        right_pad = 20
        plot_h = self.height - top_pad - btm_pad
        plot_w = self.width - left_pad - right_pad

        max_val = max(d["value"] for d in data) or 1
        n = len(data)
        bar_gap = 10
        bar_w = (plot_w - (n + 1) * bar_gap) // n
        bar_w = max(bar_w, 12)

        # Axes
        draw.line([(left_pad, top_pad), (left_pad, self.height - btm_pad)],
                  fill=_to_rgb(TEXT_MUTED), width=1)
        draw.line([(left_pad, self.height - btm_pad),
                   (self.width - right_pad, self.height - btm_pad)],
                  fill=_to_rgb(TEXT_MUTED), width=1)

        # Gridline
        draw.line([(left_pad, top_pad + plot_h // 2),
                   (self.width - right_pad, top_pad + plot_h // 2)],
                  fill=_to_rgb(TEXT_MUTED), width=1)

        label_font = _font(10)
        for i, d in enumerate(data):
            val = d["value"]
            color = _to_rgb(d.get("color", ACCENT))
            h = int((val / max_val) * plot_h)
            x = left_pad + bar_gap + i * (bar_w + bar_gap)
            y = self.height - btm_pad - h
            draw.rectangle([(x, y), (x + bar_w, self.height - btm_pad)],
                           fill=color)
            # label rotated-ish: just write below
            label = d["label"][:8]
            draw.text((x + 2, self.height - btm_pad + 8), label,
                      fill=_to_rgb(TEXT_SECONDARY), font=label_font)

        # Y label
        if y_label:
            draw.text((8, top_pad - 4), y_label[:20],
                      fill=_to_rgb(TEXT_MUTED), font=label_font)
        # Max value
        draw.text((left_pad + 4, top_pad - 4), str(max_val),
                  fill=_to_rgb(TEXT_MUTED), font=label_font)

        self._set_image(img)

    def draw_line(self, data):
        """data: list of {'label', 'in', 'out'}."""
        img, draw = self._base()
        if not data:
            self._set_image(img)
            return

        top_pad = 48
        btm_pad = 44
        left_pad = 52
        right_pad = 20
        plot_h = self.height - top_pad - btm_pad
        plot_w = self.width - left_pad - right_pad

        max_val = max(max(d.get("in", 0), d.get("out", 0)) for d in data) or 1
        n = max(len(data) - 1, 1)
        step = plot_w // n if n > 0 else plot_w

        draw.line([(left_pad, top_pad), (left_pad, self.height - btm_pad)],
                  fill=_to_rgb(TEXT_MUTED), width=1)
        draw.line([(left_pad, self.height - btm_pad),
                   (self.width - right_pad, self.height - btm_pad)],
                  fill=_to_rgb(TEXT_MUTED), width=1)

        def _y(v):
            return self.height - btm_pad - int((v / max_val) * plot_h)

        colors = {"in": _to_rgb(ACCENT_GREEN), "out": _to_rgb(ACCENT_RED)}
        for series in ("in", "out"):
            pts = []
            for i, d in enumerate(data):
                x = left_pad + i * step
                y = _y(d.get(series, 0))
                pts.append((x, y))
            if len(pts) > 1:
                draw.line(pts, fill=colors[series], width=2)
            for x, y in pts:
                draw.ellipse([(x-3, y-3), (x+3, y+3)], fill=colors[series])

        # X labels
        label_font = _font(10)
        for i, d in enumerate(data):
            x = left_pad + i * step - 12
            draw.text((x, self.height - btm_pad + 8), d["label"][:6],
                      fill=_to_rgb(TEXT_SECONDARY), font=label_font)

        # legend
        draw.text((self.width - right_pad - 80, top_pad - 8), "● In",
                  fill=colors["in"], font=label_font)
        draw.text((self.width - right_pad - 40, top_pad - 8), "● Out",
                  fill=colors["out"], font=label_font)

        self._set_image(img)

    def draw_donut(self, data):
        """data: list of {'label', 'value', 'color'}."""
        img, draw = self._base()
        if not data:
            self._set_image(img)
            return

        total = sum(d["value"] for d in data) or 1
        cx, cy = self.width // 2, self.height // 2
        radius = min(self.width - 80, self.height - 60) // 2
        inner = int(radius * 0.6)

        start = 0
        for d in data:
            sweep = int(360 * (d["value"] / total))
            color = _to_rgb(d.get("color", ACCENT))
            draw.pieslice(
                [(cx - radius, cy - radius), (cx + radius, cy + radius)],
                start, start + sweep, fill=color
            )
            start += sweep

        # donut hole
        draw.ellipse([(cx - inner, cy - inner), (cx + inner, cy + inner)],
                     fill=_to_rgb(BG_CARD))

        # center total
        center_font = _font(16)
        draw.text((cx - 20, cy - 10), str(total),
                  fill=_to_rgb(TEXT_PRIMARY), font=center_font)

        # legend
        label_font = _font(10)
        y = 26
        for d in data:
            color = _to_rgb(d.get("color", ACCENT))
            draw.text((12, y), f"■ {d['label'][:12]} ({d['value']})",
                      fill=color, font=label_font)
            y += 18

        self._set_image(img)
