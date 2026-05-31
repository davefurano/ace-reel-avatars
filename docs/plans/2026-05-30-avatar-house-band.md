# Avatar House Band Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Mac-buildable band layer that drives a fixed multi-avatar "house band" performance from a single AImyMusic Suno track — lead vocalist lip-syncs (A2F), instrumentalists move/play on a beat grid.

**Architecture:** A new `src/ace_reel/band/` package (roster → arranger → performance → orchestrator) composes existing units (`detect_beats`, `plan_dance`, `A2FClient`, `to_pcm_16k_mono_bytes`) with minimal new logic, plus a multi-avatar `BandRenderTarget` contract (Null sink + Unreal stub) mirroring the single-avatar `RenderTarget` pattern. Instrument motion is beat-grid-derived (believable, not note-accurate).

**Tech Stack:** Python 3.11, pydantic/dataclasses, librosa (reused), click (CLI), pytest (TDD). No new dependencies.

**Spec:** `docs/specs/2026-05-30-avatar-house-band-design.md`. Reuse map + boundaries there.

---

## File Structure

```
src/ace_reel/band/
  __init__.py
  roster.py         # Role enum, Member, Band, load_band(path)              — Task 1, 2
  arranger.py       # ROLE_BEATS_PER_CUE, BandArranger.arrange (pure)        — Task 3
  performance.py    # BandPerformance dataclass                              — Task 4
  orchestrator.py   # BandOrchestrator.perform(track_id, band)               — Task 6
src/ace_reel/render/
  band_base.py      # BandRenderTarget ABC + NullBandRenderTarget            — Task 5
  unreal_band.py    # UnrealBandRenderTarget (Win/RTX stub, preflight)       — Task 5
bands/
  house.json        # default house-band roster                             — Task 7
src/ace_reel/cli.py # add `band-perform` command (modify)                    — Task 7
tests/
  test_band_roster.py  test_band_arranger.py  test_band_render.py
  test_band_orchestrator.py  test_band_cli.py
  fakes.py          # extend with FakeBandRenderTarget helpers if needed     — Task 6
```

Existing types reused (do NOT redefine): `ace_reel.motion.beat.BeatResult`/`detect_beats`,
`ace_reel.motion.planner.plan_dance`/`ClipCue`, `ace_reel.contracts.frame.AnimationFrame`,
`ace_reel.contracts.interfaces.{Track, MusicSource, AceClient}`,
`ace_reel.orchestrator.to_pcm_16k_mono_bytes`, `ace_reel.render.base.NullRenderTarget` (as pattern).

---

## Task 1: Roles & Member/Band model

**Files:**
- Create: `src/ace_reel/band/__init__.py` (empty)
- Create: `src/ace_reel/band/roster.py`
- Test: `tests/test_band_roster.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_band_roster.py
import pytest
from ace_reel.band.roster import Role, Member, Band

def test_member_is_hashable_with_tuple_clips():
    m = Member(avatar="Avatar_Mark", role=Role.GUITAR, clips=("strum_down", "strum_up"))
    assert {m: 1}[m] == 1                 # usable as a dict key
    assert m.role is Role.GUITAR

def test_band_partitions_vocalist_and_instrumentalists():
    v = Member("Claire", Role.VOCALS, ())
    g = Member("Mark", Role.GUITAR, ("strum",))
    d = Member("Beat", Role.DRUMS, ("kick",))
    band = Band(name="House", members=[v, g, d])
    assert band.vocalist is v
    assert band.instrumentalists == [g, d]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `. .venv/bin/activate && python -m pytest tests/test_band_roster.py -v`
Expected: FAIL — `ModuleNotFoundError: ace_reel.band.roster`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/band/roster.py
"""House-band roster: roles, members, and the band that performs a track."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class Role(Enum):
    VOCALS = "vocals"
    GUITAR = "guitar"
    BASS = "bass"
    DRUMS = "drums"
    KEYS = "keys"

@dataclass(frozen=True)
class Member:
    avatar: str
    role: Role
    clips: tuple[str, ...] = ()      # tuple (not list) so Member stays hashable / dict-key-able

@dataclass(frozen=True)
class Band:
    name: str
    members: list[Member] = field(default_factory=list)

    @property
    def vocalist(self) -> Member:
        return next(m for m in self.members if m.role is Role.VOCALS)

    @property
    def instrumentalists(self) -> list[Member]:
        return [m for m in self.members if m.role is not Role.VOCALS]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_band_roster.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/band/__init__.py src/ace_reel/band/roster.py tests/test_band_roster.py
git commit -m "feat(band): Role/Member/Band roster model"
```

