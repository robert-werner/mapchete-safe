"""Read bands from Seninel-2 SAFE archives."""

import os
import s2reader
import numpy as np
import numpy.ma as ma
from operator import mul, add
from functools import reduce
from cached_property import cached_property
from rasterio.crs import CRS
from rasterio.features import geometry_mask
from s2reader.s2reader import BAND_IDS

from mapchete.formats import base
from mapchete.io.vector import reproject_geometry
from mapchete.io.raster import read_raster_window
from mapchete.errors import MapcheteEmptyInputTile


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
                        "id": granule.granule_identifier,
                        "srid": granule.srid,
                        "footprint": reproject_geometry(
                            granule.footprint,
                            src_crs=CRS.from_epsg(4326),
                            dst_crs=self.crs
                        ),
                        "nodatamask": granule.nodata_mask,
                        "cloudmask": granule.cloudmask,
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

    @cached_property
    def cloudmask(self):
        """SAFE file cloud mask as iterable list of geometries."""
        return [
            reproject_geometry(
                granule["cloudmask"],
                src_crs=CRS.from_epsg(4326),
                dst_crs=self.crs
            )
            for granule in self.s2metadata["granules"]
        ]

    @cached_property
    def nodatamask(self):
        """SAFE file nodata mask as iterable list of geometries."""
        return [
            reproject_geometry(
                granule["nodatamask"],
                src_crs=CRS.from_epsg(4326),
                dst_crs=self.crs
            )
            for granule in self.s2metadata["granules"]
        ]

    def open(self, tile, **kwargs):
        """Return InputTile."""
        return InputTile(
            tile, self, self.s2metadata, self.cloudmask, self.nodatamask,
            **kwargs
        )

    def bbox(self, out_crs=None):
        """Return data bounding box."""
        out_crs = self.pyramid.crs if out_crs is None else out_crs
        inp_crs = CRS().from_epsg(4326)
        if inp_crs != out_crs:
            return reproject_geometry(
                self.s2metadata["footprint"], src_crs=inp_crs, dst_crs=out_crs
            )
        else:
            return self.s2metadata["footprint"]

    def exists(self):
        """Check whether input file exists."""
        return os.path.isfile(self.path)


class InputTile(base.InputTile):
    """Target Tile representation of input data."""

    def __init__(
        self, tile, safe_file, s2metadata, cloudmask, nodatamask,
        resampling="nearest"
    ):
        """Initialize."""
        self.tile = tile
        self.safe_file = safe_file
        self.s2metadata = s2metadata
        self.cloudmask = cloudmask
        self.nodatamask = nodatamask
        self.resampling = resampling
        self.dtype = "uint16"

    def _empty(self, height):
        return ma.masked_array(np.zeros(height + (self.tile.shape, )), True)

    def read(
        self,
        indexes=None,
        resampling=None,
        mask_nodata=True,
        mask_clouds=False,
        mask_white_areas=False,
        return_empty=False
    ):
        """
        Read reprojected & resampled input data.

        Parameters
        ----------
        indexes : integer or list
            band number or list of band numbers
        resampling : str
            resampling method
        mask_nodata : bool
            mask out nodata (values in all bands equal 0) areas (default: True)
        mask_clouds : bool
            mask out clouds (default: False)
        mask_white_areas : bool
            mask out white (values over 4096) areas; might just work on RGB
            bands! (default: False)
        return_empty : bool
            returns empty array if True or raise MapcheteEmptyInputTile
            exception if False (default: False)

        Returns
        -------
        data : NumPy array or raise MapcheteEmptyInputTile exception
            Band data
        """
        resampling = resampling if resampling is not None else self.resampling
        band_indexes = self._get_band_indexes(indexes)

        # return immediately if tile does not intersect with input data
        if self.is_empty():
            if return_empty:
                return self._empty(len(band_indexes))
            else:
                raise MapcheteEmptyInputTile

        # iterate through affected granules
        granules = [
            granule
            for granule in self.s2metadata["granules"]
            if granule["footprint"].intersects(self.tile.bbox)
        ]

        # read bands from granules
        bands = []
        for band_index in band_indexes:
            band = ma.masked_array(
                ma.zeros(self.tile.shape, dtype=self.dtype), mask=True
            )
            for granule in granules:
                new_data = read_raster_window(
                    granule["band_path"][band_index],
                    self.tile,
                    indexes=1,
                    resampling=self.resampling
                ).next()
                if new_data.mask.all():
                    continue
                band = ma.masked_array(
                    data=np.where(band.mask, new_data.data, band.data),
                    mask=np.where(band.mask, new_data.mask, band.mask)
                )
                bands.append(band)

        # get combined mask
        mask = self._mask(bands, mask_nodata, mask_white_areas, mask_clouds)

        # skip if emtpy
        if mask.all():
            if return_empty:
                return self._empty(len(band_indexes))
            else:
                raise MapcheteEmptyInputTile()
        else:
            nd_mask = np.stack([mask for _ in band_indexes])
            return ma.masked_array(
                data=np.where(nd_mask, 0, np.stack(bands)),
                mask=nd_mask
            )

    def is_empty(self, indexes=None):
        """Quick check if tile is empty."""
        return not self.tile.bbox.intersects(self.safe_file.bbox())

    def _mask(
        self, bands, mask_nodata=None, mask_white_areas=None, mask_clouds=None
    ):
        # if mask_nodata: combine masks of all bands
        # TODO: use original vector mask for nodata values
        # nodata_mask = (
        #     geometry_mask(
        #         self.nodatamask,
        #         self.tile.shape,
        #         self.tile.affine,
        #         invert=True  # WTF
        #     )
        #     if mask_nodata and self.nodatamask else None
        # )
        nodata_mask = (
            reduce(add, [np.where(b.mask, True, False) for b in bands])
            if mask_nodata else None
        )
        # mask out white areas (= where all band values are >=4096)
        white_mask = (
            reduce(mul, [np.where(b >= 4096, True, False) for b in bands])
            if mask_white_areas else None
        )
        # rasterize cloud mask
        cloud_mask = (
            geometry_mask(
                self.cloudmask,
                self.tile.shape,
                self.tile.affine,
                invert=True  # WTF
            )
            if mask_clouds and self.cloudmask else None
        )
        # combine all masks
        masks = (nodata_mask, cloud_mask, white_mask)
        if any([m is not None for m in masks]):
            return reduce(add, [x for x in masks if x is not None])
        else:
            return np.zeros(self.tile.shape)

    def _get_band_indexes(self, indexes=None):
        """Return valid band indexes."""
        if indexes:
            if isinstance(indexes, list):
                return indexes
            else:
                return [indexes]
        else:
            return range(1, 14)
