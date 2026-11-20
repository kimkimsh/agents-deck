import unittest

from agents_deck.ui.sprite_art import SpriteArt
from agents_deck.ui.sprite_atlas import SpriteAtlas
from agents_deck.ui.sprite_palette import SpritePalette
from tools.render_app_icon import ICON_SIZES, composite, paintIcon, plateBounds, scene, spriteScale


class AppIconTest(unittest.TestCase):
    def setUp(self):
        self.mPalette = SpritePalette()
        self.mAtlas = SpriteAtlas(SpriteArt(), self.mPalette)

    def testEverySizeDrawsWholeSpritePixelsInsideThePlate(self):
        for tSize in ICON_SIZES:
            tContent = composite(self.mAtlas, scene(tSize))
            tScale = spriteScale(tSize, tContent)
            _, tSide = plateBounds(tSize)
            with self.subTest(size=tSize):
                self.assertGreaterEqual(tScale, 1)
                self.assertLessEqual(max(tContent.get_width(), tContent.get_height()) * tScale, tSide)

    def testIconIsExactlyItsNominalSize(self):
        tIcon = paintIcon(self.mAtlas, self.mPalette, ICON_SIZES[-1])
        self.assertEqual((tIcon.get_width(), tIcon.get_height()), (ICON_SIZES[-1], ICON_SIZES[-1]))


if __name__ == "__main__":
    unittest.main()
