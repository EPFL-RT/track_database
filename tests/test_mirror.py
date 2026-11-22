import numpy as np
import pytest

from track_database import generate_random_track, save_track, check_track
from track_database.mirror import mirror


def test_mirror_keeps_the_start(track):
    mirrored = mirror(track)
    np.testing.assert_allclose(mirrored.center_line[:2], track.center_line[:2])


def test_mirror_keeps_blue_on_the_left(track):
    # the straight track starts at (0, -5) driving along +y: its start axis is x = 0
    mirrored = mirror(track)
    assert np.all(mirrored.cones_of("blue")[:, 0] < 0)
    assert mirrored.colors.count("blue") == track.colors.count("yellow")
    assert mirrored.sides[mirrored.colors.index("blue")] == "left"


def test_mirror_swaps_the_widths(track):
    track.widths = np.column_stack((np.linspace(1.0, 2.0, 7), np.linspace(3.0, 4.0, 7)))
    np.testing.assert_array_equal(mirror(track).widths, track.widths[:, ::-1])


def test_mirror_twice_is_identity(track):
    twice = mirror(mirror(track))
    np.testing.assert_allclose(twice.cones, track.cones, atol=1e-12)
    np.testing.assert_allclose(twice.center_line, track.center_line, atol=1e-12)
    np.testing.assert_array_equal(twice.widths, track.widths)
    assert twice.colors == track.colors and twice.sides == track.sides


@pytest.mark.parametrize("seed", [0, 3])
def test_mirror_of_a_track_starting_along_x(tmp_path, seed):
    track, _ = generate_random_track(seed, f"t{seed}")  # starts at (0, 0) facing +x
    mirrored = mirror(track)
    np.testing.assert_allclose(
        mirrored.center_line[:2], track.center_line[:2], atol=1e-12
    )
    assert check_track(save_track(mirrored, str(tmp_path))).errors == []


def test_mirrored_track_stays_valid(tmp_path, track):
    report = check_track(save_track(mirror(track), str(tmp_path)))
    assert report.issues == []


def test_same_first_points_is_an_error(track):
    track.center_line[1] = track.center_line[0]
    with pytest.raises(ValueError, match="first two center line points are the same"):
        mirror(track)


def test_one_point_center_line_is_an_error(track):
    track.center_line, track.widths = track.center_line[:1], track.widths[:1]
    with pytest.raises(ValueError, match="at least 2 points"):
        mirror(track)
