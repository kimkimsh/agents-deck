"""Renders the README images from the real painter and animator, fed demo sessions.

Usage, from the repository root: python3 -m tools.render_readme_images docs/images

Every session, title and label below is invented: README images must never
come from a screen capture, which would show real conversations.
"""
import os
import sys
from typing import List, Optional, Tuple

import cairo
from PIL import Image

from agents_deck.constants.sprite_constants import SpriteConstants
from agents_deck.model.agent_kind import AgentKind
from agents_deck.model.agent_observation import AgentObservation
from agents_deck.model.background_kind import BackgroundKind
from agents_deck.model.background_task import BackgroundTask
from agents_deck.model.link_confidence import LinkConfidence
from agents_deck.model.phase import Phase
from agents_deck.model.session_state import SessionState
from agents_deck.model.tool_activity import ToolActivity
from agents_deck.model.tool_category import ToolCategory
from agents_deck.model.wait_reason import WaitReason
from agents_deck.ui.deck_painter import DeckPainter
from agents_deck.ui.grid_layout import GridLayout
from agents_deck.ui.sprite_animator import SpriteAnimator
from agents_deck.ui.sprite_art import SpriteArt
from agents_deck.ui.sprite_atlas import SpriteAtlas
from agents_deck.ui.sprite_palette import SpritePalette
from agents_deck.ui.tile_view import TileView
from tools.render_app_icon import paintIcon

SCALE = 4
# Shown at half this width in the README, so HiDPI screens get every pixel.
README_ICON_SIZE = 256
MARGIN_PX = 28
FRAME_MS = 50
LOOP_MS = 2000
NOW = 1_000_000.0
DARK_BACKDROP = (0.086, 0.090, 0.110)
LIGHT_BACKDROP = (0.945, 0.945, 0.960)
LABEL_FONT = "Sans"
LABEL_SIZE_PX = 14
LABEL_ROW_PX = 30
LABEL_RGB = (0.25, 0.24, 0.32)
STATE_CELL_PX = SpriteConstants.CANVAS * SCALE + 8
# Demo pane ids repeat one hex digit to the 32 digits Warp uses.
PANE_ID_DIGITS = 32


def session(pane: str, agent: AgentKind, title: str, phase: Phase, idleFor: float, tool, waiting, background: Tuple[BackgroundTask, ...]) -> SessionState:
    tObservation = AgentObservation(mPhase=phase, mWaitingFor=waiting, mTool=tool, mBackground=background, mBackgroundKnown=agent is not AgentKind.AGY, mConfidence=LinkConfidence.INFERRED if agent is AgentKind.CODEX else LinkConfidence.EXACT, mTitle=None)
    return SessionState(mPaneUuid=pane * PANE_ID_DIGITS, mAgent=agent, mPid=1, mStartTicks=1, mTitle=title, mObservation=tObservation, mPhaseSince=NOW - idleFor)


def task(taskId: str, kind: BackgroundKind) -> BackgroundTask:
    return BackgroundTask(mId=taskId, mKind=kind, mProcessName=None)


def demoSessions() -> List[SessionState]:
    return [
        session("a", AgentKind.CLAUDE, "api-server", Phase.THINKING, 3, None, None, ()),
        session("b", AgentKind.CODEX, "firmware", Phase.TOOL, 8, ToolActivity("exec_command", ToolCategory.SHELL), None, (task("s1", BackgroundKind.AGENT), task("s2", BackgroundKind.AGENT))),
        session("c", AgentKind.AGY, "web-ui", Phase.WAITING, 20, None, WaitReason.PERMISSION, ()),
        session("d", AgentKind.CLAUDE, "docs", Phase.TOOL, 2, ToolActivity("Edit", ToolCategory.EDIT), None, (task("b1", BackgroundKind.SHELL), task("a1", BackgroundKind.AGENT), task("b2", BackgroundKind.SHELL))),
        session("e", AgentKind.CODEX, "infra", Phase.ERROR, 1, None, None, ()),
        session("f", AgentKind.CLAUDE, "notes", Phase.IDLE, 3600, None, None, ()),
    ]


def tileViews(layout: GridLayout, sessions: List[SessionState], nowSeconds: float, showNames: bool) -> List[TileView]:
    tAnimator = SpriteAnimator()
    tViews = []
    for tIndex, tSession in enumerate(sessions):
        tRect = layout.tileRect(tIndex)
        tFrame = tAnimator.frame(tSession, nowSeconds, False)
        tObservation = tSession.mObservation
        tBadge = len(tObservation.mBackground) if tObservation.mBackground else None
        tViews.append(TileView(tRect.mX, tRect.mY, tFrame, tFrame.mOpacity, tBadge, tSession.mTitle if showNames else None))
    return tViews


def deckFrame(painter: DeckPainter, layout: GridLayout, sessions: List[SessionState], nowSeconds: float, dark: bool, shelf: bool) -> Image.Image:
    tWidth = layout.width() + 2 * MARGIN_PX
    tHeight = layout.height() + 2 * MARGIN_PX
    tSurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, tWidth, tHeight)
    tContext = cairo.Context(tSurface)
    tContext.set_source_rgb(*(DARK_BACKDROP if dark else LIGHT_BACKDROP))
    tContext.paint()
    tDeck = cairo.ImageSurface(cairo.FORMAT_ARGB32, layout.width(), layout.height())
    painter.paint(cairo.Context(tDeck), layout, tileViews(layout, sessions, nowSeconds, layout.mNameRow > 0), 1.0 if shelf else 0.0, dark)
    tContext.set_source_surface(tDeck, MARGIN_PX, MARGIN_PX)
    tContext.paint()
    return surfaceToImage(tSurface)


