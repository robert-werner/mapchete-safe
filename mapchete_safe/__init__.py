"""Read bands from Seninel-2 SAFE archives."""

import os
import s2reader
import numpy as np
import numpy.ma as ma
from rasterio.crs import CRS
from tempfile import NamedTemporaryFile
from s2reader.s2reader import BAND_IDS

from mapchete.formats import base
from mapchete.io.vector import reproject_geometry
from mapchete.io.raster import read_raster_window


class InputData(base.InputData):
    """Main input class."""

    METADATA = {
        "driver_name": "SAFE",
        "data_type": "raster",
        "mode": "r",
        "file_extensions": ["SAFE", "zip", "ZIP"]
    }

    def __init__(self, input_params):
        """Initialize."""
        super(InputData, self).__init__(input_params)
        self.path = input_params["path"]
        with s2reader.open(self.path) as s2dataset:
            self.s2metadata = dict(
                path=s2dataset.path,
                footprint=s2dataset.footprint,
                granules=[
                    dict(
                        srid=granule.srid,
                        footprint=granule.footprint,
                        band_path={
                            index: granule.band_path(_id)
                            for index, _id in zip(range(1, 14), BAND_IDS)
                            }
                    )
                    for granule in s2dataset.granules
                ]
            )

    def open(self, tile, **kwargs):
        """Return InputTile."""
        return InputTile(tile, self, self.s2metadata, **kwargs)

    def bbox(self, out_crs=None):
        """Return data bounding box."""
        if out_crs is None:
            out_crs = self.pyramid.crs
        inp_crs = CRS().from_epsg(4326)
        if inp_crs != out_crs:
            return reproject_geometry(
                self.s2metadata["footprint"], src_crs=inp_crs, dst_crs=out_crs)
        else:
            return self.s2metadata["footprint"]

    def exists(self):
        """Check whether input file exists."""
        return os.path.isfile(self.path)


class InputTile(base.InputTile):
    """Target Tile representation of input data."""

    def __init__(self, tile, safe_file, s2metadata, resampling="nearest"):
        """Initialize."""
        self.tile = tile
        self.safe_file = safe_file
        self.s2metadata = s2metadata
        self.resampling = resampling
        self.dtype = "uint16"
        self._np_band_cache = {}
        self._band_paths_cache = {}

    def read(self, indexes=None):
        """Generate reprojected numpy arrays from input file bands."""
        band_indexes = self._get_band_indexes(indexes)
        if len(band_indexes) == 1:
            return self._bands_from_cache(indexes=band_indexes).next()
        else:
            return ma.masked_array(
                data=np.stack(self._bands_from_cache(indexes=band_indexes)),
                mask=np.stack(
                    self.mask()
                    for band in band_indexes
                    )
                )

    def mask(self):
        """Nondata mask."""
        return self._bands_from_cache(2).next().mask

    def is_empty(self, indexes=None):
        """Return true if all items are masked."""
        band_indexes = self._get_band_indexes(indexes)
        src_bbox = self.safe_file.bbox()
        tile_geom = self.tile.bbox

        # empty if tile does not intersect with file bounding box
        if not tile_geom.intersects(src_bbox):
            return True

        # empty if source band(s) are empty
        all_bands_empty = True
        for band in self._bands_from_cache(band_indexes):
            if not band.mask.all():
                all_bands_empty = False
                break
        return all_bands_empty

    def _get_band_indexes(self, indexes=None):
        """Return valid band indexes."""
        if indexes:
            if isinstance(indexes, list):
                return indexes
            else:
                return [indexes]
        else:
            return range(1, 14)

    def _get_band_paths(self, band_index=None):
        """Cache Sentinel Granule paths."""
        assert isinstance(band_index, int)
        if band_index not in self._band_paths_cache:
            # Group granule band paths by SRID as gdalbuildvrt cannot
            # handle multiple images with different SRID:
            band_paths = {}
            for granule in self.s2metadata["granules"]:
                if granule["srid"] not in band_paths:
                    band_paths[granule["srid"]] = []
                band_paths[granule["srid"]].append(
                    granule["band_path"][band_index])
            self._band_paths_cache[band_index] = band_paths
        return self._band_paths_cache[band_index]

    def _bands_from_cache(self, indexes=None):
        """Cache reprojected source data for multiple usage."""
        band_indexes = self._get_band_indexes(indexes)
        for band_index in band_indexes:
            if band_index not in self._np_band_cache:
                empty_band = ma.masked_array(
                    ma.zeros(self.tile.shape, dtype=self.dtype), mask=True)
                if not len(self._get_band_paths(band_index)):
                    band = empty_band
                else:
                    band = empty_band
                    for granule in self.s2metadata["granules"]:
                        new_data = read_raster_window(
                            granule["band_path"][band_index], self.tile,
                            indexes=1, resampling=self.resampling).next()
                        band = ma.masked_array(
                            data=np.where(band.mask, new_data.data, band.data),
                            mask=np.where(
                                band.mask, new_data.mask, band.mask)
                            )
                self._np_band_cache[band_index] = band
            yield self._np_band_cache[band_index]
