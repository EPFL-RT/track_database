import numpy as np
import pytest

from track_database import list_tracks, load_track
from track_database.utils import save_center_line, save_cones

BLUE = np.array([[-1.5, 0.0], [-1.5, 5.0]])
YELLOW = np.array([[1.5, 0.0], [1.5, 5.0]])
BIG_ORANGE = np.array([[-1.5, 10.0], [1.5, 10.0]])
CENTER = np.array([[0.0, 0.0], [0.0, 5.0], [0.0, 10.0]])
WIDTHS = np.full((3, 2), 1.5)


def _make_track(folder, name, center_line=True, prefix=None):
    track_dir = folder / name
    track_dir.mkdir(parents=True)
    prefix = name if prefix is None else prefix
    save_cones(str(track_dir / f"{prefix}_cones.csv"), BLUE, YELLOW, BIG_ORANGE, [])
    if center_line:
        save_center_line(str(track_dir / f"{prefix}_center_line.csv"), CENTER, WIDTHS)
    return track_dir


@pytest.fixture
def tracks_dir(tmp_path):
    _make_track(tmp_path, "my_track")
    _make_track(tmp_path, "no_center_line", center_line=False)
    _make_track(tmp_path, "renamed", prefix="other_name")
    return tmp_path


def _check(track):
    np.testing.assert_array_equal(track.blue_cones, BLUE)
    np.testing.assert_array_equal(track.yellow_cones, YELLOW)
    np.testing.assert_array_equal(track.big_orange_cones, BIG_ORANGE)
    assert track.small_orange_cones.shape == (0, 2)
    np.testing.assert_array_equal(track.left_cones, np.vstack((BLUE, BIG_ORANGE[:1])))


def test_load_by_name_with_explicit_dir(tracks_dir):
    track = load_track("my_track", tracks_dir=str(tracks_dir))
    assert track.name == "my_track"
    _check(track)
    np.testing.assert_allclose(track.center_line, CENTER)
    np.testing.assert_allclose(track.track_widths, WIDTHS)


def test_tracks_dir_with_trailing_slash(tracks_dir):
    track = load_track("my_track", str(tracks_dir) + "/")
    assert track.name == "my_track"
    _check(track)


def test_any_prefix(tracks_dir):
    _check(load_track("renamed", tracks_dir=str(tracks_dir)))


def test_missing_center_line_raises(tracks_dir):
    with pytest.raises(ValueError, match="center line"):
        load_track("no_center_line", tracks_dir=str(tracks_dir))


def test_list_tracks(tracks_dir):
    assert list_tracks(str(tracks_dir)) == ["my_track", "no_center_line", "renamed"]


def test_not_found_lists_available(tracks_dir):
    with pytest.raises(ValueError, match="my_track"):
        load_track("does_not_exist", tracks_dir=str(tracks_dir))
