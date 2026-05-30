# ACE Reel Avatars — Template Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the engine-agnostic Python "template spine" of the NVIDIA-ACE→Unreal singing/dancing avatar pipeline — everything that runs and is testable on the MacBook Air — with the Unreal render target as a documented, interface-conforming stub to finish on a Windows/RTX box.

**Architecture:** Three typed adapters (`AceClient`, `RenderTarget`, `MusicSource`) sit behind abstract interfaces and exchange one neutral type, `AnimationFrame`. An `Orchestrator` streams a song's audio → ffmpeg transcode (16 kHz mono PCM) → `AceClient` (NVIDIA Audio2Face-3D, hosted gRPC) → `AnimationFrame`s → a `RenderTarget`. A parallel `motion` module derives tempo/beats (librosa) and emits a beat-synced clip timeline, since NVIDIA ships no audio→dance service. No ACE type leaks into render; no UE type leaks into ACE.

**Tech Stack:** Python 3.11, pydantic v2 (frame schema), grpcio + NVIDIA `nvidia-ace` SDK protos (A2F-3D), librosa + numpy (beat detection), supabase-py (music source), ffmpeg (CLI, via subprocess), click (CLI), pytest (TDD).

**Scope boundary (from `docs/00-discovery.md`):** Verifiable-on-Mac = contracts, blendshape map, AceClient (live A2F via hosted endpoint when `NVIDIA_API_KEY` set), beat detection, MusicSource (live against Supabase `xltunldffphrlqstujyg` when creds set), orchestrator, CLI. NOT verifiable here (Win64+RTX) = the actual UE5/MetaHuman render, IK-retarget of dance clips, reel export → these are stubs + setup docs.

---

## File Structure

```
ace-reel-avatars/
  pyproject.toml                 # package + deps + pytest config
  .env.example                   # NVIDIA_API_KEY, A2F function-id, SUPABASE_URL/KEY, bucket
  README.md                      # quickstart + the template story
  docs/
    00-discovery.md              # DONE (Phase 0)
    01-architecture.md           # Task 11
    setup-nvidia-ace.md          # Task 11
    setup-reel-engine.md         # Task 11 (Windows/RTX UE5 + MetaHuman + ACE plugin)
    add-a-render-target.md       # Task 11 (template extension guide)
  src/ace_reel/
    __init__.py
    contracts/
      __init__.py
      frame.py                   # AnimationFrame, ArkitBlendshapes, Emotions, BodyPose — Task 1
      interfaces.py              # AceClient, RenderTarget, MusicSource ABCs, Track — Task 2
    ace/
      __init__.py
      blendshape_map.py          # ARKit-52 canonical names + A2F weight-array mapping — Task 3
      ace_client.py              # A2FClient over hosted gRPC + ffmpeg transcode — Task 4
    motion/
      __init__.py
      beat.py                    # librosa tempo/beat detection — Task 5
      planner.py                 # beat-synced clip timeline (data only) — Task 6
    render/
      __init__.py
      base.py                    # RenderTarget already in interfaces; NullRenderTarget — Task 7
      unreal_livelink.py         # UnrealRenderTarget stub (Win/RTX) — Task 8
    music/
      __init__.py
      aimymusic_suno.py          # AImyMusicSunoSource over Supabase songs/personal-library — Task 9
    orchestrator.py              # MusicSource → AceClient → RenderTarget — Task 10
    cli.py                       # `perform --track <id> --avatar <asset> --engine null|unreal` — Task 10
  tests/
    test_frame.py  test_interfaces.py  test_blendshape_map.py  test_ace_client.py
    test_beat.py  test_planner.py  test_render.py  test_unreal_stub.py
    test_music_source.py  test_orchestrator.py  test_cli.py
    fakes.py                     # FakeMusicSource, FakeAceClient, RecordingRenderTarget
```

---

## Task 0: Project bootstrap

**Files:**
- Create: `ace-reel-avatars/pyproject.toml`
- Create: `ace-reel-avatars/.env.example`
- Create: `ace-reel-avatars/src/ace_reel/__init__.py` (+ empty `__init__.py` in every subpackage)
- Create: `ace-reel-avatars/tests/__init__.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "ace-reel-avatars"
version = "0.1.0"
description = "NVIDIA ACE x Unreal singing/dancing avatar pipeline — template spine"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.6",
  "grpcio>=1.60",
  "nvidia-ace>=1.2",          # A2F-3D protos/SDK; pin exact version in Task 4 after live check
  "librosa>=0.10",
  "numpy>=1.26",
  "supabase>=2.4",
  "click>=8.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[project.scripts]
perform = "ace_reel.cli:main"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = ["live: hits a real external service; requires creds (deselect with -m 'not live')"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Write `.env.example`** (NO real secrets — env-only, per ground rule #4)

```bash
# NVIDIA Audio2Face-3D (hosted, build.nvidia.com)
NVIDIA_API_KEY=nvapi-xxxxxxxx
A2F_GRPC_ENDPOINT=grpc.nvcf.nvidia.com:443
A2F_FUNCTION_ID=9327c39f-xxxx-xxxx-xxxx-xxxxxxxxxxxx   # James (see docs/setup-nvidia-ace.md)

