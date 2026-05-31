"""A fully-arranged band performance ready to hand to a BandRenderTarget."""
from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass
from ace_reel.contracts.interfaces import Track
from ace_reel.contracts.frame import AnimationFrame
from ace_reel.motion.planner import ClipCue
from ace_reel.band.roster import Member


@dataclass
class BandPerformance:
    track: Track
    audio_pcm: bytes
    vocalist: Member
    vocal_frames: Iterable[AnimationFrame]
    instrument_arrangement: dict[Member, list[ClipCue]]
