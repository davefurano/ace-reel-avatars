# Session Recap — ace-reel-avatars (Avatar House Band)

_For the next session. Repo: github.com/davefurano/ace-reel-avatars (public, MIT, `main`)._

## What exists now (all pushed, 46 tests green on `pytest -m "not live"`)
- **Template spine** (Mac-runnable): `contracts/` (`AnimationFrame`, `AceClient`/`RenderTarget`/`MusicSource`, `Track`),
  `ace/` (`A2FClient` + `blendshape_map` + ffmpeg `to_pcm_16k_mono`; `NvcfA2FTransport` is a documented stub),
  `motion/` (`detect_beats`→`BeatResult`, `plan_dance`→`ClipCue`), `render/` (`NullRenderTarget` + `UnrealRenderTarget` stub),
  `music/` (`AImyMusicSunoSource`), `orchestrator.py` + `perform` CLI.
- **Avatar House Band layer** `band/`: `roster.py` (`Role`/`Member`/`Band`/`load_band`), `arranger.py`
  (`BandArranger` — reuses `plan_dance` at role beat-resolutions: drums 1, bass 2, guitar/keys 4),
  `performance.py` (`BandPerformance`), `orchestrator.py` (`BandOrchestrator`). Render: `render/band_base.py`
  (`BandRenderTarget` + `NullBandRenderTarget`), `render/unreal_band.py` (Win/RTX stub). CLI `band-perform`.
  Rosters: `bands/house.json` (5-piece), `bands/demo_trio.json`.
- **Examples**: `examples/demo_band.py` (no-creds synthetic demo), `examples/suno_band.py`
  (real track via `--track <songs.id>` or `--url`; `--grid` prints a beat grid).
- **Infra**: CI + Demo GitHub Actions workflows (Node 24 actions), badges, MIT LICENSE, CONTRIBUTING.md.

## Proven end-to-end (real song)
`examples/suno_band.py --grid` ran the House Band against a real Suno track ("The Heart of Gold",
136 BPM): drums on every beat, bass every 2, guitar/keys per bar → 413 instrument cues. Real audio →
real librosa tempo → real arrangement. Vocals were a stand-in (no NVIDIA key); render is Win/RTX-only.

## Key verified facts (don't re-research these)
- **NVIDIA ACE is face-only.** Audio2Face-3D v2.0 (`nvcr.io/nim/nvidia/audio2face-3d:2.0`): PCM mono 16k in,
  ARKit-52 blendshapes + 10 emotions out over gRPC bidi. Hosted free at `grpc.nvcf.nvidia.com:443`. **No
  audio→dance service exists** — dancing = beat-synced clips (the `motion/` fallback).
- **Render needs Windows + NVIDIA RTX.** ACE Unreal plugin 2.5, UE 5.6, MetaHuman. macOS unsupported. The
  Mac is an orchestration terminal only. NVIDIA hosts inference, never the rendered video.
- **Suno data:** Supabase project `xltunldffphrlqstujyg`, table `public.songs` (~1,459 rows). `audio_path`
  is often a **full `https://cdn1.suno.ai/<id>.mp3` URL** (publicly downloadable, no key) — NOT always a
  bucket path. `AImyMusicSunoSource.get_track` now passes URLs through and only signs bucket paths.

## Gotchas already solved (keep them)
- `Member` uses `clips: tuple` (hashable — it's a dict key in the arrangement); `Band.members` is a tuple.
- `Band.vocalist` raises `ValueError` (not `StopIteration`) if no vocalist.
- `preflight()` is the **CLI's** job (fail fast for unreal-on-Mac); `run()` does not call it; `open()` re-guards.
- CLI maps `NotImplementedError`/config errors to `click.ClickException` (no tracebacks). `--engine` honors `RENDER_ENGINE`.
- librosa needs a decodable file → `suno_band.py` ffmpeg-decodes to WAV before `detect_beats`.

## Still pending (next session)
1. **CODE_OF_CONDUCT.md** — Contributor Covenant 2.1, contact davefurano@gmail.com (kept getting cut off).
2. **`docs/runbook-cloud-rtx.md`** — rent a Windows+RTX VM (AWS g5 / Azure NV / GCP G2+L4 / Paperspace),
   Parsec/DCV, install UE 5.6 + ACE plugin 2.5, free NVIDIA key, render or Movie Render Queue → MP4.
3. **`UnrealBandRenderTarget` bridge code** — implement `open`/`push_vocal_frame` (currently raise). Define a
   small in-engine transport (gRPC/socket) so the Mac orchestrator can stream frames + the instrument
   `ClipCue` timelines into UE. This is the gating work before anything renders.

## To regenerate/extend fast
Use `prompts/avatar-house-band.prompt.md` — it encodes the architecture, verified facts, type names,
and gotchas so a rebuild skips rediscovery.
