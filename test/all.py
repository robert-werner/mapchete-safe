#!/usr/bin/env python
"""Test SAFE read driver."""

import os
import sys
import yaml
import shutil
import argparse
from multiprocessing import Pool
from functools import partial
from mapchete import Mapchete
from mapchete.config import MapcheteConfig
from mapchete.formats import available_input_formats, load_input_reader


def main(args):
    """Run all tests."""
    assert "SAFE" in available_input_formats()

    parser = argparse.ArgumentParser()
    parser.add_argument("safe_file", type=str)
    parsed = parser.parse_args(args[1:])
    safe_file = parsed.safe_file

    scriptdir = os.path.dirname(os.path.realpath(__file__))
    mapchete_file = os.path.join(scriptdir, "testdata/s2_read.mapchete")

    with open(mapchete_file, "r") as config_file:
        params = yaml.load(config_file.read())
        params["input_files"].update(file1=safe_file)
        params.update(config_dir=scriptdir+"/testdata")

    config = MapcheteConfig(params)
    process = Mapchete(config)
    out_dir = os.path.join(scriptdir, "testdata/tmp")

    maxtiles = 5
    current = 0
    for tile in process.get_process_tiles(12):
        output = process.execute(tile)
        process.write(output)
        current += 1
        if current == maxtiles:
            break
    print "OK: read/write"

    f = partial(worker, process, overwrite=True)
    current = 0
    work_tiles = []
    for tile in process.get_process_tiles(12):
        work_tiles.append(tile)
        current += 1
        if current == maxtiles:
            break
    try:
        pool = Pool()
        try:
            for raw_output in pool.imap_unordered(
                f, work_tiles):
                process.write(raw_output)
                print raw_output.id, "processed"
        except KeyboardInterrupt:
            pool.terminate()
        except:
            raise
        finally:
            pool.close()
            pool.join()
        print "OK: multiprocessing"
    except:
        print "FAILED: multiprocessing"
    finally:
        try:
            shutil.rmtree(out_dir)
        except:
            pass


def worker(process, process_tile, overwrite):
    """Worker processing a tile."""
    return process.execute(process_tile, overwrite)

if __name__ == "__main__":
    main(sys.argv)