---

## Task 2: load_band with validation

**Files:**
- Modify: `src/ace_reel/band/roster.py` (add `load_band`)
- Test: `tests/test_band_roster.py` (add cases)

- [ ] **Step 1: Write the failing test (append to tests/test_band_roster.py)**

```python
import json
from ace_reel.band.roster import load_band

def _write(tmp_path, obj):
    p = tmp_path / "band.json"
    p.write_text(json.dumps(obj))
    return str(p)

def test_load_band_parses_roles_and_clips(tmp_path):
    path = _write(tmp_path, {"name": "House", "members": [
        {"avatar": "Claire", "role": "vocals"},
        {"avatar": "Mark", "role": "guitar", "clips": ["strum_down", "strum_up"]},
    ]})
    band = load_band(path)
    assert band.name == "House"
    assert band.vocalist.avatar == "Claire"
    assert band.instrumentalists[0].clips == ("strum_down", "strum_up")  # list -> tuple

def test_load_band_rejects_zero_vocalists(tmp_path):
    path = _write(tmp_path, {"name": "x", "members": [
        {"avatar": "Mark", "role": "guitar", "clips": ["s"]}]})
    with pytest.raises(ValueError, match="exactly one vocalist"):
        load_band(path)

def test_load_band_rejects_multiple_vocalists(tmp_path):
    path = _write(tmp_path, {"name": "x", "members": [
        {"avatar": "A", "role": "vocals"}, {"avatar": "B", "role": "vocals"}]})
    with pytest.raises(ValueError, match="exactly one vocalist"):
        load_band(path)

def test_load_band_rejects_unknown_role(tmp_path):
    path = _write(tmp_path, {"name": "x", "members": [
        {"avatar": "A", "role": "vocals"}, {"avatar": "B", "role": "triangle", "clips": ["t"]}]})
    with pytest.raises(ValueError, match="unknown role"):
        load_band(path)

def test_load_band_rejects_instrumentalist_without_clips(tmp_path):
    path = _write(tmp_path, {"name": "x", "members": [
        {"avatar": "A", "role": "vocals"}, {"avatar": "B", "role": "drums", "clips": []}]})
    with pytest.raises(ValueError, match="needs at least one clip"):
        load_band(path)
```

- [ ] **Step 2: Run** `python -m pytest tests/test_band_roster.py -v` → new tests FAIL (`load_band` missing).

- [ ] **Step 3: Write minimal implementation (append to roster.py)**

```python
import json

def load_band(path: str) -> Band:
    """Parse + validate a band JSON config into a Band."""
    with open(path) as f:
        data = json.load(f)
    members: list[Member] = []
    for raw in data.get("members", []):
        role_str = raw["role"]
        try:
            role = Role(role_str)
        except ValueError:
            raise ValueError(f"unknown role: {role_str!r}") from None
        clips = tuple(raw.get("clips", ()))
        if role is not Role.VOCALS and not clips:
            raise ValueError(f"instrumentalist {raw['avatar']!r} ({role_str}) needs at least one clip")
        members.append(Member(avatar=raw["avatar"], role=role, clips=clips))
    vocalists = [m for m in members if m.role is Role.VOCALS]
    if len(vocalists) != 1:
        raise ValueError(f"band must have exactly one vocalist, found {len(vocalists)}")
    return Band(name=data.get("name", "Band"), members=members)
```

