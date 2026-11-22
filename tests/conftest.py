import numpy as np
import pytest

from track_database import Track, save_track


def straight_track(name="straight", length=30.0, spacing=5.0, width=3.0):
    """A straight track along +y with 2 big orange cones at the start line y = 0."""
    ys = np.arange(spacing, length + spacing / 2, spacing)
    blue = np.column_stack((np.full(len(ys), -width / 2), ys))
    yellow = np.column_stack((np.full(len(ys), width / 2), ys))
    orange = np.array([[-width / 2 - 0.1, 0.0], [width / 2 + 0.1, 0.0]])
    center = np.column_stack((np.zeros(7), np.linspace(-5.0, length, 7)))
    return Track(
        name=name,
        cones=np.vstack((blue, yellow, orange)),
        colors=["blue"] * len(ys) + ["yellow"] * len(ys) + ["big_orange"] * 2,
        sides=["left"] * len(ys) + ["right"] * len(ys) + ["left", "right"],
        center_line=center,
        widths=np.full((len(center), 2), width / 2),
    )


@pytest.fixture
def track():
    return straight_track()


@pytest.fixture
def track_folder(tmp_path, track):
    return save_track(track, str(tmp_path))
