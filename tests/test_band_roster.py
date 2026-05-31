import json
import pytest
from ace_reel.band.roster import Role, Member, Band, load_band


def test_member_is_hashable_with_tuple_clips():
    m = Member(avatar="Avatar_Mark", role=Role.GUITAR, clips=("strum_down", "strum_up"))
    assert {m: 1}[m] == 1
    assert m.role is Role.GUITAR


def test_band_partitions_vocalist_and_instrumentalists():
    v = Member("Claire", Role.VOCALS, ())
    g = Member("Mark", Role.GUITAR, ("strum",))
    d = Member("Beat", Role.DRUMS, ("kick",))
    band = Band(name="House", members=[v, g, d])
    assert band.vocalist is v
    assert band.instrumentalists == [g, d]


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
    assert band.instrumentalists[0].clips == ("strum_down", "strum_up")


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