- [ ] **Step 4: Run** `python -m pytest tests/test_band_roster.py -v` → PASS (all roster tests).

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/band/roster.py tests/test_band_roster.py
git commit -m "feat(band): load_band JSON parser with roster validation"
```

---

## Task 3: BandArranger (beat-grid instrument cues)

**Files:**
- Create: `src/ace_reel/band/arranger.py`
- Test: `tests/test_band_arranger.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_band_arranger.py
from ace_reel.motion.beat import BeatResult
from ace_reel.band.roster import Role, Member, Band
from ace_reel.band.arranger import BandArranger

def _band():
    return Band("House", [
        Member("Claire", Role.VOCALS, ()),
        Member("Mark", Role.GUITAR, ("g1", "g2")),
        Member("Beat", Role.DRUMS, ("kick", "snare")),
    ])

def test_arrange_excludes_vocalist_and_keys_by_member():
    beats = BeatResult(bpm=120, beat_times_s=[i * 0.5 for i in range(8)])  # 8 beats
    arr = BandArranger().arrange(beats, _band())
    avatars = {m.avatar for m in arr}
    assert avatars == {"Mark", "Beat"}        # vocalist excluded; keyed by Member

def test_drums_get_one_cue_per_beat_guitar_one_per_bar():
    beats = BeatResult(bpm=120, beat_times_s=[i * 0.5 for i in range(8)])  # 8 beats
    arr = BandArranger().arrange(beats, _band())
    drums = next(c for m, c in arr.items() if m.role is Role.DRUMS)
    guitar = next(c for m, c in arr.items() if m.role is Role.GUITAR)
    assert len(drums) == 8                    # DRUMS = 1 beat/cue
    assert len(guitar) == 2                   # GUITAR = 4 beats/bar -> 8/4 = 2

def test_energy_scales_with_tempo():
    fast = BandArranger().arrange(BeatResult(180, [i*0.33 for i in range(8)]), _band())
    slow = BandArranger().arrange(BeatResult(60, [i*1.0 for i in range(8)]), _band())
    fast_drum = next(c for m, c in fast.items() if m.role is Role.DRUMS)[0]
    slow_drum = next(c for m, c in slow.items() if m.role is Role.DRUMS)[0]
    assert fast_drum.energy > slow_drum.energy
```

- [ ] **Step 2: Run** `python -m pytest tests/test_band_arranger.py -v` → FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/band/arranger.py
"""Turn a track's beats into per-instrumentalist beat-synced cue timelines (pure, no I/O)."""
from __future__ import annotations
from ace_reel.motion.beat import BeatResult
from ace_reel.motion.planner import plan_dance, ClipCue
from ace_reel.band.roster import Role, Member, Band

# How many beats elapse per emitted cue, per instrument role.
ROLE_BEATS_PER_CUE: dict[Role, int] = {
    Role.DRUMS: 1,
    Role.BASS: 2,
    Role.GUITAR: 4,
    Role.KEYS: 4,
}

class BandArranger:
    def arrange(self, beats: BeatResult, band: Band) -> dict[Member, list[ClipCue]]:
        out: dict[Member, list[ClipCue]] = {}
        for member in band.instrumentalists:
            per_cue = ROLE_BEATS_PER_CUE[member.role]
            out[member] = plan_dance(beats, list(member.clips), beats_per_bar=per_cue)
        return out
```

- [ ] **Step 4: Run** `python -m pytest tests/test_band_arranger.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/band/arranger.py tests/test_band_arranger.py
git commit -m "feat(band): BandArranger beat-grid instrument cue timelines"
```

---

## Task 4: BandPerformance dataclass

**Files:**
- Create: `src/ace_reel/band/performance.py`
- Test: `tests/test_band_render.py` (a construction test; render target follows in Task 5)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_band_render.py
from ace_reel.band.performance import BandPerformance
from ace_reel.band.roster import Role, Member
from ace_reel.contracts.interfaces import Track
from ace_reel.contracts.frame import AnimationFrame

def _vocal_frames():
    yield AnimationFrame(timestamp_s=0.0, blendshapes={"JawOpen": 0.5}, emotions={}, body_pose=None)

