import numpy as np
import pytest

from track_database import (
    RandomTrackParams,
    generate_random_track,
    save_track,
    check_track,
)


@pytest.mark.parametrize("seed", [0, 1, 7])
def test_random_tracks_are_valid(tmp_path, seed):
    track, info = generate_random_track(seed, f"track_rand_{seed:03d}")
    assert 150.0 <= info["length_m"] <= 500.0
    report = check_track(save_track(track, str(tmp_path), decimals=4))
    assert report.errors == [], report.errors


def test_same_seed_same_track():
    a, _ = generate_random_track(3, "a")
    b, _ = generate_random_track(3, "b")
    np.testing.assert_array_equal(a.cones, b.cones)
    np.testing.assert_array_equal(a.center_line, b.center_line)
    c, _ = generate_random_track(4, "c")
    assert not np.array_equal(a.cones, c.cones)


@pytest.mark.parametrize("straight", [6.0, 25.0])
def test_spawn_at_the_origin_facing_y_before_the_start_line(straight):
    params = RandomTrackParams(starting_straight_length=straight)
    track, _ = generate_random_track(0, "t", params)
    # the center line starts at the spawn (0, 0), facing +y
    np.testing.assert_allclose(track.center_line[0], [0.0, 0.0], atol=1e-9)
    direction = track.center_line[1] - track.center_line[0]
    assert abs(np.degrees(np.arctan2(direction[1], direction[0])) - 90.0) < 2.0
    # the start line (4 big orange cones) is `straight` further along the center line
    orange = track.cones_of("big_orange")
    assert len(orange) == 4
    steps = np.linalg.norm(np.diff(track.center_line, axis=0), axis=1)
    along = np.concatenate(([0.0], np.cumsum(steps)))
    nearest = np.argmin(np.linalg.norm(track.center_line - orange.mean(axis=0), axis=1))
    assert abs(along[nearest] - straight) <= params.spacing


def test_parameters_are_used():
    track, info = generate_random_track(0, "t", RandomTrackParams(track_width=4.0))
    assert info["track_width_m"] == 4.0
    np.testing.assert_array_equal(track.widths, 2.0)
