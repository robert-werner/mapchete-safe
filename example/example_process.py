#!/usr/bin/env python
"""Extract and enhance Sentinel-2 RGB data."""

from mapchete.errors import MapcheteEmptyInputTile
from rio_color.operations import sigmoidal, gamma, saturation
import numpy as np


def execute(mp):
    """Enhance RGB colors from a Sentinel-2 SAFE archive."""
    # read input SAFE file
    with mp.open(
        "input_file", resampling=mp.params["resampling"]
    ) as safe_file:
        try:
            # read red, green and blue bands & scale to 8 bit
            rgb = np.clip(
                safe_file.read(
                    [4, 3, 2],
                    mask_clouds=mp.params["mask_clouds"],
                    mask_white_areas=mp.params["mask_white_areas"]
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
                    gamma(red, mp.params["red_gamma"]),
                    gamma(green, mp.params["green_gamma"]),
                    gamma(blue, mp.params["blue_gamma"]),
                ]),
                mp.params["sigmoidal_contrast"],
                mp.params["sigmoidal_bias"]
            ),
            mp.params["saturation"]
        ) * 255,    # scale back to 8bit
        1, 255      # clip valid values from 1 to 255
    )

    # use original nodata mask and return
    return np.where(mask, 0, enhanced).astype("uint8")