def test_band_performance_holds_its_parts():
    v = Member("Claire", Role.VOCALS, ())
    perf = BandPerformance(
        track=Track("t1", "Song", 200, "https://x/a.mp3"),
        audio_pcm=b"PCM",
        vocalist=v,
        vocal_frames=_vocal_frames(),
        instrument_arrangement={},
    )
    assert perf.vocalist is v
    assert perf.audio_pcm == b"PCM"
    assert list(perf.vocal_frames)[0].blendshapes["JawOpen"] == 0.5
```

- [ ] **Step 2: Run** `python -m pytest tests/test_band_render.py -v` → FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/band/performance.py
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
    audio_pcm: bytes                                  # 16k mono — the shared sync reference
    vocalist: Member
    vocal_frames: Iterable[AnimationFrame]            # streamed A2F output
    instrument_arrangement: dict[Member, list[ClipCue]]
```

- [ ] **Step 4: Run** `python -m pytest tests/test_band_render.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/band/performance.py tests/test_band_render.py
git commit -m "feat(band): BandPerformance dataclass"
```

---

## Task 5: BandRenderTarget ABC + Null sink + Unreal stub

**Files:**
- Create: `src/ace_reel/render/band_base.py`
- Create: `src/ace_reel/render/unreal_band.py`
- Test: `tests/test_band_render.py` (append)

- [ ] **Step 1: Write the failing test (append to tests/test_band_render.py)**

```python
import pytest, sys
from ace_reel.render.band_base import BandRenderTarget, NullBandRenderTarget
from ace_reel.render.unreal_band import UnrealBandRenderTarget
from ace_reel.band.roster import Role, Member, Band
from ace_reel.motion.planner import ClipCue

def test_null_band_target_records_members_audio_frames_close():
    v = Member("Claire", Role.VOCALS, ())
    g = Member("Mark", Role.GUITAR, ("g1",))
    arrangement = {g: [ClipCue("g1", 0.0, 0.5)]}
    perf = BandPerformance(
        track=Track("t1", "S", 10, "https://x/a.mp3"),
        audio_pcm=b"PCMPCM",
        vocalist=v,
        vocal_frames=[
            AnimationFrame(timestamp_s=0.0, blendshapes={"JawOpen": 0.5}, emotions={}, body_pose=None),
            AnimationFrame(timestamp_s=0.03, blendshapes={"JawOpen": 0.1}, emotions={}, body_pose=None),
        ],
        instrument_arrangement=arrangement,
    )
    t = NullBandRenderTarget()
    t.run(perf)
    assert t.opened_with == ([v, g], len(b"PCMPCM"), arrangement)
    assert [f.timestamp_s for f in t.vocal_received] == [0.0, 0.03]
    assert t.closed is True

def test_unreal_band_is_a_band_render_target_and_preflight_rejects_off_windows():
    assert issubclass(UnrealBandRenderTarget, BandRenderTarget)
    t = UnrealBandRenderTarget()
    if sys.platform == "win32":
        pytest.skip("preflight only rejects off-Windows")
    with pytest.raises(NotImplementedError) as e:
        t.preflight()
    assert "Windows" in str(e.value) and "setup-reel-engine" in str(e.value)
```

(Note: this test references `BandPerformance`, `Track`, `AnimationFrame` already imported at the top
of `tests/test_band_render.py` from Task 4. Ensure `from ace_reel.contracts.interfaces import Track`
and `from ace_reel.contracts.frame import AnimationFrame` are present — they are, from Task 4 Step 1.)

- [ ] **Step 2: Run** `python -m pytest tests/test_band_render.py -v` → new tests FAIL (modules missing).

- [ ] **Step 3: Write minimal implementations**

