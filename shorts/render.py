"""Render a verified spec to a vertical MP4."""
import shutil
from pathlib import Path

from manim import tempconfig

from .scene import ShortScene
from .style import BG

QUALITY = {
    "preview": dict(pixel_width=540, pixel_height=960, frame_rate=15),
    "final": dict(pixel_width=1080, pixel_height=1920, frame_rate=30),
}


def render(spec, traces, quality="final", out_dir="out") -> Path:
    cfg = {**QUALITY[quality], "frame_width": 9, "frame_height": 16, "background_color": BG,
           "media_dir": f"media/{spec.slug}",  # per-video, so parallel renders never collide
           "output_file": f"{spec.slug}_{quality}", "disable_caching": True,
           "progress_bar": "none", "verbosity": "WARNING"}
    with tempconfig(cfg):
        scene = ShortScene()
        scene.spec, scene.traces = spec, traces
        scene.render()
        movie = Path(scene.renderer.file_writer.movie_file_path)
    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    dest = out / f"{spec.slug}.mp4" if quality == "final" else out / f"{spec.slug}_{quality}.mp4"
    shutil.copy(movie, dest)
    return dest
