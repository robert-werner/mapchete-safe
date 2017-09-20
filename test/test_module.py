#!/usr/bin/env python
"""Test SAFE read driver."""

import pytest
import os
from rasterio.errors import RasterioIOError

import mapchete
from mapchete.formats import available_input_formats, base

SCRIPTDIR = os.path.dirname(os.path.realpath(__file__))
EXAMPLE_MAPCHETE = os.path.join(*[SCRIPTDIR, "testdata", "example.mapchete"])


def test_format_available():
    """Format can be listed."""
    assert "SAFE" in available_input_formats()


def test_load_input():
    """Simply open example Mapchete process."""
    mapchete.open(EXAMPLE_MAPCHETE)


def test_input_data():
    """Input object properties and methods."""
    zoom = 13
    with mapchete.open(EXAMPLE_MAPCHETE) as mp:
        config = mp.config.at_zoom(zoom)
        assert config["input"]["s2"].path
        assert config["input"]["s2"].exists()
        assert config["input"]["s2"].bbox().is_valid
        assert isinstance(config["input"]["s2"].cloudmask, list)
        for mask in config["input"]["s2"].cloudmask:
            assert mask.is_valid


def test_input_tile():
    """Input tile properties and methods."""
    zoom = 13
    with mapchete.open(EXAMPLE_MAPCHETE) as mp:
        config = mp.config.at_zoom(zoom)
        tile = config["input"]["s2"].open(mp.get_process_tiles(zoom).next())
        assert isinstance(tile, base.InputTile)
        assert not tile.is_empty()
        # all read() related functions will raise an RasterioIOError because
        # test dataset does not contain JP2 files
        with pytest.raises(RasterioIOError):
            tile.read()
        assert tile.cloudmask
        for mask in tile.cloudmask:
            assert mask.is_valid


def test_empty_input_tile():
    """Empty Input tile properties and methods."""
    zoom = 13
    with mapchete.open(EXAMPLE_MAPCHETE) as mp:
        config = mp.config.at_zoom(zoom)
        tile = config["input"]["s2"].open(
            mp.config.process_pyramid.tile(zoom, 0, 0)
        )
        assert tile.is_empty()
