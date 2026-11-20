from typing import Dict, Tuple

Rgba = Tuple[float, float, float, float]


class SpritePalette:
    """Palette keys of SpriteArt resolved to colours.

    Characters, bubbles and badges are drawn straight over whatever window is
    behind the deck, and the desktop theme does not predict how bright that
    is (a light theme under a dark terminal is common). So they use fixed
    colours, and the atlas always adds the light RIM outside their dark
    outline, which separates them from dark and light backdrops alike. Only
    the plate controls sit on a themed surface; their ink "i" follows the
    theme.
    """

    COMMON: Dict[str, str] = {
        "o": "#272436",
        "e": "#272436",
        "w": "#fbf7ef",
        "p": "#f38ba0",
        "d": "#27243666",
        "B": "#fbf7ef",
        "y": "#ffc94d",
        "r": "#e5484d",
        "G": "#c9ccd6",
        "g": "#8a8fa3",
        "z": "#3a3550",
        "n": "#7ee08f",
        "c": "#7fd8f5",
        "u": "#b07a4f",
        "a": "#ff8f6b",
    }

    SPECIES: Dict[str, Dict[str, str]] = {
        "claude": {"b": "#e8875f", "h": "#f8bf9c", "s": "#bf5f3f", "f": "#ffb347", "F": "#fff1b8"},
        "codex": {"b": "#7f98cc", "h": "#bccdee", "s": "#58709f", "v": "#2b3550", "q": "#8ff7e6", "Q": "#4f8f86"},
        "agy": {"b": "#6fcf97", "h": "#bdf0d0", "s": "#45a06f", "k": "#a6e3bf"},
    }

    INK_LIGHT = "#272436"
    INK_DARK = "#e9e6f2"
    INK_KEY = "i"

    RIM_HEX = "#fbf7efe6"

    def colors(self, species: str) -> Dict[str, Rgba]:
        """Fixed colours for anything drawn over the desktop."""
        tHex = dict(self.COMMON)
        tHex.update(self.SPECIES.get(species, {}))
        return self._parsed(tHex)

    def plateColors(self, dark: bool) -> Dict[str, Rgba]:
        """Colours for controls drawn on the themed plate."""
        tHex = dict(self.COMMON)
        tHex[self.INK_KEY] = self.INK_DARK if dark else self.INK_LIGHT
        return self._parsed(tHex)

    def rim(self) -> Rgba:
        return self.parse(self.RIM_HEX)

    def _parsed(self, hexColors: Dict[str, str]) -> Dict[str, Rgba]:
        return {tKey: self.parse(tValue) for tKey, tValue in hexColors.items()}

    @staticmethod
    def parse(value: str) -> Rgba:
        tDigits = value.lstrip("#")
        tAlpha = int(tDigits[6:8], 16) / 255.0 if len(tDigits) == 8 else 1.0
        return (int(tDigits[0:2], 16) / 255.0, int(tDigits[2:4], 16) / 255.0, int(tDigits[4:6], 16) / 255.0, tAlpha)