```python
# src/ace_reel/render/band_base.py
"""Multi-avatar render contract: open a band scene, stream the vocalist's face, close."""
from __future__ import annotations
from abc import ABC, abstractmethod
from ace_reel.contracts.frame import AnimationFrame
from ace_reel.band.roster import Member
from ace_reel.motion.planner import ClipCue
from ace_reel.band.performance import BandPerformance

class BandRenderTarget(ABC):
    @abstractmethod
    def open(self, members: list[Member], audio_pcm: bytes,
             instrument_arrangement: dict[Member, list[ClipCue]]) -> None: ...
    @abstractmethod
    def push_vocal_frame(self, frame: AnimationFrame) -> None: ...
    @abstractmethod
    def close(self) -> None: ...

    def preflight(self) -> None:
        """Optional early check (platform/deps) before any audio is processed; default no-op."""

    def run(self, perf: BandPerformance) -> None:
        self.preflight()
        members = [perf.vocalist, *perf.instrument_arrangement.keys()]
        self.open(members, perf.audio_pcm, perf.instrument_arrangement)
        try:
            for frame in perf.vocal_frames:
                self.push_vocal_frame(frame)
        finally:
            self.close()

class NullBandRenderTarget(BandRenderTarget):
    def __init__(self) -> None:
        self.opened_with: tuple[list[Member], int, dict] | None = None
        self.vocal_received: list[AnimationFrame] = []
        self.closed = False

    def open(self, members, audio_pcm, instrument_arrangement) -> None:
        self.opened_with = (members, len(audio_pcm), instrument_arrangement)

    def push_vocal_frame(self, frame) -> None:
        self.vocal_received.append(frame)

    def close(self) -> None:
        self.closed = True
```

```python
# src/ace_reel/render/unreal_band.py
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
```

- [ ] **Step 4: Run** `python -m pytest tests/test_band_render.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/render/band_base.py src/ace_reel/render/unreal_band.py tests/test_band_render.py
git commit -m "feat(render): BandRenderTarget ABC + NullBandRenderTarget + Unreal band stub"
```

---

## Task 6: BandOrchestrator

**Files:**
- Create: `src/ace_reel/band/orchestrator.py`
- Test: `tests/test_band_orchestrator.py`

The orchestrator needs beats from the decoded source audio. `detect_beats` takes a path, so the
orchestrator writes the source bytes to a temp file, detects, and cleans up. The test monkeypatches
both `detect_beats` (no real audio) and the temp-file write is exercised via a real (tiny) temp file
or bypassed — here we monkeypatch `detect_beats` to ignore the path, so any temp file works.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_band_orchestrator.py
from ace_reel.band.orchestrator import BandOrchestrator
from ace_reel.band.roster import Role, Member, Band
from ace_reel.motion.beat import BeatResult
from ace_reel.render.band_base import NullBandRenderTarget
from tests.fakes import FakeMusicSource, FakeAceClient

def _band():
    return Band("House", [
        Member("Claire", Role.VOCALS, ()),
        Member("Mark", Role.GUITAR, ("g1",)),
        Member("Beat", Role.DRUMS, ("kick",)),
    ])

def test_band_perform_wires_music_beats_ace_into_band_render(monkeypatch):
    import ace_reel.band.orchestrator as bo
    # no ffmpeg / no librosa: stub transcode + beat detection
    monkeypatch.setattr(bo, "to_pcm_16k_mono_bytes", lambda src: b"PCM16K")
    monkeypatch.setattr(bo, "detect_beats", lambda path: BeatResult(120, [i * 0.5 for i in range(8)]))
    target = NullBandRenderTarget()
    BandOrchestrator(FakeMusicSource(), FakeAceClient(), target).perform("t1", _band())

    members, audio_len, arrangement = target.opened_with
    assert {m.avatar for m in members} == {"Claire", "Mark", "Beat"}
    assert audio_len == len(b"PCM16K")
    # FakeAceClient yields 2 vocal frames
    assert [f.timestamp_s for f in target.vocal_received] == [0.0, 0.033]
    # 2 instrumentalists each got a cue timeline
    assert {m.avatar for m in arrangement} == {"Mark", "Beat"}
    assert target.closed is True
