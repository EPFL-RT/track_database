"""Plot of a track: cones, center line and track borders."""

import numpy as np

from .tracks import Track

__all__ = ["plot_track"]

_STYLE = {
    "blue": dict(c="b", s=14),
    "yellow": dict(c="gold", s=14),
    "big_orange": dict(c="orange", s=28),
    "small_orange": dict(c="orange", s=7),
}


def plot_track(track: Track, ax=None):
    """Draws ``track`` on ``ax`` (a new figure by default) and returns the axes."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots()
    for color, style in _STYLE.items():
        cones = track.cones_of(color)
        if len(cones):
            ax.scatter(cones[:, 0], cones[:, 1], marker="^", label=color, **style)

    points = track.center_line
    if len(points) >= 2:
        ax.plot(points[:, 0], points[:, 1], "k--", lw=0.8, label="center line")
        tangents = np.gradient(points, axis=0)
        tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)
        left_normals = tangents @ np.array([[0.0, 1.0], [-1.0, 0.0]])
        for side, widths in ((-1, track.widths[:, 0]), (1, track.widths[:, 1])):
            border = points + side * widths[:, None] * left_normals
            ax.plot(border[:, 0], border[:, 1], color="grey", lw=0.5)
        ax.plot(*points[0], "gx", ms=8, label="start")

    ax.set_title(track.name)
    ax.set_aspect("equal")
    ax.legend(loc="best", fontsize="small")
    return ax
