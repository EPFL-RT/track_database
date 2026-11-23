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


def test_start_line_is_ahead_of_the_spawn_facing_y():
    ahead = RandomTrackParams().starting_straight_length
    track, _ = generate_random_track(0, "t")
    np.testing.assert_allclose(track.center_line[0], [0.0, ahead], atol=1e-9)
    direction = track.center_line[1] - track.center_line[0]
    assert abs(np.degrees(np.arctan2(direction[1], direction[0])) - 90.0) < 2.0
    orange = track.cones_of("big_orange")
    assert len(orange) == 4
    np.testing.assert_allclose(orange[:, 1].mean(), ahead)
    # the spawn (0, 0) is inside the track, behind the start line
    assert np.min(np.linalg.norm(track.center_line, axis=1)) < 1.5


def test_parameters_are_used():
    track, info = generate_random_track(0, "t", RandomTrackParams(track_width=4.0))
    assert info["track_width_m"] == 4.0
    np.testing.assert_array_equal(track.widths, 2.0)
