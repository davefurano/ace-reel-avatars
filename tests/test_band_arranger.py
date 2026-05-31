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


def _full_band():
    return Band("House", [
        Member("Claire", Role.VOCALS, ()),
        Member("Mark", Role.GUITAR, ("g1",)),
        Member("Lo", Role.BASS, ("b1",)),
        Member("Beat", Role.DRUMS, ("kick",)),
        Member("Rho", Role.KEYS, ("k1",)),
    ])


def test_bass_every_two_beats_keys_every_four():
    beats = BeatResult(bpm=120, beat_times_s=[i * 0.5 for i in range(8)])  # 8 beats
    arr = BandArranger().arrange(beats, _full_band())
    bass = next(c for m, c in arr.items() if m.role is Role.BASS)
    keys = next(c for m, c in arr.items() if m.role is Role.KEYS)
    assert len(bass) == 4   # BASS = 2 beats/cue -> 8/2
    assert len(keys) == 2   # KEYS = 4 beats/cue -> 8/4


def test_arrange_excludes_vocalist_and_keys_by_member():
    beats = BeatResult(bpm=120, beat_times_s=[i * 0.5 for i in range(8)])
    arr = BandArranger().arrange(beats, _band())
    avatars = {m.avatar for m in arr}
    assert avatars == {"Mark", "Beat"}


def test_drums_get_one_cue_per_beat_guitar_one_per_bar():
    beats = BeatResult(bpm=120, beat_times_s=[i * 0.5 for i in range(8)])
    arr = BandArranger().arrange(beats, _band())
    drums = next(c for m, c in arr.items() if m.role is Role.DRUMS)
    guitar = next(c for m, c in arr.items() if m.role is Role.GUITAR)
    assert len(drums) == 8
    assert len(guitar) == 2


def test_energy_scales_with_tempo():
    fast = BandArranger().arrange(BeatResult(180, [i*0.33 for i in range(8)]), _band())
    slow = BandArranger().arrange(BeatResult(60, [i*1.0 for i in range(8)]), _band())
    fast_drum = next(c for m, c in fast.items() if m.role is Role.DRUMS)[0]
    slow_drum = next(c for m, c in slow.items() if m.role is Role.DRUMS)[0]
    assert fast_drum.energy > slow_drum.energy
