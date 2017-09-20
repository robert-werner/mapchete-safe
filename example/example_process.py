#!/usr/bin/env python
"""Extract and enhance Sentinel-2 RGB data."""

from mapchete import MapcheteProcess
from mapchete.errors import MapcheteEmptyInputTile
from rio_color.operations import sigmoidal, gamma, saturation
import numpy as np


class Process(MapcheteProcess):
    """Main process class."""

    def __init__(self, **kwargs):
        """Process initialization."""
        # init process
        MapcheteProcess.__init__(self, **kwargs)
        self.identifier = "safe_to_rgb",
        self.title = "Extract and enhance Sentinel-2 RGB data",
        self.version = "0.1",
        self.abstract = "Use rio-color to enhance RGB data from Sentinel-2"

    def execute(self):
        """Enhance RGB colors from a Sentinel-2 SAFE archive."""
        # read input SAFE file
        with self.open(
            "input_file", resampling=self.params["resampling"]
        ) as safe_file:
            try:
                # read red, green and blue bands & scale to 8 bit
                rgb = np.clip(
                    safe_file.read(
                        [4, 3, 2],
                        mask_clouds=self.params["mask_clouds"],
                        mask_white_areas=self.params["mask_white_areas"]
                    ) / 16, 0, 255
                ).astype("uint8")
            except MapcheteEmptyInputTile:
                return "empty"

        # scale to 0 to 1 for filters
        red, green, blue = rgb.astype("float") / 255

        # save nodata mask for later & remove rgb to free memory
        mask = rgb.mask
        del rgb

        # using rio-color:
        # (1) apply gamma correction to each band individually
        # (2) add sigmoidal contrast & bias
        # (3) add saturation
        enhanced = np.clip(
            saturation(
                sigmoidal(
                    np.stack([
                        # apply gamma correction for each band
                        gamma(red, self.params["red_gamma"]),
                        gamma(green, self.params["green_gamma"]),
                        gamma(blue, self.params["blue_gamma"]),
                    ]),
                    self.params["sigmoidal_contrast"],
                    self.params["sigmoidal_bias"]
                ),
                self.params["saturation"]
            ) * 255,    # scale back to 8bit
            1, 255      # clip valid values from 1 to 255
        )

        # use original nodata mask and return
        return np.where(mask, 0, enhanced).astype("uint8")
