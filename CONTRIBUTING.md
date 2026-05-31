# Contributing to ace-reel-avatars

Thanks for your interest. This repo is an engine-agnostic **template spine** for an NVIDIA ACE ×
Unreal Engine avatar pipeline. Most of it runs and is tested on a laptop; the actual UE5 render is a
documented Windows/RTX stub. Contributions that keep that split clean — and the boundaries honest —
are very welcome.

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -m "not live" -q      # expect: 45 passed
python examples/demo_band.py           # the no-credentials demo
```

Python **3.11+**. No GPU, no Unreal, no API keys are needed for the non-live suite or the demo.

## Ground rules

1. **Adapter boundaries are sacred.** ACE, the render engine, and the music library each sit behind a
   typed interface in `src/ace_reel/contracts/interfaces.py`. No vendor type (`grpc`, `nvidia-ace`,
   `supabase`, `librosa`, UE types) may cross those interfaces. The only types that travel between
   layers are `AnimationFrame`, `Track`, `ClipCue`, and band `Member`/`BandPerformance`. If you find
   yourself importing a vendor SDK into `contracts/`, `band/`, or another adapter's module, stop.
2. **TDD.** Write the failing test first, watch it fail, then make it pass. Tests assert real behavior,
   not mock internals. See any existing `tests/test_*.py` for the style.
3. **No secrets in code.** Keys come from the environment and `.env.example`; never hardcode. `.env`
   is gitignored — keep it that way.
4. **Stubs fail loud.** Anything not implemented yet (the live A2F transport, the Unreal targets)
   raises `NotImplementedError` with a doc-pointing message. Never silently no-op.
5. **Keep files focused.** One clear responsibility per module. If a file is growing past its job,
   split it.

## Tests

```bash
python -m pytest -m "not live" -q                       # everything that runs offline (CI gate)
python -m pytest tests/test_ace_client.py -m live -v     # needs NVIDIA_API_KEY + tests/data/sample_vocal.wav
python -m pytest tests/test_music_source.py -m live -v   # needs SUPABASE_SERVICE_KEY + SUNO_TEST_TRACK_ID
```

Live tests are gated behind the `@pytest.mark.live` marker and **skip cleanly** without credentials —
they must never fail for lack of keys. Add new external-service tests the same way.

## CI

Two GitHub Actions workflows run on every push and PR and **must stay green**:

- **CI** (`.github/workflows/ci.yml`) — installs the package and runs `pytest -m "not live"`.
- **Demo** (`.github/workflows/demo.yml`) — runs `examples/demo_band.py` end to end.

Run both locally before opening a PR (`pytest -m "not live" -q` and `python examples/demo_band.py`).

## Extending the template

The whole point is swapping a layer without touching the others. Common contributions:

- **A new render engine** — implement `RenderTarget` (`open`/`push`/`close`; `run()` is inherited) and
  register it in `cli._render`. Walkthrough: `docs/add-a-render-target.md`. For a band engine,
  implement `BandRenderTarget` and register it in `cli._band_render`. Use `NullRenderTarget` /
  `NullBandRenderTarget` as the reference impls.
- **A new music source** — implement `MusicSource` (`get_track` + `read_audio`). Keep any client
  behind a small gateway seam so it's testable with a fake (see `AImyMusicSunoSource`).
- **A new band roster** — drop a JSON file in `bands/` (one `vocals` member + instrumentalists with
  motion `clips`). `tests/test_shipped_bands.py` validates every `bands/*.json` automatically.
- **A new ACE model** — set `A2F_FUNCTION_ID` in `.env`; no code change needed.

If your change touches design intent, skim the relevant doc in `docs/` (`00-discovery.md`,
`01-architecture.md`, the specs in `docs/specs/`) and update it in the same PR.

## Commits & PRs

- **Conventional, scoped commit messages**: `feat(band): …`, `fix(cli): …`, `docs: …`, `ci: …`,
  `chore: …`. Match the existing `git log` style.
- Keep each PR focused on one change. Update docs and tests alongside the code.
- A PR should leave the non-live suite and the demo green.

## License

By contributing, you agree your contributions are licensed under the project's
[MIT License](LICENSE).
