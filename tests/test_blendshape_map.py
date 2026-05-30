from ace_reel.ace.blendshape_map import to_arkit_dict


def test_maps_named_weight_array_to_dict():
    names = ["JawOpen", "EyeBlinkLeft", "TongueRollUp"]  # last is A2F-extra, not ARKit-52
    weights = [0.7, 0.2, 0.9]
    out = to_arkit_dict(names, weights)
    assert out == {"JawOpen": 0.7, "EyeBlinkLeft": 0.2}  # extra shape dropped


def test_clamps_weights_into_unit_range():
    out = to_arkit_dict(["JawOpen"], [1.4])
    assert out["JawOpen"] == 1.0
    out = to_arkit_dict(["JawOpen"], [-0.1])
    assert out["JawOpen"] == 0.0


def test_length_mismatch_raises():
    import pytest
    with pytest.raises(ValueError):
        to_arkit_dict(["JawOpen", "EyeBlinkLeft"], [0.5])