```

- [ ] **Step 2: Run** `python -m pytest tests/test_band_orchestrator.py -v` → FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# src/ace_reel/band/orchestrator.py
"""Drive a full band performance from one track: music -> beats+A2F -> band render target."""
from __future__ import annotations
import os, tempfile
from ace_reel.contracts.interfaces import MusicSource, AceClient
from ace_reel.orchestrator import to_pcm_16k_mono_bytes
from ace_reel.motion.beat import detect_beats
from ace_reel.band.roster import Band
from ace_reel.band.arranger import BandArranger
from ace_reel.band.performance import BandPerformance
from ace_reel.render.band_base import BandRenderTarget

class BandOrchestrator:
    def __init__(self, music: MusicSource, ace: AceClient, render: BandRenderTarget):
        self._music, self._ace, self._render = music, ace, render

    def perform(self, track_id: str, band: Band,
                emotions: dict[str, float] | None = None) -> None:
        track = self._music.get_track(track_id)
        src = self._music.read_audio(track)
        pcm = to_pcm_16k_mono_bytes(src)
        beats = detect_beats(self._source_to_tempfile(src))
        arrangement = BandArranger().arrange(beats, band)
        vocal_frames = self._ace.stream(pcm, emotions)
        perf = BandPerformance(track=track, audio_pcm=pcm, vocalist=band.vocalist,
                               vocal_frames=vocal_frames, instrument_arrangement=arrangement)
        self._render.run(perf)

    @staticmethod
    def _source_to_tempfile(src: bytes) -> str:
        fd, path = tempfile.mkstemp(suffix=".audio")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(src)
        except Exception:
            os.unlink(path)
            raise
        return path
```

(Note: the temp file is intentionally left for `detect_beats` to read; in the real librosa path it is
read once. A production hardening step — deleting it in a `finally` after `detect_beats` — is listed in
Task 8 follow-ups. The unit test monkeypatches `detect_beats` so the temp file content is irrelevant.)

- [ ] **Step 4: Run** `python -m pytest tests/test_band_orchestrator.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ace_reel/band/orchestrator.py tests/test_band_orchestrator.py
git commit -m "feat(band): BandOrchestrator wiring music+beats+A2F into band render"
```

---

## Task 7: `band-perform` CLI + house.json config

**Files:**
- Create: `bands/house.json`
- Modify: `src/ace_reel/cli.py` (add `band_perform` command + register render builders)
- Test: `tests/test_band_cli.py`

`cli.py` is currently a single `@click.command()` named `main`. To add a second command cleanly,
expose both under a `click.Group` is overkill for two commands; instead add a standalone
`@click.command()` `band_perform` and a `pyproject` script entry. Keep the existing `main`/`perform`
untouched.

- [ ] **Step 1: Write `bands/house.json`**

```json
{
  "name": "House Band",
  "members": [
    {"avatar": "Avatar_Claire", "role": "vocals"},
    {"avatar": "Avatar_Mark",   "role": "guitar", "clips": ["strum_down", "strum_up"]},
    {"avatar": "Avatar_James",  "role": "bass",   "clips": ["bass_pluck"]},
    {"avatar": "Avatar_Beat",   "role": "drums",  "clips": ["kick", "snare", "hihat"]},
    {"avatar": "Avatar_Rhodes", "role": "keys",   "clips": ["keys_comp"]}
  ]
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_band_cli.py
import pytest
from click.testing import CliRunner
from ace_reel.cli import band_perform

def test_band_cli_null_engine_summary(monkeypatch, tmp_path):
    import ace_reel.cli as cli
    from ace_reel.band.roster import Role, Member, Band
    from ace_reel.motion.beat import BeatResult
    from tests.fakes import FakeMusicSource, FakeAceClient
    band = Band("House", [Member("Claire", Role.VOCALS, ()),
                          Member("Mark", Role.GUITAR, ("g1",))])
    monkeypatch.setattr(cli, "load_band", lambda p: band)
    monkeypatch.setattr(cli, "build_music_source", lambda: FakeMusicSource())
    monkeypatch.setattr(cli, "build_ace_client", lambda: FakeAceClient())
    monkeypatch.setattr("ace_reel.band.orchestrator.to_pcm_16k_mono_bytes", lambda s: b"PCM")
    monkeypatch.setattr("ace_reel.band.orchestrator.detect_beats",
                        lambda path: BeatResult(120, [i * 0.5 for i in range(8)]))
    r = CliRunner().invoke(band_perform,
        ["--track", "t1", "--band", "bands/house.json", "--engine", "null"])
    assert r.exit_code == 0
    assert "House" in r.output and "vocalist Claire" in r.output and "2 frames" in r.output

def test_band_cli_unreal_off_windows_clean_error(monkeypatch):
    import sys, ace_reel.cli as cli
    if sys.platform == "win32":
        pytest.skip("preflight only rejects off-Windows")
    from ace_reel.band.roster import Role, Member, Band
    band = Band("House", [Member("Claire", Role.VOCALS, ())])
    monkeypatch.setattr(cli, "load_band", lambda p: band)
    r = CliRunner().invoke(band_perform,
        ["--track", "t1", "--band", "bands/house.json", "--engine", "unreal"])
    assert r.exit_code != 0
    assert "Windows" in r.output and "--engine null" in r.output
```

