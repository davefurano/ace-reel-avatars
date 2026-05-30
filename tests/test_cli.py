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
