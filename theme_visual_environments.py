"""
theme_visual_environments.py — Visual environment rendering for distinct theme experiences.

Creates distinct visual environments for each theme with:
- Background gradients and patterns
- Ambient animation definitions
- Visual asset references
- Lighting characteristics
- Environmental effects
"""

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter
import random


class VisualEnvironmentRenderer:
    """Renders distinct visual environments for each theme."""

    def __init__(self, theme_name: str, width: int = 1920, height: int = 1200):
        self.theme_name = theme_name
        self.width = width
        self.height = height

    def render_background(self) -> Image.Image:
        """Render theme-specific background."""
        if self.theme_name == "Harvest Day":
            return self._render_harvest_day()
        elif self.theme_name == "Autumn Harvest":
            return self._render_autumn_harvest()
        elif self.theme_name == "Orchard Bloom":
            return self._render_orchard_bloom()
        elif self.theme_name == "Moonlit Farm":
            return self._render_moonlit_farm()
        elif self.theme_name == "Cozy Pantry":
            return self._render_cozy_pantry()
        elif self.theme_name == "Farmers Market":
            return self._render_farmers_market()
        elif self.theme_name == "Garden Morning":
            return self._render_garden_morning()
        else:
            return self._render_harvest_day()

    def _render_harvest_day(self) -> Image.Image:
        """Bright daytime farm with green fields and golden crops."""
        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        # Sky gradient (blue)
        for y in range(int(self.height * 0.6)):
            t = y / (self.height * 0.6)
            r = int(135 + 120 * (1 - t))
            g = int(206 + 49 * (1 - t))
            b = int(235)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Fields gradient (green to golden)
        for y in range(int(self.height * 0.6), self.height):
            t = (y - self.height * 0.6) / (self.height * 0.4)
            r = int(34 + 100 * t)
            g = int(139 + 100 * t)
            b = int(34)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Add clouds
        self._add_clouds(img, 3, opacity=0.3)

        # Add crops/wheat
        self._add_wheat_field(img)

        return img

    def _render_autumn_harvest(self) -> Image.Image:
        """Fall farm with pumpkins and orange foliage."""
        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        # Sky gradient (warm orange)
        for y in range(int(self.height * 0.6)):
            t = y / (self.height * 0.6)
            r = int(255 - 50 * (1 - t))
            g = int(140 - 40 * (1 - t))
            b = int(0)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Fields gradient (orange to brown)
        for y in range(int(self.height * 0.6), self.height):
            t = (y - self.height * 0.6) / (self.height * 0.4)
            r = int(205 + 50 * t)
            g = int(100 + 55 * t)
            b = int(0)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Add pumpkins
        self._add_pumpkins(img)

        # Add falling leaves
        self._add_falling_leaves(img)

        return img

    def _render_orchard_bloom(self) -> Image.Image:
        """Orchard and garden with fruit trees and blossoms."""
        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        # Sky gradient (fresh blue)
        for y in range(int(self.height * 0.6)):
            t = y / (self.height * 0.6)
            r = int(100 + 155 * (1 - t))
            g = int(180 + 75 * (1 - t))
            b = int(200 + 55 * (1 - t))
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Garden gradient (green)
        for y in range(int(self.height * 0.6), self.height):
            t = (y - self.height * 0.6) / (self.height * 0.4)
            r = int(34 + 50 * t)
            g = int(180 - 50 * t)
            b = int(34)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Add trees and blossoms
        self._add_orchard_trees(img)

        return img

    def _render_moonlit_farm(self) -> Image.Image:
        """Night farm with moonlight and stars."""
        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        # Night sky gradient
        for y in range(self.height):
            t = y / self.height
            r = int(15 + 30 * t)
            g = int(25 + 40 * t)
            b = int(50 + 60 * t)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Add stars
        self._add_stars(img)

        # Add moon
        self._add_moon(img)

        # Add barn silhouette
        self._add_barn_silhouette(img)

        return img

    def _render_cozy_pantry(self) -> Image.Image:
        """Indoor wooden pantry with warm lighting."""
        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        # Wooden wall gradient
        for y in range(self.height):
            t = y / self.height
            r = int(139 + 50 * t)
            g = int(90 + 40 * t)
            b = int(43 + 30 * t)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Add wooden texture
        self._add_wood_texture(img)

        # Add warm lighting glow
        self._add_warm_glow(img)

        return img

    def _render_farmers_market(self) -> Image.Image:
        """Community produce market with stalls."""
        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        # Outdoor market sky
        for y in range(int(self.height * 0.5)):
            t = y / (self.height * 0.5)
            r = int(200 + 55 * (1 - t))
            g = int(220 + 35 * (1 - t))
            b = int(240)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Market ground
        for y in range(int(self.height * 0.5), self.height):
            t = (y - self.height * 0.5) / (self.height * 0.5)
            r = int(200 - 50 * t)
            g = int(180 - 50 * t)
            b = int(140 - 40 * t)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Add market stalls
        self._add_market_stalls(img)

        return img

    def _render_garden_morning(self) -> Image.Image:
        """Garden beds with morning sunlight and dew."""
        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        # Morning sky gradient
        for y in range(int(self.height * 0.6)):
            t = y / (self.height * 0.6)
            r = int(255 - 100 * (1 - t))
            g = int(200 - 20 * (1 - t))
            b = int(100)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Garden gradient
        for y in range(int(self.height * 0.6), self.height):
            t = (y - self.height * 0.6) / (self.height * 0.4)
            r = int(100 - 50 * t)
            g = int(180 - 50 * t)
            b = int(100 - 50 * t)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Add garden beds
        self._add_garden_beds(img)

        # Add dew sparkle
        self._add_dew_sparkle(img)

        return img

    # Helper methods for visual elements

    def _add_clouds(self, img: Image.Image, count: int = 3, opacity: float = 0.3):
        """Add clouds to the image."""
        draw = ImageDraw.Draw(img, "RGBA")
        rng = random.Random(42)  # Deterministic

        for _ in range(count):
            x = rng.randint(0, self.width)
            y = rng.randint(0, int(self.height * 0.3))
            size = rng.randint(100, 300)
            alpha = int(255 * opacity)

            # Draw cloud shape
            for i in range(3):
                cx = x + i * (size // 3)
                cy = y
                draw.ellipse(
                    [cx - size // 4, cy - size // 8, cx + size // 4, cy + size // 8],
                    fill=(255, 255, 255, alpha)
                )

    def _add_wheat_field(self, img: Image.Image):
        """Add wheat/crop visualization."""
        draw = ImageDraw.Draw(img)
        rng = random.Random(42)

        for _ in range(100):
            x = rng.randint(0, self.width)
            y = rng.randint(int(self.height * 0.5), self.height)
            height = rng.randint(20, 60)
            draw.line([(x, y), (x, y - height)], fill=(184, 134, 11), width=2)

    def _add_pumpkins(self, img: Image.Image):
        """Add pumpkin visualization."""
        draw = ImageDraw.Draw(img)
        rng = random.Random(42)

        for _ in range(20):
            x = rng.randint(0, self.width)
            y = rng.randint(int(self.height * 0.6), self.height)
            size = rng.randint(20, 50)
            draw.ellipse([x - size, y - size, x + size, y + size], fill=(255, 140, 0))

    def _add_falling_leaves(self, img: Image.Image):
        """Add falling leaves pattern."""
        draw = ImageDraw.Draw(img)
        rng = random.Random(42)

        for _ in range(50):
            x = rng.randint(0, self.width)
            y = rng.randint(0, self.height)
            size = rng.randint(5, 15)
            color = rng.choice([(255, 100, 0), (200, 50, 0), (255, 165, 0)])
            draw.ellipse([x - size, y - size, x + size, y + size], fill=color)

    def _add_orchard_trees(self, img: Image.Image):
        """Add orchard trees."""
        draw = ImageDraw.Draw(img)
        rng = random.Random(42)

        for _ in range(8):
            x = rng.randint(int(self.width * 0.1), int(self.width * 0.9))
            y = rng.randint(int(self.height * 0.3), int(self.height * 0.7))
            # Tree trunk
            draw.rectangle([x - 10, y, x + 10, y + 100], fill=(139, 69, 19))
            # Tree canopy
            draw.ellipse([x - 80, y - 100, x + 80, y + 50], fill=(34, 139, 34))
            # Blossoms
            for _ in range(5):
                bx = x + rng.randint(-60, 60)
                by = y + rng.randint(-80, 30)
                draw.ellipse([bx - 5, by - 5, bx + 5, by + 5], fill=(255, 192, 203))

    def _add_stars(self, img: Image.Image):
        """Add stars to night sky."""
        draw = ImageDraw.Draw(img)
        rng = random.Random(42)

        for _ in range(100):
            x = rng.randint(0, self.width)
            y = rng.randint(0, int(self.height * 0.7))
            size = rng.randint(1, 3)
            draw.ellipse([x - size, y - size, x + size, y + size], fill=(255, 255, 255))

    def _add_moon(self, img: Image.Image):
        """Add moon to night sky."""
        draw = ImageDraw.Draw(img)
        moon_x = int(self.width * 0.85)
        moon_y = int(self.height * 0.15)
        moon_size = 100

        draw.ellipse(
            [moon_x - moon_size, moon_y - moon_size, moon_x + moon_size, moon_y + moon_size],
            fill=(240, 240, 200)
        )

    def _add_barn_silhouette(self, img: Image.Image):
        """Add barn silhouette."""
        draw = ImageDraw.Draw(img)
        barn_x = int(self.width * 0.2)
        barn_y = int(self.height * 0.5)

        # Barn body
        draw.rectangle([barn_x, barn_y, barn_x + 200, barn_y + 200], fill=(30, 30, 30))
        # Barn roof
        draw.polygon([(barn_x, barn_y), (barn_x + 100, barn_y - 100), (barn_x + 200, barn_y)],
                     fill=(20, 20, 20))

    def _add_wood_texture(self, img: Image.Image):
        """Add wooden texture."""
        draw = ImageDraw.Draw(img)
        rng = random.Random(42)

        for _ in range(50):
            y = rng.randint(0, self.height)
            draw.line([(0, y), (self.width, y)], fill=(100, 50, 0), width=rng.randint(1, 3))

    def _add_warm_glow(self, img: Image.Image):
        """Add warm lighting glow."""
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow)

        # Warm glow from top
        for i in range(200):
            alpha = int(100 * (1 - i / 200))
            draw.rectangle([0, 0, self.width, i], fill=(255, 200, 100, alpha))

        img.paste(glow, (0, 0), glow)

    def _add_market_stalls(self, img: Image.Image):
        """Add market stall visualization."""
        draw = ImageDraw.Draw(img)
        rng = random.Random(42)

        for i in range(5):
            x = int(self.width * (0.1 + i * 0.18))
            y = int(self.height * 0.4)
            # Stall frame
            draw.rectangle([x - 50, y, x + 50, y + 150], outline=(139, 69, 19), width=3)
            # Awning
            draw.polygon([(x - 60, y), (x + 60, y), (x + 50, y - 30), (x - 50, y - 30)],
                         fill=(200, 100, 50))

    def _add_garden_beds(self, img: Image.Image):
        """Add garden bed visualization."""
        draw = ImageDraw.Draw(img)

        for i in range(5):
            x = int(self.width * 0.1)
            y = int(self.height * 0.5 + i * 80)
            width = int(self.width * 0.8)
            # Garden bed
            draw.rectangle([x, y, x + width, y + 60], outline=(139, 69, 19), width=2)
            # Plants
            for j in range(10):
                px = x + int(j * width / 10)
                py = y + 30
                draw.ellipse([px - 10, py - 10, px + 10, py + 10], fill=(34, 139, 34))

    def _add_dew_sparkle(self, img: Image.Image):
        """Add dew sparkle effect."""
        draw = ImageDraw.Draw(img)
        rng = random.Random(42)

        for _ in range(30):
            x = rng.randint(0, self.width)
            y = rng.randint(int(self.height * 0.5), self.height)
            draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(200, 220, 255))
