import os

from track_database import load_track
from track_database.cli import main


def test_check(track_folder, capsys):
    assert main(["check", track_folder]) == 0
    assert "1/1 tracks valid" in capsys.readouterr().out


def test_check_fails_on_errors(track_folder, capsys):
    os.remove(os.path.join(track_folder, "straight_center_line.csv"))
    assert main(["check", os.path.dirname(track_folder)]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out and "missing file" in out


def test_strict_fails_on_warnings(track_folder):
    with open(os.path.join(track_folder, "straight_cones.csv")) as f:
        lines = f.read().splitlines()
    with open(os.path.join(track_folder, "straight_cones.csv"), "w") as f:
        f.write("\n".join(l for l in lines if "big_orange" not in l) + "\n")
    assert main(["check", track_folder]) == 0
    assert main(["check", "--strict", track_folder]) == 1


def test_generate_random(tmp_path):
    out = str(tmp_path)
    assert main(["generate", "random", out, "--count", "2", "--start-seed", "5"]) == 0
    assert sorted(os.listdir(out)) == ["track_rand_005", "track_rand_006"]
    assert sorted(os.listdir(os.path.join(out, "track_rand_005"))) == [
        "track_rand_005_center_line.csv",
        "track_rand_005_cones.csv",
        "track_rand_005_meta.json",
    ]
    assert main(["check", out]) == 0


def test_mirror(track_folder, tmp_path):
    out = str(tmp_path / "mirrored")
    assert main(["mirror", track_folder, out]) == 0
    assert load_track(out).name == "mirrored"
    assert main(["mirror", track_folder, out]) == 1  # exists, no --force
    assert main(["mirror", track_folder, out, "--force"]) == 0


def test_plot(track_folder, tmp_path):
    image = str(tmp_path / "plot.png")
    assert main(["plot", track_folder, "--save", image]) == 0
    assert os.path.getsize(image) > 0


def test_bad_track_is_an_error_message(tmp_path, capsys):
    assert main(["plot", str(tmp_path / "nope")]) == 1
    assert "error:" in capsys.readouterr().err


def test_generate_refuses_to_overwrite(tmp_path, capsys):
    out = str(tmp_path)
    assert main(["generate", "random", out, "--count", "1"]) == 0
    assert main(["generate", "random", out, "--count", "1"]) == 1
    assert "use --force" in capsys.readouterr().err
    assert main(["generate", "random", out, "--count", "1", "--force"]) == 0


def test_check_fails_on_an_empty_folder(tmp_path):
    assert main(["check", str(tmp_path)]) == 1
