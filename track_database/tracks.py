"""
Reading and writing track folders.

A track named ``<name>`` is a folder ``<name>/`` containing ``<name>_cones.csv`` and
``<name>_center_line.csv``. See the README (track contract) for the exact format, and
``contract.check_track`` to check a folder against it.
"""

import csv
import math
import os
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

__all__ = [
    "COLORS",
    "CONES_COLUMNS",
    "CENTER_LINE_COLUMNS",
    "Track",
    "load_track",
    "save_track",
    "cones_file",
    "center_line_file",
]

COLORS = ("blue", "yellow", "big_orange", "small_orange")
CONES_COLUMNS = ("cone_type", "X", "Y", "Z", "std_X", "std_Y", "std_Z", "right", "left")
CENTER_LINE_COLUMNS = ("x", "y", "right_width", "left_width")


def cones_file(folder: str) -> str:
    """Path of the cones file of the track folder ``folder``."""
    name = os.path.basename(os.path.normpath(folder))
    return os.path.join(folder, f"{name}_cones.csv")


def center_line_file(folder: str) -> str:
    """Path of the center line file of the track folder ``folder``."""
    name = os.path.basename(os.path.normpath(folder))
    return os.path.join(folder, f"{name}_center_line.csv")


@dataclass
class Track:
    """
    A track, one entry per cone (in file order) and per center line point:
        cones: (N, 2) cone positions
        colors: color of each cone, one of COLORS
        sides: side of each cone, "right", "left" or "unknown" (the right/left columns)
        center_line: (M, 2) center line points
        widths: (M, 2) right and left track widths at each center line point
    """

    name: str
    cones: np.ndarray = field(default_factory=lambda: np.zeros((0, 2)))
    colors: list = field(default_factory=list)
    sides: list = field(default_factory=list)
    center_line: np.ndarray = field(default_factory=lambda: np.zeros((0, 2)))
    widths: np.ndarray = field(default_factory=lambda: np.zeros((0, 2)))

    def cones_of(self, color: str) -> np.ndarray:
        """(K, 2) positions of the cones of one color."""
        mask = np.array([c == color for c in self.colors], dtype=bool)
        return self.cones[mask].reshape(-1, 2)


def _read_rows(path: str) -> list:
    """Rows of a CSV file as dicts. A leading "#" in the header (numpy.savetxt) is ignored."""
    with open(path, newline="") as f:
        header = f.readline().lstrip("# \t").rstrip("\r\n")
        return list(csv.DictReader(f, fieldnames=header.split(",")))


def load_track(folder: str) -> Track:
    """Loads the track stored in ``folder`` (its name is the folder name)."""
    folder = os.path.expanduser(folder)
    name = os.path.basename(os.path.normpath(folder))
    if not os.path.isdir(folder):
        raise ValueError(f"Track folder {folder} does not exist")
    try:
        cone_rows = _read_rows(cones_file(folder))
        cones = np.array([[float(r["X"]), float(r["Y"])] for r in cone_rows])
        colors = [r["cone_type"] for r in cone_rows]
        sides = [
            "right" if r["right"] == "1" else "left" if r["left"] == "1" else "unknown"
            for r in cone_rows
        ]
        line_rows = _read_rows(center_line_file(folder))
        values = np.array(
            [[float(r[k]) for k in CENTER_LINE_COLUMNS] for r in line_rows]
        ).reshape(-1, 4)
    except (OSError, KeyError, TypeError, ValueError) as e:
        raise ValueError(
            f"Invalid track {folder} ({e!r}): run `track-db check {folder}` for details"
        ) from e
    return Track(
        name, cones.reshape(-1, 2), colors, sides, values[:, :2], values[:, 2:]
    )


def _number(value: float, decimals: Optional[int]) -> str:
    if not math.isfinite(value):
        raise ValueError(f"cannot save the non-finite value {value}")
    return repr(float(value)) if decimals is None else f"{value:.{decimals}f}"


def save_track(track: Track, folder: str, decimals: Optional[int] = None) -> str:
    """
    Writes ``track`` to ``folder/<name>/`` (``<name>_cones.csv`` and
    ``<name>_center_line.csv``) and returns the track folder. Values are written with full
    precision, or with ``decimals`` decimals.
    """
    if not len(track.cones) == len(track.colors) == len(track.sides):
        raise ValueError(
            f"{track.name}: cones, colors and sides must have the same length"
        )
    if len(track.center_line) != len(track.widths):
        raise ValueError(
            f"{track.name}: center_line and widths must have the same length"
        )
    track_folder = os.path.join(os.path.expanduser(folder), track.name)
    os.makedirs(track_folder, exist_ok=True)
    with open(cones_file(track_folder), "w") as f:
        f.write(",".join(CONES_COLUMNS) + "\n")
        for (x, y), color, side in zip(track.cones, track.colors, track.sides):
            right, left = int(side == "right"), int(side == "left")
            f.write(
                f"{color},{_number(x, decimals)},{_number(y, decimals)},"
                f"0.0,0.0,0.0,0.0,{right},{left}\n"
            )
    with open(center_line_file(track_folder), "w") as f:
        f.write(",".join(CENTER_LINE_COLUMNS) + "\n")
        for (x, y), (right, left) in zip(track.center_line, track.widths):
            f.write(",".join(_number(v, decimals) for v in (x, y, right, left)) + "\n")
    return track_folder
