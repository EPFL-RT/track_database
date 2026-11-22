import os
from dataclasses import replace

import pytest

from track_database import check_path, check_track, save_track


def _edit(folder, kind, edit):
    """Rewrites <name>_<kind>.csv of the track folder with edit(lines) -> lines."""
    path = os.path.join(folder, f"{os.path.basename(folder)}_{kind}.csv")
    with open(path) as f:
        lines = f.read().rstrip("\n").split("\n")
    with open(path, "w") as f:
        f.write("\n".join(edit(lines)) + "\n")


def _messages(report, level="error"):
    return [i.message for i in report.issues if i.level == level]


def test_valid_track_has_no_issue(track_folder):
    assert check_track(track_folder).issues == []


@pytest.mark.parametrize(
    "kind,edit,expected",
    [
        (
            "cones",
            lambda ls: ls[:2] + ["<<<<<<< HEAD"] + ls[2:],
            "merge conflict marker",
        ),
        ("cones", lambda ls: ls[:2] + [""] + ls[2:], "blank line"),
        ("cones", lambda ls: ["cone_type,X,Y"] + ls[1:], "header must be"),
        ("cones", lambda ls: [ls[0].replace(",", ", ")] + ls[1:], "header must be"),
        ("cones", lambda ls: ls[:1] + [" " + ls[1]] + ls[2:], "spaces around a value"),
        (
            "cones",
            lambda ls: ls[:1] + [ls[1].replace(",", ", ", 1)] + ls[2:],
            "spaces around",
        ),
        (
            "cones",
            lambda ls: ls[:1] + ["red" + ls[1][4:]] + ls[2:],
            "unknown cone_type",
        ),
        (
            "cones",
            lambda ls: ls[:1] + [ls[1].replace("5.0", "nan")] + ls[2:],
            "numbers like",
        ),
        (
            "cones",
            lambda ls: ls[:1] + [ls[1] + ",1"] + ls[2:],
            "10 values instead of 9",
        ),
        (
            "cones",
            lambda ls: ls[:1] + [ls[1].replace("5.0", "5.0abc")] + ls[2:],
            "numbers like",
        ),
        (
            "cones",
            lambda ls: ls[:1] + [ls[1][:-3] + "1,1"] + ls[2:],
            "both right and left",
        ),
        ("cones", lambda ls: ls[:1], "no cones"),
        ("center_line", lambda ls: ls[:2], "at least 2 points"),
        (
            "center_line",
            lambda ls: ls[:1] + [ls[1].replace("1.5", "0.0", 1)] + ls[2:],
            "must be positive",
        ),
    ],
)
def test_errors(track_folder, kind, edit, expected):
    _edit(track_folder, kind, edit)
    errors = _messages(check_track(track_folder))
    assert any(expected in e for e in errors), errors


def test_hash_header_is_accepted(track_folder):
    _edit(track_folder, "center_line", lambda ls: ["# " + ls[0]] + ls[1:])
    assert check_track(track_folder).issues == []


def test_error_gives_the_line(track_folder):
    _edit(track_folder, "cones", lambda ls: ls[:3] + ["=======", *ls[3:]])
    (issue,) = check_track(track_folder).errors
    assert issue.line == 4 and str(issue).endswith("4: merge conflict marker: =======")


def test_missing_file_suggests_renaming(track_folder):
    os.rename(
        os.path.join(track_folder, "straight_cones.csv"),
        os.path.join(track_folder, "cones.csv"),
    )
    errors = _messages(check_track(track_folder))
    assert any("found cones.csv: rename it" in e for e in errors), errors


def test_extra_files_are_ignored(track_folder):
    with open(os.path.join(track_folder, "straight_meta.json"), "w") as f:
        f.write("{}")
    assert check_track(track_folder).issues == []


@pytest.mark.parametrize(
    "edit,expected",
    [
        (lambda ls: ls + [ls[1]], "duplicate cone"),
        (
            lambda ls: ls[:1] + [ls[1][:-3] + "1,0"] + ls[2:],
            "blue cone not marked as left",
        ),
        (lambda ls: [l for l in ls if not l.startswith("big_orange")], "no start line"),
    ],
)
def test_warnings(track_folder, edit, expected):
    _edit(track_folder, "cones", edit)
    report = check_track(track_folder)
    assert report.errors == []
    assert any(expected in w for w in _messages(report, "warning"))


def test_start_line_must_cross_the_center_line(track_folder):
    # move the start line to the side of the track, away from the center line
    _edit(
        track_folder,
        "cones",
        lambda ls: [
            l.replace("big_orange,-1.6,", "big_orange,10.0,").replace(
                "big_orange,1.6,", "big_orange,12.0,"
            )
            for l in ls
        ],
    )
    assert any("start line" in e for e in _messages(check_track(track_folder)))


def test_narrow_track_warning(track_folder):
    _edit(
        track_folder,
        "center_line",
        lambda ls: [l.replace(",1.5,1.5", ",1.0,1.0") for l in ls],
    )
    assert any("narrower" in w for w in _messages(check_track(track_folder), "warning"))


def test_check_path_on_a_tracks_folder(tmp_path, track):
    save_track(track, str(tmp_path))
    save_track(replace(track, name="other"), str(tmp_path))
    reports = check_path(str(tmp_path))
    assert [os.path.basename(r.folder) for r in reports] == ["other", "straight"]
