# track_database

A command line tool (and small Python package) to **check, plot, generate and mirror**
Formula Student track folders. The tracks themselves live in BRAINS, which reads
them with its own readers.

This repository defines the **track contract** below: the file format BRAINS expects.
`track-db check` tests a folder against it, so a broken track is caught before a node
fails on it.

## Install

```bash
uv tool install "git+https://github.com/EPFL-RT/track_database.git@v4.0.0"
# or: pip install "git+https://github.com/EPFL-RT/track_database.git@v4.0.0"
```

This installs the `track-db` command (`python -m track_database` works too).

## Usage

```bash
track-db check ~/brains/tracks            # every track of a tracks folder
track-db check ~/brains/tracks/skidpad    # one track
track-db plot ~/brains/tracks/skidpad        # or --save skidpad.png
track-db generate random ~/brains/tracks --count 5 --start-seed 100
track-db mirror ~/brains/tracks/fsds_competition_1 ~/brains/tracks/fsds_competition_1_mirrored
```

- `check` prints the errors and warnings of each track, with the file and line, and exits
  with 1 if a track has an error (`--strict`: or a warning).
- `generate random` writes closed tracks `<prefix><seed>/` (default prefix `track_rand_`),
  with a `<name>_meta.json` of the seed and parameters. The same seed always gives the same
  track. `track-db generate random --help` lists the parameters (width, corner radius, length,
  cone spacing...). The generator is adapted from the
  [EUFS track generator](https://gitlab.com/eufs/public/eufs_sim) (see License).
- `mirror` writes the mirror image of a track, named after its new folder. It mirrors
  across the start axis, so the start and its direction don't change. Blue and yellow 
  cones are swapped so that blue cones stay on the left.

## Track contract

A track named `<name>` is a folder `<name>/` containing exactly these two files:

**`<name>_cones.csv`**, one cone per row:
```
cone_type,X,Y,Z,std_X,std_Y,std_Z,right,left
blue,-1.5,5.0,0.0,0.0,0.0,0.0,0,1
```
- `cone_type`: `blue`, `yellow`, `big_orange` or `small_orange`.
- `X`, `Y` [m]: position. `Z` and the standard deviations `std_*`.
- `right`, `left`: 0 or 1, the side of the track the cone is on (not both 1).

**`<name>_center_line.csv`**, at least 2 points:
```
x,y,right_width,left_width
0.0,0.0,1.5,1.5
```
- `x`, `y` [m]: center line point. `right_width`, `left_width` [m] > 0: distance to the
  right and left borders.

Both files: the header is exactly the one above, without spaces (a leading `# `, as written
by `numpy.savetxt`, is accepted), every row has all the columns, there are no spaces around
the values, the numbers are plain decimals with an optional exponent (`1.5`, `-2e-3`; no
`nan` or `inf`), and there are no blank lines.

`track-db check` reports as **errors** everything above, plus a start line that doesn't 
cross the center line. It reports as **warnings**: blue cones not marked left or yellow ones 
not marked right, duplicate cones (closer than 5 cm), fewer than 2 big orange cones and a 
track narrower than 3 m.

## Python

```python
from track_database import load_track, save_track, check_track, generate_random_track
from track_database.mirror import mirror

track = load_track("~/brains/tracks/fsds_competition_1")
track.cones, track.colors, track.sides     # (N, 2) positions, one color and side per cone
track.center_line, track.widths            # (M, 2) points, (M, 2) right and left widths
save_track(mirror(track), "/tmp/tracks")   # writes /tmp/tracks/fsds_competition_1/
check_track("/tmp/tracks/skidpad").errors
```

## Development

```bash
pip install -e . pytest
python -m pytest tests
```

## License

MIT (see LICENSE.md), except `track_database/random_track.py`, which is derived from the EUFS
track generator and stays under the Apache License 2.0 (see `track_database/LICENSE.eufs_sim`).
