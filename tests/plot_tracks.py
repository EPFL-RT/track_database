import sys

import matplotlib.pyplot as plt
import numpy as np

from track_database import *
from track_database.utils import *

if __name__ == "__main__":
    # usage: python plot_tracks.py <tracks_dir>
    tracks_dir = sys.argv[1]
    # tracks = list_tracks(tracks_dir)
    tracks = {"VSV", "VSV_XS", "VSV_XL"}
    for track_name in tracks:
        track = load_track(track_name, tracks_dir)
        plt.figure()
        plt.title(track_name)
        plot_cones(
            track.blue_cones,
            track.yellow_cones,
            track.big_orange_cones,
            track.small_orange_cones,
            origin=np.zeros(2),
            show=False,
        )
        plt.tight_layout()
    plt.show()