- [ ] **Step 3: Run** `python -m pytest tests/test_band_cli.py -v` → FAIL (`band_perform` missing).

- [ ] **Step 4: Add the command to `src/ace_reel/cli.py`** (append; reuse existing builders)

```python
# --- append to src/ace_reel/cli.py ---
from ace_reel.band.roster import load_band
from ace_reel.band.orchestrator import BandOrchestrator
from ace_reel.render.band_base import NullBandRenderTarget
from ace_reel.render.unreal_band import UnrealBandRenderTarget

def _band_render(engine: str):
    return NullBandRenderTarget() if engine == "null" else UnrealBandRenderTarget()

@click.command()
@click.option("--track", required=True, help="Suno songs.id")
@click.option("--band", "band_path", required=True, help="path to a band JSON config")
@click.option("--engine", type=click.Choice(["null", "unreal"]), envvar="RENDER_ENGINE",
              default="null", help="render target (or set RENDER_ENGINE)")
def band_perform(track: str, band_path: str, engine: str):
    target = _band_render(engine)
    try:
        target.preflight()  # fail fast (e.g. unreal on a Mac) before building clients
        band = load_band(band_path)
        BandOrchestrator(build_music_source(), build_ace_client(), target).perform(track, band)
    except NotImplementedError as e:
        raise click.ClickException(str(e)) from None
    except (KeyError, ValueError, FileNotFoundError) as e:
        raise click.ClickException(f"missing/invalid configuration: {e}") from None
    if isinstance(target, NullBandRenderTarget):
        members, _, arrangement = target.opened_with
        cues = sum(len(c) for c in arrangement.values())
        click.echo(
            f"{band.name} — {len(members)} members: vocalist {band.vocalist.avatar} "
            f"({len(target.vocal_received)} frames) + {len(arrangement)} instrument timelines, "
            f"{cues} cues total"
        )
```

(Note: `band.vocalist.avatar` prints just the avatar string; the test asserts `vocalist Claire`, so
`bands/house.json`'s `Avatar_Claire` is fine in real use, and the test injects a band whose vocalist
avatar is `Claire`.)

- [ ] **Step 5: Register the script entry in `pyproject.toml`** under `[project.scripts]`:

```toml
[project.scripts]
perform = "ace_reel.cli:main"
band-perform = "ace_reel.cli:band_perform"
```

- [ ] **Step 6: Run** `python -m pytest tests/test_band_cli.py -v` → PASS. Then `pip install -e ".[dev]"` to refresh entry points and confirm `band-perform --help` works.

- [ ] **Step 7: Commit**

```bash
git add bands/house.json src/ace_reel/cli.py pyproject.toml tests/test_band_cli.py
git commit -m "feat(cli): band-perform command + house.json roster"
```

---

## Task 8: Full-suite green + docs touch-up

**Files:**
- Modify: `README.md` (add a one-line note + band-perform example)
- Modify: `docs/01-architecture.md` (add a short "Band layer" subsection cross-referencing the spec)

- [ ] **Step 1: Run the whole non-live suite**

Run: `python -m pytest -m "not live" -q`
Expected: ALL pass (existing 25 + new band tests, ~14 added). If anything fails, fix before docs.

- [ ] **Step 2: Add a `band-perform` quickstart line to `README.md`**

Append under the existing CLI/quickstart section:

