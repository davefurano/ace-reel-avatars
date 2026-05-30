import numpy as np, soundfile as sf, pytest
from ace_reel.motion.beat import detect_beats


def _make_click_track(path, bpm=120, sr=22050, seconds=8):
    n = sr * seconds
    audio = np.zeros(n, dtype=np.float32)
    step = int(sr * 60 / bpm)
    for i in range(0, n, step):
        audio[i:i+200] = 0.9
    sf.write(path, audio, sr)


def test_detects_tempo_and_beats(tmp_path):
    wav = tmp_path / "click.wav"
    _make_click_track(wav, bpm=120)
    result = detect_beats(str(wav))
    assert result.bpm == pytest.approx(120, abs=3)
    assert len(result.beat_times_s) >= 12
    assert all(b2 > b1 for b1, b2 in zip(result.beat_times_s, result.beat_times_s[1:]))
