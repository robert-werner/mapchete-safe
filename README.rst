====================
Mapchete SAFE plugin
====================

A Sentinel-2 SAFE archive data reader plugin for Mapchete.

-------
Example
-------

Use the files from the example folder and download a Sentinel-2 product SAFE file. The example process takes the red, green and blue bands, enhances the colors and saves the output as a tile pyramid using PNG files.

.. code-block:: shell

    # install rio-color before
    pip install rio-color

    # host an OpenLayers instance at localhost:5000 to view the output (zoom 8 or higher)
    mapchete serve rgb.mapchete --memory --input_file S2A_MSIL1C_20170421T100031_N0204_R122_T33TUL_20170421T100541.SAFE.zip

    # create a tile pyramid for zooms 8 to 14 in output/ directory:
    mapchete execute rgb.mapchete -z 8 14 --input_file S2A_MSIL1C_20170421T100031_N0204_R122_T33TUL_20170421T100541.SAFE.zip


Try out editing the process parameters in ``rgb.mapchete`` to inspect their behaviour or the python code in ``example_process.py``. You can do this while ``mapchete serve`` is running, it will automatically reload.

-----
Usage
-----

Simply provide the path to the SAFE directory or SAFE.zip file as ``input`` in a mapchete process configuration to read Sentinel-2 data.

The ``read()`` function has the following flags:

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

------------
Installation
------------

Dependencies
------------

Make sure GDAL and OpenJPEG are installed. It is advised to use OpenJPEG 2.2.0 or higher to efficiently read JPEG2000 files. Also, rasterio has to be rebuilt to ensure it uses OpenJPEG instead of the standard JasPer driver:

.. code-block:: shell

    # e.g. install rasterio version 1.0a9:
    pip install --no-binary :all: rasterio==1.0a9


Driver
------

The driver is available via ``pip``:

.. code-block:: shell

    pip install mapchete-safe


Or clone the repository and run:

.. code-block:: shell

    pip install -r requirements.txt
    python setup.py install


Tests
-----

Run tests from the repository's root directory:

.. code-block:: shell

    python setup.py test



-------
License
-------

MIT License

Copyright (c) 2015, 2016, 2017 `EOX IT Services`_

.. _`EOX IT Services`: https://eox.at/