# AImyMusic Suno library (canonical monorepo project)
SUPABASE_URL=https://xltunldffphrlqstujyg.supabase.co
SUPABASE_SERVICE_KEY=eyJxxxx
SUNO_AUDIO_BUCKET=personal-library

# Render
RENDER_ENGINE=null   # null (Mac) | unreal (Win/RTX)
```

- [ ] **Step 3: Create package dirs + empty `__init__.py`** for `ace_reel`, `contracts`, `ace`, `motion`, `render`, `music`, and `tests`.

- [ ] **Step 4: Verify install**

Run: `cd ace-reel-avatars && python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"`
Expected: installs without error (if `nvidia-ace` resolution fails, comment it out and re-pin in Task 4).

- [ ] **Step 5: Commit**

```bash
git init && git add -A && git commit -m "chore: bootstrap ace-reel-avatars template spine"
```

---

## Task 1: AnimationFrame contract (the template's spine)

**Files:**
- Create: `src/ace_reel/contracts/frame.py`
- Test: `tests/test_frame.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_frame.py
import pytest
from pydantic import ValidationError
from ace_reel.contracts.frame import AnimationFrame, ARKIT_52, EMOTIONS

def test_frame_holds_arkit_blendshapes_emotions_and_timestamp():
    bs = {name: 0.0 for name in ARKIT_52}
    bs["JawOpen"] = 0.8
    emo = {name: 0.0 for name in EMOTIONS}
    emo["joy"] = 0.5
    f = AnimationFrame(timestamp_s=0.033, blendshapes=bs, emotions=emo, body_pose=None)
    assert f.timestamp_s == pytest.approx(0.033)
    assert f.blendshapes["JawOpen"] == pytest.approx(0.8)
    assert f.emotions["joy"] == pytest.approx(0.5)
    assert f.body_pose is None

def test_frame_rejects_unknown_blendshape():
    bs = {"NotARealShape": 0.5}
    with pytest.raises(ValidationError):
        AnimationFrame(timestamp_s=0.0, blendshapes=bs, emotions={}, body_pose=None)

def test_frame_clamps_out_of_range_weight():
    with pytest.raises(ValidationError):
        AnimationFrame(timestamp_s=0.0, blendshapes={"JawOpen": 2.0}, emotions={}, body_pose=None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_frame.py -v`
Expected: FAIL — `ModuleNotFoundError: ace_reel.contracts.frame`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/contracts/frame.py
"""Engine-agnostic animation frame — the one type every adapter speaks."""
from __future__ import annotations
from pydantic import BaseModel, field_validator, ConfigDict

# Apple ARKit-52 blendshape names — the common pivot between A2F-3D output and MetaHuman.
ARKIT_52: tuple[str, ...] = (
    "EyeBlinkLeft","EyeLookDownLeft","EyeLookInLeft","EyeLookOutLeft","EyeLookUpLeft",
    "EyeSquintLeft","EyeWideLeft","EyeBlinkRight","EyeLookDownRight","EyeLookInRight",
    "EyeLookOutRight","EyeLookUpRight","EyeSquintRight","EyeWideRight","JawForward",
    "JawLeft","JawRight","JawOpen","MouthClose","MouthFunnel","MouthPucker","MouthLeft",
    "MouthRight","MouthSmileLeft","MouthSmileRight","MouthFrownLeft","MouthFrownRight",
    "MouthDimpleLeft","MouthDimpleRight","MouthStretchLeft","MouthStretchRight",
    "MouthRollLower","MouthRollUpper","MouthShrugLower","MouthShrugUpper","MouthPressLeft",
    "MouthPressRight","MouthLowerDownLeft","MouthLowerDownRight","MouthUpperUpLeft",
    "MouthUpperUpRight","BrowDownLeft","BrowDownRight","BrowInnerUp","BrowOuterUpLeft",
    "BrowOuterUpRight","CheekPuff","CheekSquintLeft","CheekSquintRight","NoseSneerLeft",
    "NoseSneerRight","TongueOut",
)
_ARKIT_SET = frozenset(ARKIT_52)

# A2F-3D's 10 emotion channels.
EMOTIONS: tuple[str, ...] = (
    "amazement","anger","cheekiness","disgust","fear","grief","joy","outofbreath","pain","sadness",
)
_EMOTION_SET = frozenset(EMOTIONS)


class JointRotation(BaseModel):
    """One skeletal joint as a quaternion (body pose; None until the dance module fills it)."""
    name: str
    x: float; y: float; z: float; w: float


class BodyPose(BaseModel):
    joints: list[JointRotation]


class AnimationFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timestamp_s: float
    blendshapes: dict[str, float]
    emotions: dict[str, float]
    body_pose: BodyPose | None = None

    @field_validator("blendshapes")
    @classmethod
    def _check_blendshapes(cls, v: dict[str, float]) -> dict[str, float]:
        bad = set(v) - _ARKIT_SET
        if bad:
            raise ValueError(f"unknown ARKit blendshapes: {sorted(bad)}")
        for name, w in v.items():
            if not (0.0 <= w <= 1.0):
                raise ValueError(f"blendshape {name}={w} out of range [0,1]")
        return v

    @field_validator("emotions")
    @classmethod
    def _check_emotions(cls, v: dict[str, float]) -> dict[str, float]:
        bad = set(v) - _EMOTION_SET
        if bad:
            raise ValueError(f"unknown emotions: {sorted(bad)}")
        for name, w in v.items():
            if not (0.0 <= w <= 1.0):
                raise ValueError(f"emotion {name}={w} out of range [0,1]")
        return v
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_frame.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/contracts/frame.py tests/test_frame.py
git commit -m "feat(contracts): AnimationFrame with ARKit-52 + emotion validation"
```

---

## Task 2: Adapter interfaces + Track

**Files:**
- Create: `src/ace_reel/contracts/interfaces.py`
- Test: `tests/test_interfaces.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_interfaces.py
import inspect, pytest
from ace_reel.contracts.interfaces import AceClient, RenderTarget, MusicSource, Track

