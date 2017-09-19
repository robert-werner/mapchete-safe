"""Read bands from Seninel-2 SAFE archives."""

import os
import s2reader
import numpy as np
import numpy.ma as ma
from rasterio.crs import CRS
from s2reader.s2reader import BAND_IDS

from mapchete.formats import base
from mapchete.io.vector import reproject_geometry
from mapchete.io.raster import read_raster_window


METADATA = {
    "driver_name": "SAFE",
    "data_type": "raster",
    "mode": "r",
    "file_extensions": ["SAFE", "zip", "ZIP"]
}


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
        self.path = input_params["path"]
        self.pyramid = input_params["pyramid"]
        self.pixelbuffer = input_params["pixelbuffer"]
        self.crs = self.pyramid.crs
        self.srid = self.pyramid.srid
        with s2reader.open(self.path) as s2dataset:
            self.s2metadata = {
                "path": s2dataset.path,
                "footprint": s2dataset.footprint,
                "granules": [
                    {
                        "srid": granule.srid,
                        "footprint": granule.footprint,
                        "band_path": {
                            index: granule.band_path(
                                _id, for_gdal=True, absolute=True
                            )
                            for index, _id in zip(range(1, 14), BAND_IDS)
                        }
                    }
                    for granule in s2dataset.granules
                ]
            }

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
                mask=np.stack(self.mask() for band in band_indexes)
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
        for band in self._bands_from_cache(band_indexes):
            if not band.mask.all():
                return False
        return True

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
        if band_index not in self._band_paths_cache:
            # group granule band paths by SRID
            band_paths = {}
            for granule in self.s2metadata["granules"]:
                if granule["srid"] not in band_paths:
                    band_paths[granule["srid"]] = []
                band_paths[granule["srid"]].append(
                    granule["band_path"][band_index]
                )
            self._band_paths_cache[band_index] = band_paths
        return self._band_paths_cache[band_index]

    def _bands_from_cache(self, indexes=None):
        """Cache reprojected source data for multiple usage."""
        band_indexes = self._get_band_indexes(indexes)
        for band_index in band_indexes:
            if band_index not in self._np_band_cache:
                # flatten all granules on one output array
                band = ma.masked_array(
                    ma.zeros(self.tile.shape, dtype=self.dtype), mask=True
                )
                if len(self._get_band_paths(band_index)):
                    for granule in self.s2metadata["granules"]:
                        new_data = read_raster_window(
                            granule["band_path"][band_index], self.tile,
                            indexes=1, resampling=self.resampling).next()
                        if new_data.all() is ma.masked:
                            continue
                        band = ma.masked_array(
                            data=np.where(band.mask, new_data.data, band.data),
                            mask=np.where(
                                band.mask, new_data.mask, band.mask)
                            )
                self._np_band_cache[band_index] = band
            yield self._np_band_cache[band_index]
