"""Turn a track's beats into per-instrumentalist beat-synced cue timelines (pure, no I/O)."""
from __future__ import annotations
from ace_reel.motion.beat import BeatResult
from ace_reel.motion.planner import plan_dance, ClipCue
from ace_reel.band.roster import Role, Member, Band

ROLE_BEATS_PER_CUE: dict[Role, int] = {
    Role.DRUMS: 1,
    Role.BASS: 2,
    Role.GUITAR: 4,
    Role.KEYS: 4,
}


class BandArranger:
    def arrange(self, beats: BeatResult, band: Band) -> dict[Member, list[ClipCue]]:
        out: dict[Member, list[ClipCue]] = {}
        for member in band.instrumentalists:
            per_cue = ROLE_BEATS_PER_CUE[member.role]
            out[member] = plan_dance(beats, list(member.clips), beats_per_bar=per_cue)
        return out