def test_interfaces_are_abstract():
    for cls in (AceClient, RenderTarget, MusicSource):
        with pytest.raises(TypeError):
            cls()  # cannot instantiate an ABC with abstract methods

def test_track_carries_metadata():
    t = Track(id="abc", title="Song", duration_s=180, audio_url="https://x/y.mp3", bpm=None)
    assert t.id == "abc" and t.bpm is None

def test_aceclient_stream_is_the_contract():
    assert "stream" in {n for n, _ in inspect.getmembers(AceClient, inspect.isfunction)}
```

- [ ] **Step 2: Run** `pytest tests/test_interfaces.py -v` → FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/contracts/interfaces.py
"""The three sacred adapter boundaries. No concrete vendor type may leak across these."""
from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from .frame import AnimationFrame


@dataclass(frozen=True)
class Track:
    id: str
    title: str
    duration_s: int
    audio_url: str          # signed/streamable URL to the source audio (any codec)
    bpm: float | None = None


class MusicSource(ABC):
    """Yields Tracks (audio + metadata) from some library."""
    @abstractmethod
    def get_track(self, track_id: str) -> Track: ...
    @abstractmethod
    def read_audio(self, track: Track) -> bytes:
        """Return the raw source audio bytes (original codec; orchestrator transcodes)."""


class AceClient(ABC):
    """Turns 16 kHz mono PCM audio into a stream of engine-agnostic AnimationFrames."""
    @abstractmethod
    def stream(self, pcm_16k_mono: bytes, emotions: dict[str, float] | None = None
               ) -> Iterator[AnimationFrame]: ...


class RenderTarget(ABC):
    """Engine-agnostic sink for AnimationFrames + the song audio. Concrete impls drive an engine."""
    @abstractmethod
    def open(self, avatar_asset: str, audio_pcm_16k_mono: bytes) -> None: ...
    @abstractmethod
    def push(self, frame: AnimationFrame) -> None: ...
    @abstractmethod
    def close(self) -> None: ...

    def run(self, avatar_asset: str, audio: bytes, frames: Iterable[AnimationFrame]) -> None:
        self.open(avatar_asset, audio)
        try:
            for f in frames:
                self.push(f)
        finally:
            self.close()
```

- [ ] **Step 4: Run** `pytest tests/test_interfaces.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/contracts/interfaces.py tests/test_interfaces.py
git commit -m "feat(contracts): AceClient/RenderTarget/MusicSource interfaces + Track"
```

---

## Task 3: Blendshape map (A2F weight array → named ARKit-52)

**Files:**
- Create: `src/ace_reel/ace/blendshape_map.py`
- Test: `tests/test_blendshape_map.py`

A2F-3D's gRPC stream sends blendshape **names once** in a header, then per-frame **weight arrays** in that order. This module turns `(names, weights)` into the `{name: weight}` dict our frame wants, dropping A2F's extra (non-ARKit-52) tongue shapes.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_blendshape_map.py
from ace_reel.ace.blendshape_map import to_arkit_dict

def test_maps_named_weight_array_to_dict():
    names = ["JawOpen", "EyeBlinkLeft", "TongueRollUp"]  # last is A2F-extra, not ARKit-52
    weights = [0.7, 0.2, 0.9]
    out = to_arkit_dict(names, weights)
    assert out == {"JawOpen": 0.7, "EyeBlinkLeft": 0.2}  # extra shape dropped

def test_clamps_weights_into_unit_range():
    out = to_arkit_dict(["JawOpen"], [1.4])
    assert out["JawOpen"] == 1.0
    out = to_arkit_dict(["JawOpen"], [-0.1])
    assert out["JawOpen"] == 0.0

def test_length_mismatch_raises():
    import pytest
    with pytest.raises(ValueError):
        to_arkit_dict(["JawOpen", "EyeBlinkLeft"], [0.5])
```

- [ ] **Step 2: Run** `pytest tests/test_blendshape_map.py -v` → FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/ace/blendshape_map.py
"""Map A2F-3D's (names, weights) blendshape stream onto the ARKit-52 pivot."""
from __future__ import annotations
from ace_reel.contracts.frame import _ARKIT_SET

def to_arkit_dict(names: list[str], weights: list[float]) -> dict[str, float]:
    if len(names) != len(weights):
        raise ValueError(f"names ({len(names)}) and weights ({len(weights)}) length mismatch")
    out: dict[str, float] = {}
    for name, w in zip(names, weights):
        if name in _ARKIT_SET:                 # drop A2F extras (extended tongue shapes etc.)
            out[name] = min(1.0, max(0.0, float(w)))
    return out
```

