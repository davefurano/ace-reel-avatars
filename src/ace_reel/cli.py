"""`perform` — one command to play a library track as an avatar performance."""
from __future__ import annotations
import click
from ace_reel.orchestrator import Orchestrator
from ace_reel.render.base import NullRenderTarget
from ace_reel.render.unreal_livelink import UnrealRenderTarget
from ace_reel.band.roster import load_band
from ace_reel.band.orchestrator import BandOrchestrator
from ace_reel.render.band_base import NullBandRenderTarget
from ace_reel.render.unreal_band import UnrealBandRenderTarget

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
@click.option("--engine", type=click.Choice(["null", "unreal"]), envvar="RENDER_ENGINE",
              default="null", help="render target (or set RENDER_ENGINE)")
def main(track: str, avatar: str, engine: str):
    target = _render(engine)
    try:
        target.preflight()  # fail fast (e.g. unreal on a Mac) before building clients
        Orchestrator(build_music_source(), build_ace_client(), target).perform(track, avatar)
    except NotImplementedError as e:
        raise click.ClickException(str(e)) from None
    except (KeyError, ValueError) as e:
        raise click.ClickException(f"missing/invalid configuration: {e}") from None
    n = len(target.received) if isinstance(target, NullRenderTarget) else "?"
    click.echo(f"performed track {track} on {avatar} [{engine}] -> {n} frames")

def _band_render(engine: str):
    return NullBandRenderTarget() if engine == "null" else UnrealBandRenderTarget()

@click.command()
@click.option("--track", required=True, help="Suno songs.id")
@click.option("--band", "band_path", required=True, help="path to a band JSON config")
@click.option("--engine", type=click.Choice(["null", "unreal"]), envvar="RENDER_ENGINE",
              default="null", help="render target (or set RENDER_ENGINE)")
def band_perform(track: str, band_path: str, engine: str):
    target = _band_render(engine)
    try:
        target.preflight()  # fail fast (e.g. unreal on a Mac) before building clients
        band = load_band(band_path)
        BandOrchestrator(build_music_source(), build_ace_client(), target).perform(track, band)
    except NotImplementedError as e:
        raise click.ClickException(str(e)) from None
    except (KeyError, ValueError, FileNotFoundError) as e:
        raise click.ClickException(f"missing/invalid configuration: {e}") from None
    if isinstance(target, NullBandRenderTarget):
        members, _, arrangement = target.opened_with
        cues = sum(len(c) for c in arrangement.values())
        click.echo(
            f"{band.name} — {len(members)} members: vocalist {band.vocalist.avatar} "
            f"({len(target.vocal_received)} frames) + {len(arrangement)} instrument timelines, "
            f"{cues} cues total"
        )


if __name__ == "__main__":
    main()
