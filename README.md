# track_database

Python and C++ utilities to load, save and create Formula Student tracks stored as
CSV files (in a format compatible with FSDS).

**This repository contains no tracks.** The tracks live in a *tracks folder* owned
by whoever uses this package (in brains: `brains/tracks`). Every function takes
that folder explicitly: `load_track(name, tracks_dir)` loads the track stored in
`<tracks_dir>/<name>/`. If it doesn't exist, the error lists the available tracks
(`list_tracks(tracks_dir)` returns them too). To add a track, drop a new folder in
the tracks folder; nothing has to change in this repository.

## Track folder format

A track named `track_name` is a folder `track_name/` containing:
- `track_name_cones.csv`: the cones positions, in the format
  `cone_type,X,Y,Z,std_X,std_Y,std_Z,right,left`.
  The `cone_type` is either `blue`, `yellow`, `big_orange` or `small_orange`.
  The `right` and `left` columns are binary (0 or 1) values indicating if the cone
  is on the right or left side of the track.
  `std_X`, `std_Y` and `std_Z` are the standard deviations of the cone position,
  usually 0.
- `track_name_center_line.csv`: the center line points, in the format
  `x,y,right_width,left_width` (a leading `#` in the header is accepted).

If the files are not prefixed with the folder name, any `*cones.csv` /
`*center_line.csv` file in the folder is used.

## Python

Install with `pip` (or `uv`), e.g. pinned to a tag:
```
pip install "git+https://github.com/EPFL-RT/track_database.git@v4.0.0"
```

```python
import track_database as tdb

track = tdb.load_track("skidpad", "~/brains/tracks")
track.blue_cones, track.center_line, track.track_widths  # numpy arrays (N, 2)
tdb.list_tracks("~/brains/tracks")
```

Modules:
- `tracks.py`: the `Track` class (a *Plain Old Data Structure* containing the blue,
  yellow, big orange, small orange, left and right cones positions, the center
  line points and the track widths), `load_track` and `list_tracks`.
- `utils.py`: IO functions to save and load cones and center line files.
- `primitives.py`: functions to create tracks, such as `line()`, `circle()` and
  `circular_arc()`.
- `track_generator.py`: random track generator
  (`python track_generator.py --track_name my_track --output_dir <tracks_dir>`).
- `export_as_world.py`: export a track as a Gazebo `.world` file.

## C++

A header-only library (C++17, depends only on Eigen) in [`cpp/`](cpp/), with the
same API in the `track_database` namespace:

```cpp
#include "track_database/track_database.hpp"

auto track = track_database::load_track("skidpad", "/path/to/tracks");
track.blue_cones;     // Eigen::MatrixX2d
track.center_line;    // Eigen::MatrixX2d
track_database::save_cones("out_cones.csv", track.blue_cones, track.yellow_cones);
```

Use it from CMake with `FetchContent`, pinned to the same tag as the Python package:
```cmake
include(FetchContent)
FetchContent_Declare(track_database
    GIT_REPOSITORY https://github.com/EPFL-RT/track_database.git
    GIT_TAG v4.0.0
    SOURCE_SUBDIR cpp)
FetchContent_MakeAvailable(track_database)
target_link_libraries(my_target PRIVATE track_database::track_database)
```

## Tests

```
pytest tests/test_tracks.py
cmake -S cpp -B build -DTRACK_DATABASE_BUILD_TESTS=ON && cmake --build build && ./build/test_tracks [tracks_folder]
```