- [ ] **Step 4: Run** `pytest tests/test_blendshape_map.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/ace/blendshape_map.py tests/test_blendshape_map.py
git commit -m "feat(ace): A2F weight-array -> ARKit-52 blendshape map"
```

---

## Task 4: AceClient — Audio2Face-3D over hosted gRPC

**Files:**
- Create: `src/ace_reel/ace/ace_client.py`
- Test: `tests/test_ace_client.py`

> **Live-verify step (ground rule #1):** Before coding, fetch the current A2F-3D proto/SDK
> (`https://github.com/NVIDIA/Audio2Face-3D` + `https://docs.nvidia.com/ace/audio2face-3d-microservice/latest/text/interacting/a2f-rpc.html`),
> confirm the `nvidia-ace` package version exposing `ProcessAudioStream` / `AnimationDataStream`,
> and pin it in `pyproject.toml`. Record the pinned version in `docs/setup-nvidia-ace.md`.

The client has two seams so it's testable without a GPU/network: a **transport** (yields raw
`(names, weights, timecode, emotions)` tuples) and the **A2FClient** that wraps any transport into
`AnimationFrame`s. The real transport (`NvcfA2FTransport`) is exercised only by a `@live` test.

- [ ] **Step 1: Write the failing test (transport-agnostic core + ffmpeg helper)**

```python
# tests/test_ace_client.py
import os, pytest
from ace_reel.ace.ace_client import A2FClient, A2FRawFrame, to_pcm_16k_mono
from ace_reel.contracts.frame import AnimationFrame

class FakeTransport:
    def process(self, pcm, emotions):
        yield A2FRawFrame(names=["JawOpen"], weights=[0.6], timecode_s=0.0,
                          emotions={"joy": 0.4})
        yield A2FRawFrame(names=["JawOpen"], weights=[0.1], timecode_s=0.033,
                          emotions={"joy": 0.4})

def test_client_wraps_raw_frames_into_animation_frames():
    client = A2FClient(transport=FakeTransport())
    frames = list(client.stream(b"\x00\x00" * 16000))
    assert all(isinstance(f, AnimationFrame) for f in frames)
    assert frames[0].blendshapes["JawOpen"] == pytest.approx(0.6)
    assert frames[0].emotions["joy"] == pytest.approx(0.4)
    assert frames[1].timestamp_s == pytest.approx(0.033)

@pytest.mark.live
def test_live_hosted_a2f_returns_frames():
    if not os.getenv("NVIDIA_API_KEY"):
        pytest.skip("no NVIDIA_API_KEY")
    from ace_reel.ace.ace_client import NvcfA2FTransport
    pcm = to_pcm_16k_mono("tests/data/sample_vocal.wav")
    client = A2FClient(transport=NvcfA2FTransport())
    frames = list(client.stream(pcm))
    assert len(frames) > 10
    assert "JawOpen" in frames[0].blendshapes
```

- [ ] **Step 2: Run** `pytest tests/test_ace_client.py -v -m "not live"` → FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/ace/ace_client.py
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

    Wiring (verified against current proto in the Live-verify step):
      - metadata: ('authorization', f'Bearer {NVIDIA_API_KEY}'),
                  ('function-id', A2F_FUNCTION_ID)
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
        # Implemented + verified in Phase 2 against the pinned nvidia-ace proto; see docstring.
        raise NotImplementedError(
            "NvcfA2FTransport requires the pinned nvidia-ace proto; complete in Task 4 Step 6."
        )
```

- [ ] **Step 4: Run** `pytest tests/test_ace_client.py -v -m "not live"` → PASS (core wrapping verified with FakeTransport).

- [ ] **Step 5: Commit the verified core**

```bash
git add src/ace_reel/ace/ace_client.py tests/test_ace_client.py
git commit -m "feat(ace): A2FClient core (transport seam) + ffmpeg transcode; NVCF transport stubbed"
```

- [ ] **Step 6: Implement `NvcfA2FTransport.process` against the pinned proto, then verify live**

Fill `process()` using the `nvidia-ace` gRPC stubs confirmed in the Live-verify step. Place a short
royalty-free vocal at `tests/data/sample_vocal.wav`.
Run: `NVIDIA_API_KEY=… A2F_FUNCTION_ID=… pytest tests/test_ace_client.py -v -m live`
Expected: PASS — >10 frames, `JawOpen` present. (If no key available, leave `@live` skipped and
note in `docs/setup-nvidia-ace.md` that Phase 2 live-verify is pending a key.)

```bash
git add src/ace_reel/ace/ace_client.py docs/setup-nvidia-ace.md
git commit -m "feat(ace): live NVCF Audio2Face-3D transport"
```

---

## Task 5: Beat detection (motion)

**Files:**
- Create: `src/ace_reel/motion/beat.py`
- Test: `tests/test_beat.py`

NVIDIA ships no audio→dance, so we derive tempo ourselves (the `songs` table has no BPM column).

- [ ] **Step 1: Write the failing test (synthetic 120 BPM click track)**

```python
# tests/test_beat.py
import numpy as np, soundfile as sf, pytest
from ace_reel.motion.beat import detect_beats

def _make_click_track(path, bpm=120, sr=22050, seconds=8):
    n = sr * seconds
    audio = np.zeros(n, dtype=np.float32)
    step = int(sr * 60 / bpm)
    for i in range(0, n, step):
        audio[i:i+200] = 0.9            # short click
    sf.write(path, audio, sr)

