"""
The track contract: what a track folder must contain to be used by BRAINS. See the README for
the full description; ``check_track`` checks a folder against it.

Errors make the track unusable (a BRAINS reader or hess_sim fails on it). Warnings flag tracks
that load but are probably wrong.
"""

import math
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .tracks import (
    CENTER_LINE_COLUMNS,
    COLORS,
    CONES_COLUMNS,
    center_line_file,
    cones_file,
)

__all__ = ["Issue", "Report", "check_track", "check_path"]

DUPLICATE_DISTANCE = 0.05  # [m] two cones closer than this are duplicates
MIN_TRACK_WIDTH = 3.0  # [m] minimum track width of the Formula Student rules
MERGE_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
# Numbers BRAINS reads: plain decimals with an optional exponent (no nan, inf or spaces).
NUMBER = re.compile(r"[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?")


@dataclass
class Issue:
    level: str  # "error" or "warning"
    file: str
    line: Optional[int]
    message: str

    def __str__(self) -> str:
        where = self.file if self.line is None else f"{self.file}:{self.line}"
        return f"{self.level}: {where}: {self.message}"


@dataclass
class Report:
    folder: str
    issues: list = field(default_factory=list)

    @property
    def errors(self) -> list:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list:
        return [i for i in self.issues if i.level == "warning"]

    def error(self, file: str, line: Optional[int], message: str):
        self.issues.append(Issue("error", file, line, message))

    def warning(self, file: str, line: Optional[int], message: str):
        self.issues.append(Issue("warning", file, line, message))


def _rows(path: str, columns: tuple, suffix: str, report: Report) -> Optional[list]:
    """(line number, fields) of the data rows of a CSV file, or None if it can't be read.
    Checks the header, blank lines and merge-conflict markers."""
    if not os.path.isfile(path):
        others = sorted(
            f for f in os.listdir(os.path.dirname(path)) if f.endswith(suffix)
        )
        hint = f" (found {', '.join(others)}: rename it)" if others else ""
        report.error(path, None, f"missing file{hint}")
        return None
    with open(path, newline="") as f:
        text = f.read()
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # final newline
    lines = [line.rstrip("\r") for line in lines]
    if not lines:
        report.error(path, None, "empty file")
        return None

    header = lines[0].lstrip("# \t").split(",")
    if tuple(header) != columns:
        report.error(
            path, 1, f"header must be {','.join(columns)} (no spaces), got {lines[0]}"
        )
        return None

    rows = []
    for number, line in enumerate(lines[1:], start=2):
        if line.startswith(MERGE_MARKERS):
            report.error(path, number, f"merge conflict marker: {line}")
        elif not line.strip():
            report.error(path, number, "blank line (BRAINS' C++ reader fails on it)")
        else:
            fields = line.split(",")
            if len(fields) != len(columns):
                report.error(
                    path, number, f"{len(fields)} values instead of {len(columns)}"
                )
            elif any(value != value.strip() for value in fields):
                report.error(path, number, "spaces around a value")
            else:
                rows.append((number, fields))
    return rows