```markdown
### Band mode (Avatar House Band)

Play a track through a fixed multi-avatar band (lead sings, instrumentalists move on-beat):

    perform        --track <id> --avatar <name> --engine null     # single avatar
    band-perform   --track <id> --band bands/house.json --engine null   # full band

`null` runs on the Mac (records the performance); `unreal` needs the Windows/RTX box.
Design: `docs/specs/2026-05-30-avatar-house-band-design.md`.
```

- [ ] **Step 3: Add a "Band layer" subsection to `docs/01-architecture.md`**

```markdown
## Band layer (Avatar House Band)

`src/ace_reel/band/` composes the spine into a multi-avatar performance: `roster` (Band/Member),
`arranger` (beats -> per-instrument ClipCue timelines, reusing `plan_dance`), `performance`
(BandPerformance), `orchestrator` (BandOrchestrator). The vocalist streams A2F face frames; each
instrumentalist gets a static beat-synced cue timeline. `render/band_base.py` (NullBandRenderTarget
+ Unreal stub) is the multi-avatar analogue of the single-avatar RenderTarget. Full design:
`docs/specs/2026-05-30-avatar-house-band-design.md`.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/01-architecture.md
git commit -m "docs: document the band layer (Avatar House Band)"
```

- [ ] **Step 5 (follow-up hardening, optional, same commit or separate):** in
`band/orchestrator.py`, delete the temp file after `detect_beats` returns (wrap in try/finally) so
band runs don't leak temp files. Add a test that the temp path no longer exists after `perform`
(monkeypatch `detect_beats` to capture the path, assert `not os.path.exists(path)` post-run).

```python
# in BandOrchestrator.perform, replace the beats line with:
        tmp = self._source_to_tempfile(src)
        try:
            beats = detect_beats(tmp)
        finally:
            os.path.exists(tmp) and os.unlink(tmp)
```

```bash
git add src/ace_reel/band/orchestrator.py tests/test_band_orchestrator.py
git commit -m "harden(band): clean up temp audio file after beat detection"
```

---

## Self-Review

**Spec coverage** (vs `docs/specs/2026-05-30-avatar-house-band-design.md`):
- `roster.py` Role/Member/Band/load_band + validation → Tasks 1–2 ✅ (one-vocalist, unknown-role, empty-clips, tuple-hashable Member).
- `arranger.py` ROLE_BEATS_PER_CUE + pure `arrange` reusing `plan_dance`, vocalist excluded → Task 3 ✅.
- `performance.py` BandPerformance → Task 4 ✅.
- `band_base.py` BandRenderTarget (open/push_vocal_frame/close/preflight/run) + NullBandRenderTarget; `unreal_band.py` stub → Task 5 ✅.
- `orchestrator.py` BandOrchestrator (transcode + source-beats + A2F + arrange + render.run) → Task 6 ✅.
- CLI `band-perform` (+ RENDER_ENGINE, clean ClickExceptions, summary) + `bands/house.json` → Task 7 ✅.
- Testing matrix (roster/arranger/render/orchestrator/CLI) → Tasks 1–7 ✅. Docs → Task 8.
- Out-of-scope items (signal analysis, instrumentalist faces, sections, UE render) are NOT built — correct.

**Placeholder scan:** every code step has runnable code; the only `NotImplementedError`s are the intentional, tested Unreal-band stub. Task 8 Step 5 is labeled a follow-up but includes full code (not a placeholder).

**Type consistency:** `Member(avatar, role, clips: tuple)`, `Band(name, members)` + `.vocalist`/`.instrumentalists`, `BandArranger().arrange(beats, band) -> dict[Member, list[ClipCue]]`, `BandPerformance(track, audio_pcm, vocalist, vocal_frames, instrument_arrangement)`, `BandRenderTarget.open(members, audio_pcm, instrument_arrangement)/push_vocal_frame/close/preflight/run`, `BandOrchestrator(music, ace, render).perform(track_id, band, emotions=None)`, `band_perform` CLI. Names match across all tasks and the existing spine (`plan_dance`, `detect_beats`, `to_pcm_16k_mono_bytes`, `FakeMusicSource`/`FakeAceClient`).
