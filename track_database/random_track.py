# SPDX-License-Identifier: Apache-2.0
#
# Derived from the EUFS track generator (eufs_sim, eufs_tracks/eufs_tracks/track_generator/
# track_generator.py, https://gitlab.com/eufs/public/eufs_sim), which is licensed under the
# Apache License 2.0: see LICENSE.eufs_sim next to this file. Modified in 2026 for the EPFL
# Racing Team, the changes are listed in the docstring below. The rest of the repository is
# MIT licensed, this file stays under the Apache License 2.0.
"""Random closed race tracks, to test planners on.

The path generation, self-intersection check, start-line selection and cone placement are
adapted from the EUFS track generator. Changes made: np.complex (removed in NumPy 1.24) replaced
by complex; the center line is kept and moved together with the cones; the global random module
is no longer used, so a seed fully determines the track; the center line is resampled to a fixed
spacing; the output is a track_database Track.

The track starts at (0, 0) facing +x, at the end of its straightest stretch, between 4 big
orange cones. The same seed and parameters always give the same track.
"""

import cmath
import math
import random
from dataclasses import dataclass

import numpy as np

from .tracks import Track

__all__ = ["RandomTrackParams", "generate_random_track"]


@dataclass
class RandomTrackParams:
    min_corner_radius: float = 3.0  # [m] of the center line (FS hairpin)
    track_width: float = 3.0  # [m]
    max_frequency: int = 7  # track complexity
    amplitude: float = 1 / 3  # track complexity
    min_length: float = 150.0  # [m] shorter tracks are rejected
    max_length: float = 500.0  # [m] longer tracks are rejected
    spacing: float = 2.0  # [m] center line spacing
    margin: float = 1.0  # [m] min gap between two parts of the track
    starting_straight_length: float = 6.0  # [m]
    min_cone_spacing: float = 3 * math.pi / 16  # [m]
    max_cone_spacing: float = 5.0  # [m]
    cone_spacing_bias: float = 0.5
    starting_cone_spacing: float = 0.5  # [m] between the big orange cones of a side


# ---------------------------------------------------------------------------------- path ----


def corner_radii(dt, dpdt):
    """Signed radius of curvature at every sample of a closed path given by its derivative."""
    ddpdt = np.append(np.diff(dpdt), dpdt[0] - dpdt[-1]) / dt
    return abs(dpdt) ** 3 / (np.conj(dpdt) * ddpdt).imag


def generate_path(rng, n_points, min_corner_radius, max_frequency, amplitude):
    """Random closed path: the unit circle plus waves of frequency 2..max_frequency with random
    phases, scaled so that its sharpest corner has a radius of exactly min_corner_radius.

    Returns (points, normals, radii): complex positions [m], unit left normals, signed corner
    radii [m], all of length n_points.
    """
    z = np.exp(2j * np.pi * np.arange(n_points) / n_points)
    waves = np.zeros(n_points, dtype=complex)
    dwaves = np.zeros(n_points, dtype=complex)
    for frequency in range(2, max_frequency + 1):
        phase = cmath.exp(2j * math.pi * rng.random())
        z_pow = z**frequency
        waves += z * (
            z_pow / (phase * (frequency + 1)) + phase / (z_pow * (frequency - 1))
        )
        dwaves += z_pow / phase - phase / z_pow

    points = z + amplitude * waves
    dpdt = (1j * z) * (1 + amplitude * dwaves)
    normals = 1j * dpdt / abs(dpdt)
    radii = corner_radii(2 * math.pi / n_points, dpdt)
    scale = min_corner_radius / min(abs(radii))
    return scale * points, normals, scale * radii


# ---------------------------------------------------------------------- self-intersection ----


def _intersects(p, dp, q, dq):
    """True if the segments p -> p + dp and q -> q + dq intersect."""
    q = (q - p) / dp
    dq = dq / dp
    if dq.imag == 0:
        return q.imag == 0 and q.real < 1 and q.real + dq.real > 0
    return (
        q.imag * (q.imag + dq.imag) <= 0 and 0 < q.real - dq.real * q.imag / dq.imag < 1
    )