def _number(value: str) -> Optional[float]:
    if not NUMBER.fullmatch(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _check_cones(path: str, rows: list, report: Report):
    """Returns the (N, 2) positions and the colors of the valid cones."""
    positions, colors, lines = [], [], []
    for line, fields in rows:
        row = dict(zip(CONES_COLUMNS, fields))
        color = row["cone_type"]
        numbers = [_number(row[k]) for k in ("X", "Y", "Z", "std_X", "std_Y", "std_Z")]
        right, left = row["right"], row["left"]
        if color not in COLORS:
            report.error(path, line, f"unknown cone_type '{color}' (one of {COLORS})")
            continue
        if any(n is None for n in numbers):
            report.error(
                path, line, "X, Y, Z and std_* must be numbers like 1.5 or -2e-3"
            )
            continue
        if right not in ("0", "1") or left not in ("0", "1"):
            report.error(path, line, "right and left must be 0 or 1")
            continue
        if right == "1" and left == "1":
            report.error(path, line, "a cone can't be both right and left")
            continue
        if color == "blue" and left != "1":
            report.warning(path, line, "blue cone not marked as left")
        if color == "yellow" and right != "1":
            report.warning(path, line, "yellow cone not marked as right")
        positions.append(numbers[:2])
        colors.append(color)
        lines.append(line)

    positions = np.array(positions).reshape(-1, 2)
    if len(positions) == 0:
        report.error(path, None, "no cones")
    for i in range(len(positions)):
        distances = np.linalg.norm(positions[i + 1 :] - positions[i], axis=1)
        for j in np.flatnonzero(distances < DUPLICATE_DISTANCE):
            report.warning(
                path,
                lines[i],
                f"duplicate cone (same position as line {lines[i + 1 + j]})",
            )
    return positions, colors


def _check_center_line(path: str, rows: list, report: Report) -> np.ndarray:
    """Returns the (M, 4) values of the valid center line points."""
    values = []
    for line, fields in rows:
        numbers = [_number(value) for value in fields]
        if any(n is None for n in numbers):
            report.error(path, line, "values must be numbers like 1.5 or -2e-3")
        elif numbers[2] <= 0 or numbers[3] <= 0:
            report.error(path, line, "right_width and left_width must be positive")
        else:
            values.append(numbers)
    values = np.array(values).reshape(-1, 4)
    if len(values) < 2:
        report.error(path, None, "the center line needs at least 2 points")
    elif np.min(values[:, 2] + values[:, 3]) < MIN_TRACK_WIDTH - 1e-9:
        report.warning(
            path,
            None,
            f"the track is narrower than {MIN_TRACK_WIDTH} m "
            f"(min {np.min(values[:, 2] + values[:, 3]):.2f} m)",
        )
    return values


def _start_line_crosses(orange: np.ndarray, center_line: np.ndarray) -> bool:
    """Same start line construction as hess_sim (ConeMap::setStartLine)."""

    def cross(u, v):
        return u[0] * v[1] - u[1] * v[0]

    def crosses(a, b):
        for k in range(len(center_line)):
            p, q = center_line[k], center_line[(k + 1) % len(center_line)]
            if (
                cross(b - a, p - a) * cross(b - a, q - a) <= 0
                and cross(q - p, a - p) * cross(q - p, b - p) <= 0
            ):
                return True
        return False

    if len(orange) == 4:
        nearest = np.argmin(np.linalg.norm(center_line - orange.mean(axis=0), axis=1))
        tangent = center_line[(nearest + 1) % len(center_line)] - center_line[nearest]
        normal = np.array([-tangent[1], tangent[0]])
        o = orange[np.argsort(orange @ normal)]
        candidates = [((o[0] + o[1]) / 2, (o[2] + o[3]) / 2)]
    else:
        candidates = [
            (orange[i], orange[j])
            for i in range(len(orange))
            for j in range(i + 1, len(orange))
        ]
    return any(crosses(a, b) for a, b in candidates)


def check_track(folder: str) -> Report:
    """Checks the track folder ``folder`` against the track contract."""
    folder = os.path.normpath(os.path.expanduser(folder))
    report = Report(folder)
    if not os.path.isdir(folder):
        report.error(folder, None, "not a folder")
        return report

    cones_path, center_line_path = cones_file(folder), center_line_file(folder)
    cone_rows = _rows(cones_path, CONES_COLUMNS, "cones.csv", report)
    line_rows = _rows(center_line_path, CENTER_LINE_COLUMNS, "center_line.csv", report)
    if cone_rows is None or line_rows is None:
        return report
    positions, colors = _check_cones(cones_path, cone_rows, report)
    center_line = _check_center_line(center_line_path, line_rows, report)

    orange = positions[[c == "big_orange" for c in colors]].reshape(-1, 2)
    if len(orange) < 2:
        report.warning(
            cones_path,
            None,
            f"{len(orange)} big_orange cones: no start line, hess_sim disables lap timing",
        )
    elif len(center_line) >= 2 and not _start_line_crosses(orange, center_line[:, :2]):
        report.error(
            cones_path,
            None,
            "the start line (big_orange cones) does not cross the center line: "
            "hess_sim fails on this track",
        )
    return report


def _is_track_folder(path: str) -> bool:
    """A track folder contains one of its two files, or has no subfolder."""
    if os.path.isfile(cones_file(path)) or os.path.isfile(center_line_file(path)):
        return True
    return not any(
        os.path.isdir(os.path.join(path, d)) and not d.startswith(".")
        for d in os.listdir(path)
    )


def check_path(path: str) -> list:
    """Reports of the track folder ``path``, or of every track folder in ``path``."""
    path = os.path.expanduser(path)
    if not os.path.isdir(path) or _is_track_folder(path):
        return [check_track(path)]
    return [
        check_track(os.path.join(path, track))
        for track in sorted(os.listdir(path))
        if os.path.isdir(os.path.join(path, track)) and not track.startswith(".")
    ]