def test_detects_tempo_and_beats(tmp_path):
    wav = tmp_path / "click.wav"
    _make_click_track(wav, bpm=120)
    result = detect_beats(str(wav))
    assert result.bpm == pytest.approx(120, abs=3)
    assert len(result.beat_times_s) >= 12
    assert all(b2 > b1 for b1, b2 in zip(result.beat_times_s, result.beat_times_s[1:]))
```

- [ ] **Step 2: Run** `pytest tests/test_beat.py -v` → FAIL. (Add `soundfile` to dev deps if missing.)

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/motion/beat.py
"""Tempo + beat-time detection via librosa (fallback for absent audio->dance service)."""
from __future__ import annotations
from dataclasses import dataclass
import librosa

@dataclass(frozen=True)
class BeatResult:
    bpm: float
    beat_times_s: list[float]

def detect_beats(audio_path: str) -> BeatResult:
    y, sr = librosa.load(audio_path, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return BeatResult(bpm=float(tempo), beat_times_s=[float(t) for t in beat_times])
```

- [ ] **Step 4: Run** `pytest tests/test_beat.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/motion/beat.py tests/test_beat.py
git commit -m "feat(motion): librosa tempo + beat detection"
```

---

## Task 6: Beat-synced clip planner (data only)

**Files:**
- Create: `src/ace_reel/motion/planner.py`
- Test: `tests/test_planner.py`

Maps beats → a timeline of dance-clip cues (`clip_name`, `start_s`, `energy`). The actual retarget
+ playback is UE-side (`docs/setup-reel-engine.md`); here we emit the *plan* the engine consumes.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_planner.py
from ace_reel.motion.beat import BeatResult
from ace_reel.motion.planner import plan_dance

def test_plans_one_clip_cue_per_bar():
    beats = BeatResult(bpm=120, beat_times_s=[0.0,0.5,1.0,1.5,2.0,2.5,3.0,3.5])  # 8 beats
    cues = plan_dance(beats, clips=["sway", "step"], beats_per_bar=4)
    assert len(cues) == 2                       # 8 beats / 4 = 2 bars
    assert cues[0].start_s == 0.0 and cues[1].start_s == 2.0
    assert cues[0].clip_name in ("sway", "step")
    assert 0.0 <= cues[0].energy <= 1.0

def test_energy_scales_with_tempo():
    slow = plan_dance(BeatResult(60, [0,1,2,3,4]), clips=["a"], beats_per_bar=4)
    fast = plan_dance(BeatResult(160, [0,0.375,0.75,1.125,1.5]), clips=["a"], beats_per_bar=4)
    assert fast[0].energy > slow[0].energy
```

- [ ] **Step 2: Run** `pytest tests/test_planner.py -v` → FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/motion/planner.py
"""Turn detected beats into a beat-synced dance-clip timeline (consumed by the render engine)."""
from __future__ import annotations
from dataclasses import dataclass
from ace_reel.motion.beat import BeatResult

@dataclass(frozen=True)
class ClipCue:
    clip_name: str
    start_s: float
    energy: float          # 0..1, drives playback rate / amplitude in-engine

def plan_dance(beats: BeatResult, clips: list[str], beats_per_bar: int = 4) -> list[ClipCue]:
    if not clips:
        raise ValueError("need at least one dance clip")
    energy = min(1.0, max(0.0, (beats.bpm - 60) / 120))   # 60bpm→0, 180bpm→1
    cues: list[ClipCue] = []
    for bar_idx, i in enumerate(range(0, len(beats.beat_times_s), beats_per_bar)):
        cues.append(ClipCue(clip_name=clips[bar_idx % len(clips)],
                            start_s=beats.beat_times_s[i], energy=energy))
    return cues
```

- [ ] **Step 4: Run** `pytest tests/test_planner.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/motion/planner.py tests/test_planner.py
git commit -m "feat(motion): beat-synced dance-clip planner"
```

---

## Task 7: RenderTarget base — NullRenderTarget

**Files:**
- Create: `src/ace_reel/render/base.py`
- Test: `tests/test_render.py`

`NullRenderTarget` is the Mac-runnable sink: it records frames (for tests + the `null` CLI engine).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_render.py
from ace_reel.render.base import NullRenderTarget
from ace_reel.contracts.frame import AnimationFrame

def _frame(ts): return AnimationFrame(timestamp_s=ts, blendshapes={"JawOpen":0.3}, emotions={}, body_pose=None)

def test_null_target_records_open_frames_close_in_order():
    t = NullRenderTarget()
    t.run("Avatar_Claire", b"\x00\x00", [_frame(0.0), _frame(0.033)])
    assert t.opened_with == ("Avatar_Claire", 2)        # asset, audio byte-count
    assert [f.timestamp_s for f in t.received] == [0.0, 0.033]
    assert t.closed is True
