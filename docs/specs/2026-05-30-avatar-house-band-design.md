# Avatar House Band — Design Spec

> **Status:** approved 2026-05-30. Next step: implementation plan (superpowers:writing-plans).
> **Scope:** a Mac-buildable orchestration layer that drives a fixed multi-avatar "house band"
> performance from a single AImyMusic Suno track, built on the existing `ace-reel-avatars` spine.

## Goal

Turn one song into a coordinated performance by a persistent band of avatars: a lead vocalist
lip-syncs to the track (via Audio2Face-3D) while instrumentalists (guitar, bass, drums, keys) move
and "play" to the beat. The deliverable is the **band layer** — roster, arrangement, orchestration,
and a multi-avatar render contract — all runnable and testable on the Mac. The actual UE5 multi-avatar
render stays a documented stub (Windows/RTX, like the single-avatar `UnrealRenderTarget`).

## Approach (chosen)

**Approach A — Band-as-composition over the existing spine, beat-grid-driven (v1).** Reuse, don't
rewrite. Instrument motion is timed to a beat grid derived from `detect_beats` (believable, not
note-accurate). Per-instrument signal analysis (onset/chroma/RMS) is a future upgrade behind the
same `BandArranger` interface; manual cue sheets were rejected (don't scale to 1,459 songs).

## Architecture

New package `src/ace_reel/band/`, plus a multi-avatar render contract in `src/ace_reel/render/`.
Everything composes existing units — `detect_beats`, `plan_dance`, `A2FClient`,
`to_pcm_16k_mono_bytes`, the `RenderTarget` pattern — with minimal new logic.

```
src/ace_reel/band/
  __init__.py
  roster.py         # Role enum, Member, Band, load_band(path)
  arranger.py       # BandArranger.arrange(beats, band) -> instrument cue timelines (pure)
  performance.py    # BandPerformance dataclass
  orchestrator.py   # BandOrchestrator.perform(track_id, band)
src/ace_reel/render/
  band_base.py      # BandRenderTarget ABC + NullBandRenderTarget
  unreal_band.py    # UnrealBandRenderTarget — documented Win/RTX stub (preflight)
bands/
  house.json        # the default house-band roster
```

### Components

**`roster.py`**
- `Role` enum: `VOCALS, GUITAR, BASS, DRUMS, KEYS`.
- `Member` (frozen dataclass): `avatar: str`, `role: Role`, `clips: tuple[str, ...]` (instrument
  motion clip names; empty for the vocalist). **`clips` is a tuple, not a list, so `Member` stays
  hashable** — it is used as a dict key in the arrangement. `load_band` converts the JSON `clips`
  array to a tuple.
- `Band` (frozen dataclass): `name: str`, `members: list[Member]`. Exposes `vocalist` (the single
  `VOCALS` member) and `instrumentalists` (the rest).
- `load_band(path: str) -> Band`: parse JSON, map `role` strings to `Role`, validate:
  - exactly **one** `VOCALS` member (raise `ValueError` on 0 or >1);
  - every role string is a known `Role` (raise on unknown);
  - each instrumentalist has a non-empty `clips` list (raise on empty).

**`arranger.py`**
- `ROLE_BEATS_PER_CUE: dict[Role, int]` = `{DRUMS: 1, BASS: 2, GUITAR: 4, KEYS: 4}` (vocalist absent).
- `BandArranger.arrange(beats: BeatResult, band: Band) -> dict[Member, list[ClipCue]]`: for each
  **instrumentalist**, return `plan_dance(beats, member.clips, beats_per_bar=ROLE_BEATS_PER_CUE[role])`.
  Pure function, no I/O. The vocalist is excluded (gets a face stream, not cues).

**`performance.py`**
- `BandPerformance` (dataclass): `track: Track`, `audio_pcm: bytes` (16k mono, the shared sync
  reference), `vocalist: Member`, `vocal_frames: Iterable[AnimationFrame]` (streamed A2F output),
  `instrument_arrangement: dict[Member, list[ClipCue]]`.

**`orchestrator.py`**
- `BandOrchestrator(music: MusicSource, ace: AceClient, render: BandRenderTarget)`.
- `perform(track_id: str, band: Band, emotions: dict | None = None) -> None`:
  1. `track = music.get_track(track_id)`; `src = music.read_audio(track)`.
  2. `pcm = to_pcm_16k_mono_bytes(src)`.
  3. `beats = detect_beats(<source audio>)` — beats are derived from the source audio (better
     fidelity than 16k PCM). The orchestrator materializes the source to a temp file for
     `detect_beats` (which takes a path); the temp file is cleaned up after.
  4. `arrangement = BandArranger().arrange(beats, band)`.
  5. `vocal_frames = ace.stream(pcm, emotions)` (the vocalist's lip-sync).
  6. `perf = BandPerformance(track, pcm, band.vocalist, vocal_frames, arrangement)`.
  7. `render.run(perf)`.

**`render/band_base.py`**
- `BandRenderTarget` (ABC):
  - `open(self, members: list[Member], audio_pcm: bytes, instrument_arrangement: dict[Member, list[ClipCue]]) -> None`
    — set up the scene with all avatars; instrument cue timelines are known up front (static).
  - `push_vocal_frame(self, frame: AnimationFrame) -> None` — the only streamed channel.
  - `close(self) -> None`.
  - `preflight(self) -> None` — default no-op (override to fail fast).
  - `run(self, perf: BandPerformance) -> None` — template method: `preflight()`, `open(...)`,
    stream `vocal_frames` via `push_vocal_frame`, `finally: close()`.
- `NullBandRenderTarget`: records `opened_with` (members, audio length, arrangement),
  `vocal_received: list[AnimationFrame]`, `closed: bool` — the Mac sink + test double.

**`render/unreal_band.py`**
- `UnrealBandRenderTarget(BandRenderTarget)`: `preflight()` raises `NotImplementedError` off-Windows
  with the "use --engine null" guidance; `open`/`push_vocal_frame` raise pending the in-engine
  bridge. Docstring captures the multi-avatar UE wiring: N MetaHumans in one Sequencer/scene, the
  vocalist driven by `Apply ACE Face Animations`, instrumentalists driven by IK-retargeted instrument
  clips on `metahuman_base_skel` scheduled from the `ClipCue` timelines, one shared audio track.

### Data flow

```
track → read_audio → transcode → pcm(16k)            ┐
            └→ (temp file) → detect_beats → BeatResult ──→ BandArranger.arrange(beats, band)
pcm → A2FClient.stream (vocalist face)                ┘        │  {instrumentalist: [ClipCue]}
                                                                ▼
                          BandPerformance → BandRenderTarget.run()
   vocalist: streamed AnimationFrames   ·   instrumentalists: static beat-synced ClipCue timelines
```

### CLI

New command `band-perform --track <songs.id> --band <path> --engine null|unreal` (`--engine` also
honors `RENDER_ENGINE`). `null` runs on the Mac and prints a summary, e.g.
`"House Band — 5 members: vocalist Avatar_Claire (N frames) + 4 instrument timelines, X cues total"`.
`unreal` fails fast via `preflight()` off-Windows. Config/transcode/`NotImplementedError` errors
surface as clean `click.ClickException`s (no tracebacks), matching the existing `perform` command.

### Error handling

- `load_band`: 0 or >1 vocalists, unknown role, or empty instrument `clips` → `ValueError`.
- `arrange`: empty `clips` reaches `plan_dance` → its existing `ValueError` (belt-and-suspenders).
- `UnrealBandRenderTarget.preflight` off-Windows → `NotImplementedError` → `ClickException`.
- Missing/invalid config or env → `ClickException` ("missing/invalid configuration: …").

### Testing (TDD, all Mac-runnable, `pytest -m "not live"`)

- **roster:** loads a valid band; rejects 0 vocalists, 2 vocalists, unknown role, empty instrument
  clips; `vocalist`/`instrumentalists` partition correctly.
- **arranger:** drums get one cue per beat, bass every 2, guitar/keys every 4; energy scales with
  bpm; the vocalist is absent from the result; clip names rotate within each role.
- **orchestrator:** with `FakeMusicSource` + `FakeAceClient` + monkeypatched `detect_beats`,
  `NullBandRenderTarget` receives all members, the same audio length, one vocal stream of the
  expected frame count, and one cue timeline per instrumentalist.
- **band render:** `NullBandRenderTarget` records open args, vocal frames in order, and `closed`;
  `UnrealBandRenderTarget.preflight` raises off-Windows.
- **CLI:** `band-perform … --engine null` smoke test prints the member summary; `--engine unreal`
  off-Windows exits non-zero with the friendly platform message (no traceback).

## Out of scope (v1)

Named explicitly so they don't creep in:
- Per-instrument signal analysis (onset/chroma/RMS) — Approach B, future, same interface.
- Instrumentalist facial/emotion animation — v1 instrumentalists are body/instrument cues only.
- Song-section dynamics (verse/chorus energy curves).
- Note-accurate instrument timing.
- The actual UE5 multi-avatar render / reel export — Windows/RTX, documented stub only.
- Vocal-stem separation for backing/harmony vocals (single lead lip-syncs the full mix).

## Reuse map (what this builds on)

`detect_beats` / `BeatResult`, `plan_dance` / `ClipCue` (motion); `A2FClient.stream` (ace);
`to_pcm_16k_mono_bytes` (orchestrator); `Track` / `MusicSource` / `AceClient` / `AnimationFrame`
(contracts); the `RenderTarget` template-method + `preflight` + `NullRenderTarget`/stub pattern
(render). See `docs/01-architecture.md` and `docs/00-discovery.md`.