def surfaceToImage(surface: cairo.ImageSurface) -> Image.Image:
    tImage = Image.frombuffer("RGBA", (surface.get_width(), surface.get_height()), bytes(surface.get_data()), "raw", "BGRA", surface.get_stride(), 1)
    return tImage.convert("RGB")


def saveGif(frames: List[Image.Image], path: str):
    tPalette = frames[0].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    tFrames = [tFrame.quantize(palette=tPalette, dither=Image.Dither.NONE) for tFrame in frames]
    tFrames[0].save(path, save_all=True, append_images=tFrames[1:], duration=FRAME_MS, loop=0, optimize=False, disposal=1)


def renderDeck(painter: DeckPainter, outDir: str, dark: bool, name: str):
    tSessions = demoSessions()
    tLayout = GridLayout(3, 2, SCALE, len(tSessions), True)
    tFrames = [deckFrame(painter, tLayout, tSessions, NOW + tStep * FRAME_MS / 1000.0, dark, True) for tStep in range(LOOP_MS // FRAME_MS)]
    saveGif(tFrames, os.path.join(outDir, name))


def renderStates(atlas: SpriteAtlas, outDir: str):
    """One row per species, one column per state, with the state written under it."""
    tStates: List[Tuple[str, Phase, float, Optional[ToolActivity], Optional[WaitReason]]] = [
        ("thinking", Phase.THINKING, 2, None, None),
        ("shell", Phase.TOOL, 2, ToolActivity("Bash", ToolCategory.SHELL), None),
        ("editing", Phase.TOOL, 2, ToolActivity("Edit", ToolCategory.EDIT), None),
        ("searching", Phase.TOOL, 2, ToolActivity("Grep", ToolCategory.SEARCH), None),
        ("web", Phase.TOOL, 2, ToolActivity("WebFetch", ToolCategory.WEB), None),
        ("sub-agent", Phase.TOOL, 2, ToolActivity("Agent", ToolCategory.AGENT), None),
        ("permission", Phase.WAITING, 2, None, WaitReason.PERMISSION),
        ("question", Phase.WAITING, 2, None, WaitReason.INPUT),
        ("error", Phase.ERROR, 60, None, None),
        ("idle", Phase.IDLE, 5, None, None),
        ("asleep", Phase.IDLE, 3600, None, None),
    ]
    tAgents = (AgentKind.CLAUDE, AgentKind.CODEX, AgentKind.AGY)
    tTile = STATE_CELL_PX
    tWidth = MARGIN_PX * 2 + len(tStates) * tTile
    tHeight = MARGIN_PX * 2 + len(tAgents) * tTile + LABEL_ROW_PX
    tSurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, tWidth, tHeight)
    tContext = cairo.Context(tSurface)
    tContext.set_source_rgb(*LIGHT_BACKDROP)
    tContext.paint()
    tAnimator = SpriteAnimator()
    for tRow, tAgent in enumerate(tAgents):
        for tColumn, (tLabel, tPhase, tAge, tTool, tWaiting) in enumerate(tStates):
            tSession = session("z", tAgent, tLabel, tPhase, tAge, tTool, tWaiting, ())
            tFrame = tAnimator.frame(tSession, NOW, True)
            tSprite = atlas.character(tFrame.mSpecies, tFrame.mFrame, tFrame.mOverlays)
            tContext.save()
            tContext.translate(MARGIN_PX + tColumn * tTile, MARGIN_PX + tRow * tTile)
            tContext.scale(SCALE, SCALE)
            tContext.set_source_surface(tSprite, 0, 0)
            tContext.get_source().set_filter(cairo.FILTER_NEAREST)
            tContext.paint()
            tContext.restore()
    tContext.select_font_face(LABEL_FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    tContext.set_font_size(LABEL_SIZE_PX)
    tContext.set_source_rgb(*LABEL_RGB)
    tBaseline = MARGIN_PX + len(tAgents) * tTile + LABEL_SIZE_PX
    for tColumn, tState in enumerate(tStates):
        tExtents = tContext.text_extents(tState[0])
        tContext.move_to(MARGIN_PX + tColumn * tTile + (tTile - tExtents.width) / 2 - tExtents.x_bearing, tBaseline)
        tContext.show_text(tState[0])
    surfaceToImage(tSurface).save(os.path.join(outDir, "states.png"))


def main() -> int:
    tOutDir = sys.argv[1]
    os.makedirs(tOutDir, exist_ok=True)
    tArt = SpriteArt()
    tPalette = SpritePalette()
    tAtlas = SpriteAtlas(tArt, tPalette)
    tPainter = DeckPainter(tAtlas, tArt)
    renderDeck(tPainter, tOutDir, True, "deck-dark.gif")
    renderDeck(tPainter, tOutDir, False, "deck-light.gif")
    renderStates(tAtlas, tOutDir)
    paintIcon(tAtlas, tPalette, README_ICON_SIZE).write_to_png(os.path.join(tOutDir, "icon.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
