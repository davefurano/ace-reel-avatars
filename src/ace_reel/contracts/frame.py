"""Engine-agnostic animation frame — the one type every adapter speaks."""
from __future__ import annotations
from pydantic import BaseModel, field_validator, ConfigDict

ARKIT_52: tuple[str, ...] = (
    "EyeBlinkLeft","EyeLookDownLeft","EyeLookInLeft","EyeLookOutLeft","EyeLookUpLeft",
    "EyeSquintLeft","EyeWideLeft","EyeBlinkRight","EyeLookDownRight","EyeLookInRight",
    "EyeLookOutRight","EyeLookUpRight","EyeSquintRight","EyeWideRight","JawForward",
    "JawLeft","JawRight","JawOpen","MouthClose","MouthFunnel","MouthPucker","MouthLeft",
    "MouthRight","MouthSmileLeft","MouthSmileRight","MouthFrownLeft","MouthFrownRight",
    "MouthDimpleLeft","MouthDimpleRight","MouthStretchLeft","MouthStretchRight",
    "MouthRollLower","MouthRollUpper","MouthShrugLower","MouthShrugUpper","MouthPressLeft",
    "MouthPressRight","MouthLowerDownLeft","MouthLowerDownRight","MouthUpperUpLeft",
    "MouthUpperUpRight","BrowDownLeft","BrowDownRight","BrowInnerUp","BrowOuterUpLeft",
    "BrowOuterUpRight","CheekPuff","CheekSquintLeft","CheekSquintRight","NoseSneerLeft",
    "NoseSneerRight","TongueOut",
)
_ARKIT_SET = frozenset(ARKIT_52)

EMOTIONS: tuple[str, ...] = (
    "amazement","anger","cheekiness","disgust","fear","grief","joy","outofbreath","pain","sadness",
)
_EMOTION_SET = frozenset(EMOTIONS)


class JointRotation(BaseModel):
    """One skeletal joint as a quaternion (body pose; None until the dance module fills it)."""
    name: str
    x: float; y: float; z: float; w: float


class BodyPose(BaseModel):
    joints: list[JointRotation]


class AnimationFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timestamp_s: float
    blendshapes: dict[str, float]
    emotions: dict[str, float]
    body_pose: BodyPose | None = None

    @field_validator("blendshapes")
    @classmethod
    def _check_blendshapes(cls, v: dict[str, float]) -> dict[str, float]:
        bad = set(v) - _ARKIT_SET
        if bad:
            raise ValueError(f"unknown ARKit blendshapes: {sorted(bad)}")
        for name, w in v.items():
            if not (0.0 <= w <= 1.0):
                raise ValueError(f"blendshape {name}={w} out of range [0,1]")
        return v

    @field_validator("emotions")
    @classmethod
    def _check_emotions(cls, v: dict[str, float]) -> dict[str, float]:
        bad = set(v) - _EMOTION_SET
        if bad:
            raise ValueError(f"unknown emotions: {sorted(bad)}")
        for name, w in v.items():
            if not (0.0 <= w <= 1.0):
                raise ValueError(f"emotion {name}={w} out of range [0,1]")
        return v