```

- [ ] **Step 2: Run** `pytest tests/test_render.py -v` → FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/render/base.py
"""NullRenderTarget — engine-less sink used on the Mac and in tests."""
from __future__ import annotations
from ace_reel.contracts.interfaces import RenderTarget
from ace_reel.contracts.frame import AnimationFrame

class NullRenderTarget(RenderTarget):
    def __init__(self) -> None:
        self.opened_with: tuple[str, int] | None = None
        self.received: list[AnimationFrame] = []
        self.closed = False

    def open(self, avatar_asset: str, audio_pcm_16k_mono: bytes) -> None:
        self.opened_with = (avatar_asset, len(audio_pcm_16k_mono))

    def push(self, frame: AnimationFrame) -> None:
        self.received.append(frame)

    def close(self) -> None:
        self.closed = True
```

- [ ] **Step 4: Run** `pytest tests/test_render.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/render/base.py tests/test_render.py
git commit -m "feat(render): NullRenderTarget engine-less sink"
```

---

## Task 8: UnrealRenderTarget — documented stub (Win/RTX)

**Files:**
- Create: `src/ace_reel/render/unreal_livelink.py`
- Test: `tests/test_unreal_stub.py`

Conforms to `RenderTarget` so the orchestrator/CLI accept it, but raises a clear, doc-pointing error
on `open()` off Windows. The docstring captures the real wiring (`Apply ACE Face Animations` →
`Face_AnimBP`) for whoever finishes it on the RTX box.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_unreal_stub.py
import pytest
from ace_reel.render.unreal_livelink import UnrealRenderTarget
from ace_reel.contracts.interfaces import RenderTarget

def test_is_a_render_target():
    assert issubclass(UnrealRenderTarget, RenderTarget)

def test_open_raises_clear_unsupported_error():
    t = UnrealRenderTarget()
    with pytest.raises(NotImplementedError) as e:
        t.open("Avatar_Claire", b"\x00\x00")
    assert "Windows" in str(e.value) and "setup-reel-engine" in str(e.value)
```

- [ ] **Step 2: Run** `pytest tests/test_unreal_stub.py -v` → FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/render/unreal_livelink.py
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
```

- [ ] **Step 4: Run** `pytest tests/test_unreal_stub.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/render/unreal_livelink.py tests/test_unreal_stub.py
git commit -m "feat(render): UnrealRenderTarget interface-conforming stub + wiring docstring"
```

---

## Task 9: AImyMusicSunoSource (Supabase)

**Files:**
- Create: `src/ace_reel/music/aimymusic_suno.py`
- Test: `tests/test_music_source.py`

Reads the canonical `songs` table (`xltunldffphrlqstujyg`) and signs `audio_path` from the
`personal-library` bucket. Split into a **gateway** seam (DB/storage calls) so logic is unit-testable
without network; a `@live` test hits real Supabase when creds are set.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_music_source.py
import os, pytest
from ace_reel.music.aimymusic_suno import AImyMusicSunoSource
from ace_reel.contracts.interfaces import Track

class FakeGateway:
    def fetch_song(self, track_id):
        return {"id": track_id, "title": "Neon", "duration_seconds": 200,
                "audio_path": "songs/neon.mp3"}
    def sign_url(self, path):
        return f"https://signed/{path}"
    def download(self, url):
        return b"ID3audio"

def test_get_track_maps_row_to_track():
    src = AImyMusicSunoSource(gateway=FakeGateway())
    t = src.get_track("abc")
    assert isinstance(t, Track)
    assert t.title == "Neon" and t.duration_s == 200
    assert t.audio_url == "https://signed/songs/neon.mp3" and t.bpm is None

def test_read_audio_downloads_signed_url():
    src = AImyMusicSunoSource(gateway=FakeGateway())
    assert src.read_audio(src.get_track("abc")) == b"ID3audio"

@pytest.mark.live
def test_live_fetches_real_song():
    if not os.getenv("SUPABASE_SERVICE_KEY"):
        pytest.skip("no SUPABASE_SERVICE_KEY")
    src = AImyMusicSunoSource.from_env()
    # smallest stable assertion: a known visible song id resolves with a non-empty title
    # (replace KNOWN_ID after picking one via the songs table)
    t = src.get_track(os.environ["SUNO_TEST_TRACK_ID"])
    assert t.title and t.audio_url.startswith("http")
```

- [ ] **Step 2: Run** `pytest tests/test_music_source.py -v -m "not live"` → FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/music/aimymusic_suno.py
"""MusicSource over the AImyMusic Suno library (Supabase songs + personal-library bucket)."""
from __future__ import annotations
import os
import urllib.request
from ace_reel.contracts.interfaces import MusicSource, Track

class SupabaseGateway:
    """Thin seam over supabase-py + storage (kept tiny so the source is testable with a fake)."""
    def __init__(self, url: str, key: str, bucket: str):
        from supabase import create_client
        self._sb = create_client(url, key)
        self._bucket = bucket
    def fetch_song(self, track_id: str) -> dict:
        res = self._sb.table("songs").select(
            "id,title,duration_seconds,audio_path").eq("id", track_id).single().execute()
        return res.data
    def sign_url(self, path: str) -> str:
        signed = self._sb.storage.from_(self._bucket).create_signed_url(path, 3600)
        return signed["signedURL"]
    def download(self, url: str) -> bytes:
        with urllib.request.urlopen(url) as r:
            return r.read()

class AImyMusicSunoSource(MusicSource):
    def __init__(self, gateway):
        self._gw = gateway

    @classmethod
    def from_env(cls) -> "AImyMusicSunoSource":
        return cls(SupabaseGateway(os.environ["SUPABASE_URL"],
                                   os.environ["SUPABASE_SERVICE_KEY"],
                                   os.environ.get("SUNO_AUDIO_BUCKET", "personal-library")))

    def get_track(self, track_id: str) -> Track:
        row = self._gw.fetch_song(track_id)
        return Track(id=row["id"], title=row["title"],
                     duration_s=int(row["duration_seconds"] or 0),
                     audio_url=self._gw.sign_url(row["audio_path"]), bpm=None)

    def read_audio(self, track: Track) -> bytes:
        return self._gw.download(track.audio_url)
```

