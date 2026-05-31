"""House-band roster: roles, members, and the band that performs a track."""
from __future__ import annotations
import json
from dataclasses import dataclass
from enum import Enum


class Role(Enum):
    VOCALS = "vocals"
    GUITAR = "guitar"
    BASS = "bass"
    DRUMS = "drums"
    KEYS = "keys"


@dataclass(frozen=True)
class Member:
    avatar: str
    role: Role
    clips: tuple[str, ...] = ()      # tuple (not list) so Member stays hashable / dict-key-able


@dataclass(frozen=True)
class Band:
    name: str
    members: tuple[Member, ...] = ()      # tuple matches frozen intent and keeps Band hashable

    @property
    def vocalist(self) -> Member:
        v = next((m for m in self.members if m.role is Role.VOCALS), None)
        if v is None:
            raise ValueError("band has no vocalist")
        return v

    @property
    def instrumentalists(self) -> list[Member]:
        return [m for m in self.members if m.role is not Role.VOCALS]


def load_band(path: str) -> Band:
    """Parse + validate a band JSON config into a Band."""
    with open(path) as f:
        data = json.load(f)
    members: list[Member] = []
    for raw in data.get("members", []):
        role_str = raw["role"]
        try:
            role = Role(role_str)
        except ValueError:
            raise ValueError(f"unknown role: {role_str!r}") from None
        clips = tuple(raw.get("clips", ()))
        if role is not Role.VOCALS and not clips:
            raise ValueError(f"instrumentalist {raw['avatar']!r} ({role_str}) needs at least one clip")
        members.append(Member(avatar=raw["avatar"], role=role, clips=clips))
    vocalists = [m for m in members if m.role is Role.VOCALS]
    if len(vocalists) != 1:
        raise ValueError(f"band must have exactly one vocalist, found {len(vocalists)}")
    return Band(name=data.get("name", "Band"), members=tuple(members))
