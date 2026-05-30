"""Audio2Face-3D client. A2FClient wraps a transport; NvcfA2FTransport hits hosted gRPC."""
from __future__ import annotations
import os, subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from ace_reel.contracts.frame import AnimationFrame
from ace_reel.contracts.interfaces import AceClient
from ace_reel.ace.blendshape_map import to_arkit_dict


@dataclass
class A2FRawFrame:
    names: list[str]
    weights: list[float]
    timecode_s: float
    emotions: dict[str, float] = field(default_factory=dict)


def to_pcm_16k_mono(path: str) -> bytes:
    """Transcode any audio file to A2F's required PCM s16le mono 16 kHz via ffmpeg."""
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-acodec", "pcm_s16le",
         "-ac", "1", "-ar", "16000", "pipe:1"],
        check=True, stdout=subprocess.PIPE,
    )
    return out.stdout


class A2FClient(AceClient):
    def __init__(self, transport):
        self._transport = transport

    def stream(self, pcm_16k_mono: bytes, emotions: dict[str, float] | None = None
               ) -> Iterator[AnimationFrame]:
        for raw in self._transport.process(pcm_16k_mono, emotions or {}):
            yield AnimationFrame(
                timestamp_s=raw.timecode_s,
                blendshapes=to_arkit_dict(raw.names, raw.weights),
                emotions={k: min(1.0, max(0.0, v)) for k, v in raw.emotions.items()},
                body_pose=None,
            )


class NvcfA2FTransport:
    """Real transport: bidirectional ProcessAudioStream against grpc.nvcf.nvidia.com.

    Wiring (verify against current proto before implementing):
      - metadata: ('authorization', f'Bearer {NVIDIA_API_KEY}'), ('function-id', A2F_FUNCTION_ID)
      - send: AudioStream header (PCM, ch=1, bits=16, rate=16000) then audio chunks
      - recv: AnimationDataStream — SkelAnimationHeader (blendshape names) then per-frame
              weights + timecode + emotion values.
    """
    def __init__(self, endpoint: str | None = None, api_key: str | None = None,
                 function_id: str | None = None):
        self._endpoint = endpoint or os.environ["A2F_GRPC_ENDPOINT"]
        self._api_key = api_key or os.environ["NVIDIA_API_KEY"]
        self._function_id = function_id or os.environ["A2F_FUNCTION_ID"]

    def process(self, pcm: bytes, emotions: dict[str, float]) -> Iterator[A2FRawFrame]:
        # Implemented + verified against the pinned nvidia-ace proto in the key-gated step.
        raise NotImplementedError(
            "NvcfA2FTransport requires the pinned nvidia-ace proto; complete in the key-gated step."
        )