- [ ] **Step 4: Run** `pytest tests/test_music_source.py -v -m "not live"` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/music/aimymusic_suno.py tests/test_music_source.py
git commit -m "feat(music): AImyMusicSunoSource over Supabase songs + personal-library"
```

---

## Task 10: Orchestrator + CLI

**Files:**
- Create: `src/ace_reel/orchestrator.py`, `src/ace_reel/cli.py`, `tests/fakes.py`
- Test: `tests/test_orchestrator.py`, `tests/test_cli.py`

- [ ] **Step 1: Write `tests/fakes.py` + the failing orchestrator test**

```python
# tests/fakes.py
from ace_reel.contracts.interfaces import MusicSource, AceClient, Track
from ace_reel.contracts.frame import AnimationFrame
from ace_reel.render.base import NullRenderTarget

class FakeMusicSource(MusicSource):
    def get_track(self, track_id): return Track(track_id, "Fake", 10, "https://x/a.mp3")
    def read_audio(self, track): return b"SRCAUDIO"

class FakeAceClient(AceClient):
    def stream(self, pcm_16k_mono, emotions=None):
        yield AnimationFrame(timestamp_s=0.0, blendshapes={"JawOpen":0.5}, emotions={}, body_pose=None)
        yield AnimationFrame(timestamp_s=0.033, blendshapes={"JawOpen":0.1}, emotions={}, body_pose=None)
```

```python
# tests/test_orchestrator.py
from ace_reel.orchestrator import Orchestrator
from ace_reel.render.base import NullRenderTarget
from tests.fakes import FakeMusicSource, FakeAceClient

def test_perform_pipes_music_through_ace_into_render(monkeypatch):
    # stub transcode so no ffmpeg needed in unit test
    import ace_reel.orchestrator as orch
    monkeypatch.setattr(orch, "to_pcm_16k_mono_bytes", lambda src: b"PCM16K")
    target = NullRenderTarget()
    Orchestrator(FakeMusicSource(), FakeAceClient(), target).perform("track1", "Avatar_Claire")
    assert target.opened_with == ("Avatar_Claire", len(b"PCM16K"))
    assert [f.timestamp_s for f in target.received] == [0.0, 0.033]
    assert target.closed is True
```

- [ ] **Step 2: Run** `pytest tests/test_orchestrator.py -v` → FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/orchestrator.py
"""Stream a song through ACE into a render target."""
from __future__ import annotations
import subprocess
from ace_reel.contracts.interfaces import MusicSource, AceClient, RenderTarget

def to_pcm_16k_mono_bytes(src_audio: bytes) -> bytes:
    """ffmpeg transcode from in-memory source bytes to PCM s16le mono 16 kHz."""
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le",
         "-ac", "1", "-ar", "16000", "pipe:1"],
        input=src_audio, check=True, stdout=subprocess.PIPE,
    )
    return p.stdout

class Orchestrator:
    def __init__(self, music: MusicSource, ace: AceClient, render: RenderTarget):
        self._music, self._ace, self._render = music, ace, render

    def perform(self, track_id: str, avatar_asset: str,
                emotions: dict[str, float] | None = None) -> None:
        track = self._music.get_track(track_id)
        pcm = to_pcm_16k_mono_bytes(self._music.read_audio(track))
        frames = self._ace.stream(pcm, emotions)
        self._render.run(avatar_asset, pcm, frames)
```

- [ ] **Step 4: Run** `pytest tests/test_orchestrator.py -v` → PASS.

- [ ] **Step 5: Write the failing CLI test**

```python
# tests/test_cli.py
from click.testing import CliRunner
from ace_reel.cli import main

def test_cli_null_engine_smoke(monkeypatch):
    import ace_reel.cli as cli
    from tests.fakes import FakeMusicSource, FakeAceClient
    monkeypatch.setattr(cli, "build_music_source", lambda: FakeMusicSource())
    monkeypatch.setattr(cli, "build_ace_client", lambda: FakeAceClient())
    monkeypatch.setattr("ace_reel.orchestrator.to_pcm_16k_mono_bytes", lambda b: b"PCM")
    r = CliRunner().invoke(main, ["--track", "t1", "--avatar", "Avatar_Claire", "--engine", "null"])
    assert r.exit_code == 0
    assert "2 frames" in r.output
```

- [ ] **Step 6: Run** `pytest tests/test_cli.py -v` → FAIL.

- [ ] **Step 7: Write the CLI**

