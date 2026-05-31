"""Unreal Engine 5 multi-avatar band render target via the NVIDIA ACE plugin 2.5.

NOT runnable on macOS. Win/RTX only. Real wiring (see docs/setup-reel-engine.md):
  - N MetaHumans in one scene/Sequencer sharing the song audio track.
  - Vocalist face driven by `Apply ACE Face Animations` in their `Face_AnimBP`
    (`mh_arkit_mapping_pose_A2F`), RemoteA2F provider.
  - Instrumentalists driven by IK-retargeted instrument clips on `metahuman_base_skel`,
    scheduled from each member's ClipCue timeline (start_s + energy -> playback rate/amplitude).
  - Reel export via Movie Render Queue (1080x1920) for the offline path.
This client would forward vocal frames + the instrument arrangement to an in-engine bridge;
implement on the RTX box. Until then preflight()/open() fail loudly.
"""
from __future__ import annotations
import sys
from ace_reel.contracts.frame import AnimationFrame
from ace_reel.render.band_base import BandRenderTarget
from ace_reel.band.roster import Member
from ace_reel.motion.planner import ClipCue

_UNSUPPORTED = (
    "UnrealBandRenderTarget requires Windows + NVIDIA RTX + UE 5.6 + ACE plugin 2.5. "
    "See docs/setup-reel-engine.md. Use --engine null on this Mac."
)


class UnrealBandRenderTarget(BandRenderTarget):
    def preflight(self) -> None:
        if sys.platform != "win32":
            raise NotImplementedError(_UNSUPPORTED)

    def open(self, members: list[Member], audio_pcm: bytes,
             instrument_arrangement: dict[Member, list[ClipCue]]) -> None:
        if sys.platform != "win32":
            raise NotImplementedError(_UNSUPPORTED)
        raise NotImplementedError("In-engine band bridge not yet implemented; see docs/setup-reel-engine.md")

    def push_vocal_frame(self, frame: AnimationFrame) -> None:
        raise NotImplementedError("see docs/setup-reel-engine.md")

    def close(self) -> None:
        pass
