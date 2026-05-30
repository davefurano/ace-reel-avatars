"""`perform` — one command to play a library track as an avatar performance."""
from __future__ import annotations
import click
from ace_reel.orchestrator import Orchestrator
from ace_reel.render.base import NullRenderTarget
from ace_reel.render.unreal_livelink import UnrealRenderTarget

def build_music_source():
    from ace_reel.music.aimymusic_suno import AImyMusicSunoSource
    return AImyMusicSunoSource.from_env()

def build_ace_client():
    from ace_reel.ace.ace_client import A2FClient, NvcfA2FTransport
    return A2FClient(transport=NvcfA2FTransport())

def _render(engine: str):
    return NullRenderTarget() if engine == "null" else UnrealRenderTarget()

@click.command()
@click.option("--track", required=True, help="Suno songs.id")
@click.option("--avatar", required=True, help="Avatar/MetaHuman asset name")
@click.option("--engine", type=click.Choice(["null", "unreal"]), default="null")
def main(track: str, avatar: str, engine: str):
    target = _render(engine)
    Orchestrator(build_music_source(), build_ace_client(), target).perform(track, avatar)
    n = len(target.received) if isinstance(target, NullRenderTarget) else "?"
    click.echo(f"performed track {track} on {avatar} [{engine}] -> {n} frames")

if __name__ == "__main__":
    main()