```python
# src/ace_reel/cli.py
"""`perform` — one command to play a library track as an avatar performance."""
from __future__ import annotations
import click
from ace_reel.orchestrator import Orchestrator
from ace_reel.render.base import NullRenderTarget
from ace_reel.render.unreal_livelink import UnrealRenderTarget

def build_music_source():
    from ace_reel.music.aimymusic_suno import AImyMusicSunoSource
    return AImyMusicSunoSource.from_env()

def build_ace_client():
    from ace_reel.ace.ace_client import A2FClient, NvcfA2FTransport
    return A2FClient(transport=NvcfA2FTransport())

def _render(engine: str):
    return NullRenderTarget() if engine == "null" else UnrealRenderTarget()

@click.command()
@click.option("--track", required=True, help="Suno songs.id")
@click.option("--avatar", required=True, help="Avatar/MetaHuman asset name")
@click.option("--engine", type=click.Choice(["null", "unreal"]), default="null")
def main(track: str, avatar: str, engine: str):
    target = _render(engine)
    Orchestrator(build_music_source(), build_ace_client(), target).perform(track, avatar)
    n = len(target.received) if isinstance(target, NullRenderTarget) else "?"
    click.echo(f"performed track {track} on {avatar} [{engine}] -> {n} frames")

if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Run** `pytest tests/test_cli.py -v` → PASS.

- [ ] **Step 9: Run the whole suite**

Run: `pytest -m "not live" -v`
Expected: all non-live tests PASS.

- [ ] **Step 10: Commit**

```bash
git add src/ace_reel/orchestrator.py src/ace_reel/cli.py tests/fakes.py tests/test_orchestrator.py tests/test_cli.py
git commit -m "feat: orchestrator + perform CLI wiring music->ace->render"
```

---

## Task 11: Docs + README (template story)

**Files:**
- Create: `docs/01-architecture.md`, `docs/setup-nvidia-ace.md`, `docs/setup-reel-engine.md`, `docs/add-a-render-target.md`, `README.md`

- [ ] **Step 1: `docs/01-architecture.md`** — the adapter diagram (from the prompt), the `AnimationFrame` contract, and the "ACE is face-only; dancing = beat-synced clips" decision with the discovery-doc cross-reference.
- [ ] **Step 2: `docs/setup-nvidia-ace.md`** — get an `nvapi-` key, the three A2F function-ids (Claire/Mark/James), the pinned `nvidia-ace` version, and how to run the `@live` AceClient test.
- [ ] **Step 3: `docs/setup-reel-engine.md`** — Windows/RTX + UE 5.6 + ACE plugin 2.5 + MetaHuman import + `Apply ACE Face Animations`/`mh_arkit_mapping_pose_A2F` wiring + IK-retarget dance clips + Movie Render Queue reel export (1080×1920). Mark every step "Windows/RTX only."
- [ ] **Step 4: `docs/add-a-render-target.md`** — implement `RenderTarget` (open/push/close), register it in `cli._render`; show `NullRenderTarget` as the reference impl. This is the "it's a template" payoff.
- [ ] **Step 5: `README.md`** — quickstart (`pip install -e ".[dev]"`, `pytest -m "not live"`, `perform --track <id> --avatar <name> --engine null`), the template story, and the hardware reality (Mac = spine + orchestration; Win/RTX = render).
- [ ] **Step 6: Commit**

```bash
git add docs README.md && git commit -m "docs: architecture, setup guides, template extension guide"
```

---

## Self-Review

**Spec coverage** (vs prompt + agreed scope):
- Phase 1 skeleton & contracts → Tasks 0–2 ✅ (AnimationFrame = ARKit-52 + emotion + timestamp + optional body pose; three interfaces; `.env.example`).
- Phase 2 ACE singing → Tasks 3–4 ✅ (hosted A2F first; self-host path documented; latency/live-verify in Task 4 Step 6).
- Phase 3 Unreal bridge → Task 8 ✅ as documented stub (per agreed Mac scope; real verify deferred to Win/RTX in `setup-reel-engine.md`).
- Phase 4 dancing → Tasks 5–6 ✅ (beat detection + clip planner = the prompt's explicit fallback, since discovery confirmed no audio→dance).
- Phase 5 AImyMusic source → Task 9 ✅ (canonical `songs` + `personal-library`; full-mix to A2F; stem separation flagged future).
- Phase 6 two run modes + template polish → Tasks 10–11 ✅ (null/unreal engines, one-command CLI, add-a-render-target guide; reel-export documented Win-side).
- Ground rules: research-first (Phase 0 done) ✅; adapter boundaries ✅; no secrets (env + `.env.example`) ✅; streaming `AceClient.stream` iterator ✅; verify-by-running (non-live suite + `@live` gates) ✅.

**Placeholder scan:** All code steps contain runnable code. The two intentional `NotImplementedError`s (NVCF transport pre-live, Unreal stub) are explicit, tested, and scoped — not silent placeholders.

**Type consistency:** `AnimationFrame(timestamp_s, blendshapes, emotions, body_pose)`, `Track(id,title,duration_s,audio_url,bpm)`, `AceClient.stream`, `RenderTarget.open/push/close/run`, `to_pcm_16k_mono_bytes`, `to_arkit_dict`, `BeatResult`, `ClipCue` — names match across all tasks.

**Known follow-ups (out of this session's Mac scope):** live A2F verify needs an `nvapi-` key; live music test needs a Supabase service key + a chosen `SUNO_TEST_TRACK_ID`; the entire UE5 render/dance/reel path needs a Windows/RTX box.
