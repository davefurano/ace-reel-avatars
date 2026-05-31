import pytest
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


def test_cli_unreal_engine_reports_clean_error(monkeypatch):
    import ace_reel.cli as cli
    from tests.fakes import FakeMusicSource, FakeAceClient
    monkeypatch.setattr(cli, "build_music_source", lambda: FakeMusicSource())
    monkeypatch.setattr(cli, "build_ace_client", lambda: FakeAceClient())
    monkeypatch.setattr("ace_reel.orchestrator.to_pcm_16k_mono_bytes", lambda b: b"PCM")
    r = CliRunner().invoke(main, ["--track", "t1", "--avatar", "A", "--engine", "unreal"])
    assert r.exit_code != 0
    assert "Error:" in r.output and "Windows" in r.output


def test_cli_unreal_on_mac_fails_clean_without_credentials(monkeypatch):
    # No builder patching, no Supabase/NVIDIA env: preflight must reject BEFORE building
    # clients, so the user sees the friendly platform error, not a KeyError traceback.
    import sys
    if sys.platform == "win32":
        pytest.skip("preflight only rejects off-Windows")
    for var in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "NVIDIA_API_KEY", "RENDER_ENGINE"):
        monkeypatch.delenv(var, raising=False)
    r = CliRunner().invoke(main, ["--track", "t1", "--avatar", "A", "--engine", "unreal"])
    assert r.exit_code != 0
    assert "Windows" in r.output and "--engine null" in r.output
    assert r.exc_info is None or r.exc_info[0] is SystemExit  # no leaked NotImplementedError/KeyError
