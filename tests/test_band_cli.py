import pytest
from click.testing import CliRunner
from ace_reel.cli import band_perform

def test_band_cli_null_engine_summary(monkeypatch, tmp_path):
    import ace_reel.cli as cli
    from ace_reel.band.roster import Role, Member, Band
    from ace_reel.motion.beat import BeatResult
    from tests.fakes import FakeMusicSource, FakeAceClient
    band = Band("House", (Member("Claire", Role.VOCALS, ()),
                          Member("Mark", Role.GUITAR, ("g1",))))
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
    band = Band("House", (Member("Claire", Role.VOCALS, ()),))
    monkeypatch.setattr(cli, "load_band", lambda p: band)
    r = CliRunner().invoke(band_perform,
        ["--track", "t1", "--band", "bands/house.json", "--engine", "unreal"])
    assert r.exit_code != 0
    assert "Windows" in r.output and "--engine null" in r.output
