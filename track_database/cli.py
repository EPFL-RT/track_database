"""
track-db: command line tool to check, plot, generate and mirror track folders.

    track-db check <track folder or tracks folder>...
    track-db plot <track folder> [--save plot.png]
    track-db generate random <tracks folder> [--count 20] [--start-seed 0] ...
    track-db mirror <track folder> <new track folder>
"""

import argparse
import json
import os
import sys
from dataclasses import fields, replace

from .contract import check_path
from .random_track import RandomTrackParams, generate_random_track
from .tracks import load_track, save_track
from .mirror import mirror


def _check(args) -> int:
    reports = [report for path in args.paths for report in check_path(path)]
    failed = 0
    for report in reports:
        bad = report.errors or (args.strict and report.warnings)
        failed += bool(bad)
        if report.issues or args.verbose:
            print(f"{'FAIL' if bad else 'ok'}  {report.folder}")
            for issue in report.issues:
                print(f"  {issue}")
    print(f"{len(reports) - failed}/{len(reports)} tracks valid")
    return 1 if failed else 0


def _plot(args) -> int:
    import matplotlib

    if args.save:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from .plot import plot_track

    plot_track(load_track(args.track))
    if args.save:
        plt.savefig(args.save, dpi=150, bbox_inches="tight")
        print(f"saved {args.save}")
    else:
        plt.show()
    return 0


def _generate_random(args) -> int:
    params = RandomTrackParams(
        **{f.name: getattr(args, f.name) for f in fields(RandomTrackParams)}
    )
    seeds = range(args.start_seed, args.start_seed + args.count)
    names = [f"{args.prefix}{seed:03d}" for seed in seeds]
    existing = [n for n in names if os.path.exists(os.path.join(args.out, n))]
    if existing and not args.force:
        print(
            f"{', '.join(existing)} already exist in {args.out}, "
            "use --force to overwrite them",
            file=sys.stderr,
        )
        return 1
    for seed, name in zip(seeds, names):
        track, info = generate_random_track(seed, name, params)
        folder = save_track(track, args.out, decimals=4)
        with open(os.path.join(folder, f"{name}_meta.json"), "w") as f:
            f.write(json.dumps(info, indent=2) + "\n")
        print(
            f"{folder}: {info['length_m']:6.1f} m, {len(track.center_line)} center points, "
            f"min radius {info['center_line_min_radius_m']:.2f} m"
        )
    return 0


def _mirror(args) -> int:
    track = mirror(load_track(args.track))
    out = os.path.normpath(os.path.expanduser(args.out))
    if os.path.exists(out) and not args.force:
        print(f"{out} already exists, use --force to overwrite it", file=sys.stderr)
        return 1
    folder = save_track(
        replace(track, name=os.path.basename(out)), os.path.dirname(out) or "."
    )
    print(f"saved {folder}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="track-db",
        description="Check, plot, generate and mirror track folders "
        "(<name>/<name>_cones.csv and <name>/<name>_center_line.csv).",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser(
        "check", help="check track folders against the track contract"
    )
    p.add_argument(
        "paths", nargs="+", help="track folders, or folders containing track folders"
    )
    p.add_argument("--strict", action="store_true", help="fail on warnings too")
    p.add_argument("-v", "--verbose", action="store_true", help="list valid tracks too")
    p.set_defaults(run=_check)

    p = commands.add_parser("plot", help="plot a track")
    p.add_argument("track", help="track folder")
    p.add_argument("--save", help="save the plot to this file instead of showing it")
    p.set_defaults(run=_plot)

    p = commands.add_parser("generate", help="generate tracks")
    kinds = p.add_subparsers(dest="kind", required=True)
    p = kinds.add_parser(
        "random",
        help="random closed tracks (adapted from the EUFS track generator)",
        description="Writes <out>/<prefix><seed>/ for each seed, with a <name>_meta.json "
        "of the generation parameters. The same seed always gives the same track.",
    )
    p.add_argument("out", help="tracks folder in which the track folders are created")
    p.add_argument(
        "--count", type=int, default=20, help="number of tracks (default 20)"
    )
    p.add_argument("--start-seed", type=int, default=0, help="seed of the first track")
    p.add_argument(
        "--prefix",
        default="track_rand_",
        help="name prefix (default track_rand_; BRAINS' motion planning treats track_* as "
        "trackdrive)",
    )
    p.add_argument(
        "--force", action="store_true", help="overwrite existing track folders"
    )
    defaults = RandomTrackParams()
    for f in fields(RandomTrackParams):
        p.add_argument(
            "--" + f.name.replace("_", "-"),
            dest=f.name,
            type=type(getattr(defaults, f.name)),
            default=getattr(defaults, f.name),
            help=f"(default {getattr(defaults, f.name):.4g})",
        )
    p.set_defaults(run=_generate_random)

    p = commands.add_parser(
        "mirror",
        help="write the mirror image of a track, with the same start",
        description="Mirrors the track across its start axis (the line through the first "
        "center line point, along the first center line segment): the start and its "
        "direction don't change, so the car starts the same way, and the turns go the "
        "other way. Blue and yellow cones are swapped so that blue cones stay on the left. "
        "For a skidpad, the mirror image drives the left circle first, which the FS rules "
        "don't allow. The new track is named after the folder it is written to.",
    )
    p.add_argument("track", help="track folder")
    p.add_argument(
        "out", help="new track folder, e.g. tracks/fsds_competition_1_mirrored"
    )
    p.add_argument(
        "--force", action="store_true", help="overwrite the new track folder"
    )
    p.set_defaults(run=_mirror)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.run(args)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
