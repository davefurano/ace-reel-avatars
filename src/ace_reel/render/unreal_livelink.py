"""Unreal Engine 5 + MetaHuman render target via the NVIDIA ACE plugin 2.5.

NOT runnable on macOS. Real wiring (see docs/setup-reel-engine.md), verified Phase 0:
  - UE 5.6 + ACE plugin 2.5 (NV_ACE_Reference), Win64/Linux + NVIDIA RTX only.
  - Animation enters via the Anim Blueprint node `Apply ACE Face Animations`, placed in the
    MetaHuman `Face_AnimBP` before `mh_arkit_mapping_pose` (swap to `mh_arkit_mapping_pose_A2F`).
  - Provider RemoteA2F (gRPC to NVCF/self-hosted A2F). Audio+animation arrive co-synced.
  - Body/dance: ClipCues from motion.planner drive IK-retargeted clips on metahuman_base_skel,
    layered with the face via Layered Blend Per Bone (mask from spine_03/neck_01).
This client would forward AnimationFrames to a small in-engine gRPC/socket bridge; implement on
the RTX box. Until then `open()` fails loudly so nothing silently no-ops.
"""
from __future__ import annotations
import sys
from ace_reel.contracts.interfaces import RenderTarget
from ace_reel.contracts.frame import AnimationFrame


class UnrealRenderTarget(RenderTarget):
    def open(self, avatar_asset: str, audio_pcm_16k_mono: bytes) -> None:
        if sys.platform != "win32":
            raise NotImplementedError(
                "UnrealRenderTarget requires Windows + NVIDIA RTX + UE 5.6 + ACE plugin 2.5. "
                "See docs/setup-reel-engine.md. Use --engine null on this Mac."
            )
        raise NotImplementedError("In-engine bridge not yet implemented; see docs/setup-reel-engine.md")

    def push(self, frame: AnimationFrame) -> None:
        raise NotImplementedError("see docs/setup-reel-engine.md")

    def close(self) -> None:
        pass
