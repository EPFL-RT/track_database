import os

import numpy as np
import pytest

from track_database import load_track, save_track


def test_save_then_load_gives_the_same_track(track, track_folder):
    assert os.path.basename(track_folder) == "straight"
    assert sorted(os.listdir(track_folder)) == [
        "straight_center_line.csv",
        "straight_cones.csv",
    ]
    loaded = load_track(track_folder)
    assert loaded.name == "straight"
    np.testing.assert_array_equal(loaded.cones, track.cones)
    assert loaded.colors == track.colors
    assert loaded.sides == track.sides
    np.testing.assert_array_equal(loaded.center_line, track.center_line)
    np.testing.assert_array_equal(loaded.widths, track.widths)


def test_full_precision_by_default(tmp_path, track):
    track.cones[0] = [1234.56789012345, -0.000123456789012345]
    loaded = load_track(save_track(track, str(tmp_path)))
    np.testing.assert_array_equal(loaded.cones[0], track.cones[0])


def test_fixed_decimals(tmp_path, track):
    folder = save_track(track, str(tmp_path), decimals=4)
    with open(os.path.join(folder, "straight_cones.csv")) as f:
        f.readline()
        assert f.readline().startswith("blue,-1.5000,5.0000,")


def test_trailing_slash(track_folder):
    assert load_track(track_folder + "/").name == "straight"


def test_hash_header(track, track_folder):
    path = os.path.join(track_folder, "straight_center_line.csv")
    with open(path) as f:
        content = f.read()
    with open(path, "w") as f:
        f.write("# " + content)  # as written by numpy.savetxt
    np.testing.assert_array_equal(
        load_track(track_folder).center_line, track.center_line
    )


def test_cones_of(track):
    assert track.cones_of("big_orange").shape == (2, 2)
    assert track.cones_of("small_orange").shape == (0, 2)


def test_invalid_track_points_to_check(tmp_path):
    folder = tmp_path / "broken"
    folder.mkdir()
    (folder / "broken_cones.csv").write_text("cone_type,X\nblue,oops\n")
    (folder / "broken_center_line.csv").write_text("x,y,right_width,left_width\n")
    with pytest.raises(ValueError, match="track-db check"):
        load_track(str(folder))


def test_missing_folder(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        load_track(str(tmp_path / "nope"))


def test_save_refuses_missing_sides(tmp_path, track):
    track.sides = []
    with pytest.raises(ValueError, match="same length"):
        save_track(track, str(tmp_path))


def test_save_refuses_missing_widths(tmp_path, track):
    track.widths = track.widths[:-1]
    with pytest.raises(ValueError, match="same length"):
        save_track(track, str(tmp_path))
