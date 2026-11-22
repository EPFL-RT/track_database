"""Mirror image of a track that keeps its start (position and direction), so that a car
starting on the original track starts the same way on the mirrored one."""

from dataclasses import replace

import numpy as np

from .tracks import Track

__all__ = ["mirror"]

_SWAPPED_COLORS = {"blue": "yellow", "yellow": "blue"}
_SWAPPED_SIDES = {"left": "right", "right": "left"}


def mirror(track: Track) -> Track:
    """
    Mirror image of the track across its start axis. Left and right are exchanged, so the blue
    and yellow cones are swapped (blue cones stay on the left), as well as the sides and the
    right/left widths.
    """
    if len(track.center_line) < 2:
        raise ValueError(
            f"{track.name}: the center line should contain at least 2 points"
        )
    start = track.center_line[0]
    direction = track.center_line[1] - start
    if not np.any(direction):
        raise ValueError(f"{track.name}: the first two center line points are the same")
    direction = direction / np.linalg.norm(direction)

    def reflect(points: np.ndarray) -> np.ndarray:
        offset = points - start
        return start + 2 * np.outer(offset @ direction, direction) - offset

    return replace(
        track,
        cones=reflect(track.cones),
        colors=[_SWAPPED_COLORS.get(c, c) for c in track.colors],
        sides=[_SWAPPED_SIDES.get(s, s) for s in track.sides],
        center_line=reflect(track.center_line),
        widths=track.widths[:, ::-1].copy(),
    )
