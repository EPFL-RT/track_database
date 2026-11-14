"""
Track loading. Tracks live in a tracks folder, given
explicitly to every function, laid out as::

    <tracks_dir>/<track_name>/<track_name>_cones.csv
    <tracks_dir>/<track_name>/<track_name>_center_line.csv
"""
import os
from typing import Optional

import numpy as np

try:
    from .utils import load_cones, load_center_line
except ImportError:
    from utils import load_cones, load_center_line

__all__ = ["list_tracks", "find_track_folder", "load_track", "Track"]


def list_tracks(tracks_dir: str) -> list[str]:
    """Returns the sorted names of the track folders found in ``tracks_dir``."""
    folder = os.path.expanduser(tracks_dir)
    if not os.path.isdir(folder):
        return []
    return sorted(
        entry
        for entry in os.listdir(folder)
        if not entry.startswith(".") and os.path.isdir(os.path.join(folder, entry))
    )


def find_track_folder(name: str, tracks_dir: str) -> str:
    """Returns the folder ``<tracks_dir>/<name>`` of a track, or raises a ``ValueError``
    listing the available tracks if it does not exist."""
    folder = os.path.abspath(os.path.expanduser(tracks_dir))
    candidate = os.path.join(folder, name)
    if name and os.path.isdir(candidate):
        return candidate
    raise ValueError(
        f"Track '{name}' not found in {folder}. "
        f"Available tracks: {list_tracks(folder)}"
    )


def _find_file(folder: str, name: str, suffix: str) -> Optional[str]:
    """Looks for <name><suffix> first, then for any file ending with <suffix>."""
    preferred = os.path.join(folder, name + suffix)
    if os.path.isfile(preferred):
        return preferred
    matches = sorted(f for f in os.listdir(folder) if f.endswith(suffix))
    return os.path.join(folder, matches[0]) if matches else None


class Track:
    """
    Plain Old Data Structure (PODS) that represents a track. The track is defined by a
    set of cones and a center line. The cones are stored in the following arrays:
        blue_cones: array of blue cones
        yellow_cones: array of yellow cones
        big_orange_cones: array of big orange cones
        small_orange_cones: array of small orange cones
        right_cones: array of right cones
        left_cones: array of left cones
    The center line is stored in the following array:
        center_line: array of points on the center line
        track_widths: array of track widths at each point on the center line
    """

    name: str
    folder: str
    blue_cones: np.ndarray
    yellow_cones: np.ndarray
    big_orange_cones: np.ndarray
    small_orange_cones: np.ndarray
    right_cones: np.ndarray
    left_cones: np.ndarray
    center_line: np.ndarray
    track_widths: np.ndarray

    def __init__(self, name: str, tracks_dir: str):
        self.name = name
        self.folder = find_track_folder(name, tracks_dir)

        cone_file = _find_file(self.folder, self.name, "_cones.csv") or _find_file(
            self.folder, self.name, "cones.csv"
        )
        if cone_file is None:
            raise ValueError(f"No cones csv file found in track folder {self.folder}")
        (
            self.blue_cones,
            self.yellow_cones,
            self.big_orange_cones,
            self.small_orange_cones,
            self.right_cones,
            self.left_cones,
        ) = load_cones(cone_file)

        center_line_file = _find_file(
            self.folder, self.name, "_center_line.csv"
        ) or _find_file(self.folder, self.name, "center_line.csv")
        if center_line_file is None:
            raise ValueError(
                f"No center line csv file found in track folder {self.folder}"
            )
        self.center_line, self.track_widths = load_center_line(center_line_file)


def load_track(name: str, tracks_dir: str) -> Track:
    """Loads the track stored in the folder ``<tracks_dir>/<name>``."""
    return Track(name, tracks_dir)
