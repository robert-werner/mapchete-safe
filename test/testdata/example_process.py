#!/usr/bin/env python
"""Example process file."""

from mapchete import MapcheteProcess
import numpy as np

class Process(MapcheteProcess):
    """Main process class."""

    def __init__(self, **kwargs):
        """Process initialization."""
        # init process
        MapcheteProcess.__init__(self, **kwargs)
        self.identifier = "my_process_id",
        self.title = "My long process title",
        self.version = "0.1",
        self.abstract = "short description on what my process does"

    def execute(self):
        """User defined process."""
        # Reading and writing data works like this:
        with self.open("file1", resampling="bilinear") as raster_file:
            if raster_file.is_empty(1):
                return "empty"

            return [
                np.clip(band, 0, 255)
                for band in raster_file.read([3, 2, 1])
            ]
