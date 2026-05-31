"""Guard the shipped band configs in bands/ against drift — they must all pass load_band."""
import glob
import os
import pytest
from ace_reel.band.roster import load_band

_BANDS = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "bands", "*.json")))


@pytest.mark.parametrize("path", _BANDS, ids=[os.path.basename(p) for p in _BANDS])
def test_shipped_band_config_loads(path):
    band = load_band(path)
    assert band.name
    assert band.vocalist.avatar            # exactly one vocalist (load_band enforces)
    assert band.instrumentalists           # at least one player
    assert all(m.clips for m in band.instrumentalists)


def test_at_least_house_and_demo_ship():
    names = {os.path.basename(p) for p in _BANDS}
    assert {"house.json", "demo_trio.json"} <= names