def _intersects_brute(edges):
    for i, e_i in enumerate(edges):
        for e_j in edges[i + 1 :]:
            if e_j[0] == e_i[1] or e_j[1] == e_i[0]:  # adjacent edges share a point
                continue
            if _intersects(e_i[0], e_i[1] - e_i[0], e_j[0], e_j[1] - e_j[0]):
                return True
    return False


def _side(p, dp, edges):
    side0 = np.sign(((edges[:, 0] - p) / dp).imag)
    side1 = np.sign(((edges[:, 1] - p) / dp).imag)
    return np.sign(side0 + side1)


def _intersects_recurse(edges, rng):
    """Splits the edges in two halves along a line and recurses, brute force when small."""
    if len(edges) <= 8:
        return _intersects_brute(edges)
    center = sum(edges[:, 0] + edges[:, 1]) / (2 * len(edges))
    pivot = edges[len(edges) // 2][0]
    for _ in range(32):
        side = _side(center, pivot - center, edges)
        left, right = edges[side >= 0], edges[side <= 0]
        if (
            abs(len(left) / len(edges) - 0.5) + abs(len(right) / len(edges) - 0.5)
            < 1 / 8
        ):
            return _intersects_recurse(left, rng) or _intersects_recurse(right, rng)
        pivot = edges[rng.randrange(len(edges))][0]
    return _intersects_brute(edges)


def self_intersects(points, normals, margin, rng):
    """True if the track comes within `margin` of itself (both borders are checked)."""

    def edges(p):
        return np.column_stack((p, np.roll(p, -1)))

    return _intersects_recurse(
        edges(points + margin * normals), rng
    ) or _intersects_recurse(edges(points - margin * normals), rng)


# ------------------------------------------------------------------------- starting line ----


def _cyclic_smooth(indices, points, values, diameter):
    distance_to_next = abs(np.append(np.diff(points), points[0] - points[-1]))
    smoothed = values[indices].astype(float)
    for n, i in enumerate(indices):
        coef_sum = 1.0
        curr = (i if i != 0 else len(values)) - 1
        distance = distance_to_next[curr]
        while distance < diameter:
            coef = distance_to_next[curr] * math.sin(math.pi * distance / diameter)
            smoothed[n] += coef * values[curr]
            coef_sum += coef
            curr = (curr if curr != 0 else len(values)) - 1
            distance += distance_to_next[curr]
        smoothed[n] /= coef_sum
    return smoothed


def start_index(points, radii, straight_length, downsample=2):
    """Index of the end of the straightest stretch of length straight_length."""
    curvature = abs(1 / radii[::downsample])
    candidates = np.argsort(curvature)[: len(curvature) // 8]
    smoothed = _cyclic_smooth(
        candidates, points[::downsample], curvature, 1.5 * straight_length
    )
    return downsample * candidates[np.argmin(smoothed)]


# --------------------------------------------------------------------------------- cones ----


def place_cones(
    points, normals, radii, min_corner_radius, min_spacing, max_spacing, width, bias
):
    """Blue (left) and yellow (right) cones at width / 2 either side of the center line,
    denser where the corners are tight."""
    min_density, max_density = 1 / max_spacing, 1 / min_spacing
    density_range = max_density - min_density
    c1 = density_range / 2 * ((1 - bias) * min_corner_radius - (1 + bias) * width / 2)
    c2 = density_range / 2 * ((1 + bias) * min_corner_radius - (1 - bias) * width / 2)

    def place(border, border_radii, side):
        distance_to_next = abs(np.append(np.diff(border), border[0] - border[-1]))
        density = min_density + side * c1 / border_radii + c2 / abs(border_radii)
        density *= np.roll(distance_to_next, 1)
        threshold = sum(density) / round(sum(density))  # first and last cones match up
        cones, current = [border[0]], 0.0
        for i, d in enumerate(density[1:]):
            current += d
            if current >= threshold:
                current -= threshold
                cones.append(border[i])
        return np.array(cones)

    blue = place(points + normals * width / 2, radii - width / 2, 1)
    yellow = place(points - normals * width / 2, radii + width / 2, -1)
    return blue, yellow


# ------------------------------------------------------------------------------- generate ----


def resample(points, spacing):
    """Closed polyline resampled at (almost) equal arc-length spacing."""
    closed = np.append(points, points[0])
    s = np.concatenate(([0.0], np.cumsum(abs(np.diff(closed)))))
    n = max(int(round(s[-1] / spacing)), 8)
    s_new = np.linspace(0.0, s[-1], n, endpoint=False)
    return np.interp(s_new, s, closed.real) + 1j * np.interp(s_new, s, closed.imag)


def polyline_min_radius(points):
    """Smallest radius of the circle through three consecutive points of a closed polyline."""
    a, b, c = np.roll(points, 1), points, np.roll(points, -1)
    cross = ((b - a).conj() * (c - b)).imag
    denom = abs(b - a) * abs(c - b) * abs(c - a)
    kappa = np.abs(2 * cross / denom)
    return 1 / kappa.max()


def generate_random_track(seed: int, name: str, params: RandomTrackParams = None):
    """One random track. Returns (Track, info), info being a dict of the seed, the generation
    parameters, the actual length and the min corner radius of the center line."""
    p = params or RandomTrackParams()
    rng = random.Random(seed)
    width = p.track_width
    margin = width / 2 + p.margin

    # Resolution of the dense path, as in the EUFS generator.
    t = p.amplitude * p.max_frequency
    approx_length = ((0.6387 * t + 43.86) * t + 123.1) * t + 35.9
    r = math.log2(approx_length) / p.min_corner_radius
    n_points = int(
        4 * approx_length * max(1 / p.min_cone_spacing, r / p.max_cone_spacing)
    )

    for _ in range(1000):
        points, normals, radii = generate_path(
            rng, n_points, p.min_corner_radius, p.max_frequency, p.amplitude
        )
        length = float(sum(abs(np.diff(np.append(points, points[0])))))
        if p.min_length <= length <= p.max_length and not self_intersects(
            points, normals, margin, rng
        ):
            break
    else:
        raise RuntimeError(
            f"seed {seed}: no valid track in 1000 attempts, relax the limits"
        )

    # Start at the end of the straightest stretch, at (0, 0), facing +x. The center line and
    # the cones get the same transform so that they stay together.
    i0 = start_index(points, radii, p.starting_straight_length)
    points, normals, radii = (np.roll(a, -i0) for a in (points, normals, radii))
    rotation = 1j / normals[0]
    points = (points - points[0]) * rotation
    normals = normals * rotation

    blue, yellow = place_cones(
        points,
        normals,
        radii,
        p.min_corner_radius,
        p.min_cone_spacing,
        p.max_cone_spacing,
        width,
        p.cone_spacing_bias,
    )
    half = p.starting_cone_spacing / 2
    orange = np.array(
        [blue[0] + half, yellow[0] + half, blue[0] - half, yellow[0] - half]
    )
    blue, yellow = blue[1:], yellow[1:]

    center = resample(points, p.spacing)
    cones = np.concatenate((blue, yellow, orange))
    track = Track(
        name=name,
        cones=np.column_stack((cones.real, cones.imag)),
        colors=["blue"] * len(blue) + ["yellow"] * len(yellow) + ["big_orange"] * 4,
        sides=["left"] * len(blue) + ["right"] * len(yellow) + ["unknown"] * 4,
        center_line=np.column_stack((center.real, center.imag)),
        widths=np.full((len(center), 2), width / 2),
    )
    info = {
        "seed": seed,
        "length_m": round(length, 3),
        "min_corner_radius_m": p.min_corner_radius,
        "center_line_min_radius_m": round(float(polyline_min_radius(center)), 3),
        "track_width_m": width,
        "center_line_spacing_m": p.spacing,
        "max_frequency": p.max_frequency,
        "amplitude": p.amplitude,
        "generator": "track_database.random_track (adapted from the EUFS track generator)",
    }
    return track, info
