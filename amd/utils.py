# Builtins
import logging
import os
import re
import sys

from pathlib import Path

# External
import earthaccess
import ray

import xarray as xr

from emit_tools   import emit_xarray
from mlky.ext.ray import Config as C


Logger = logging.getLogger('amd/utils')


def initConfig(config, patch, defs, override, printconfig=False, printonly=False, print=print, initray=True):
    """
    Initializes the mlky Config object

    Parameters
    ----------
    mlky.cli options
    """
    C(config, _patch=patch, _defs=defs, _override=override)

    # Print configuration to terminal
    if printconfig or printonly:
        print(f'Config({config!r}, _patch={patch!r}, _defs={defs})')
        print('-'*100)
        print(C.toYaml(comments=None, listStyle='short', header=False))
        print('-'*100)

        if printonly:
            sys.exit()

    if initray:
        ray.init(**C.ray)
        C.initRay()


def initLogging(mode=None):
    """
    Initializes the logging module per the config
    """
    # Logging handlers
    handlers = []

    # Create console handler
    sh = logging.StreamHandler(sys.stdout)

    if (level := C.log.terminal):
        sh.setLevel(level)

    handlers.append(sh)

    if (file := C.log.file):
        file = Path(file)

        if (mode or C.log.mode) == 'write' and file.exists():
            os.remove(C.log.file)

        file.parent.mkdir(parents=True, exist_ok=True)

        # Add the file logging
        fh = logging.FileHandler(file)
        fh.setLevel(C.log.level or logging.DEBUG)

        handlers.append(fh)

    logging.basicConfig(
        level    = C.log.get('level', 'DEBUG'),
        format   = C.log.get('format', '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'),
        datefmt  = C.log.get('format', '%m-%d %H:%M'),
        handlers = handlers,
    )


def getEarthAccessSession():
    """
    """
    try:
        Logger.info('Logging into earthaccess')
        earthaccess.login()
        return earthaccess.get_requests_https_session()
    except:
        Logger.exception('Failed to start a session with earthaccess')

    return False


def download(url, session=None, output='./downloads', overwrite=False, chunk_size=64*2**20):
    """
    Downloads files from a URL

    Parameters
    ----------
    url: str
        URL to download
    output: str, default='./downloads'
        Output directory
    overwrite: bool, default=False
        Overwrite existing files
    """
    gb = 2**30

    if session is None:
        if (session := getEarthAccessSession()) is False:
            return

    output = Path(output)
    output.mkdir(exist_ok=True, parents=True)
    Logger.debug(f'Downloads output: {output}')

    name = url.split('/')[-1]
    file = output / name

    if overwrite or not file.exists():
        Logger.debug(f'Retrieving {url} => {file}')
        try:
            with session.get(url, stream=True) as stream:
                if stream.status_code >= 400:
                    Logger.error(f'Failed to retrieve file (status code {stream.status_code}): {url}')
                else:
                    with open(file, 'wb') as dst:
                        for i, chunk in enumerate(stream.iter_content(chunk_size=chunk_size)):
                            dst.write(chunk)
                            Logger.debug(f'Downloaded {file.stat().st_size / gb:.2f} GB')

        except Exception as e:
            Logger.error(f'Failed to retrieve file: {url}\nReason: {e}')
    else:
        Logger.debug(f'File already exists, skipping: {file}')

    return True


def batchDownload(urls=[], batch=None, **kwargs):
    """
    Performs batch downloading of files per a configuration
    """
    if (session := getEarthAccessSession()) is False:
        return

    if batch:
        Logger.debug(f'Batch download: {batch}')
        for granule in batch.granules:
            for kind, products in batch.products.items():
                base = batch.base[kind]
                urls += [
                    base.format(
                        granule = granule,
                        product = product,
                        type    = kind
                    )
                    for product in products
                ]

    if C.isinstance(urls, list) and urls:
        Logger.debug(f'List download:')
        for url in urls:
            Logger.debug(f'- {url}')
        for url in urls:
            if not download(url, session, **kwargs):
                Logger.error('Failed to download, exiting early')
                return


def load_raster(file, rename={}, bands=[]):
    """
    Loads an EMIT raster file. Auto splits the 'band' dimension into individual
    variables and renames the coordinates, if provided

    Parameters
    ----------
    file: str
        Path to an EMIT rasterized file to load
    rename: dict
        Rename keys before returning
    bands: list
        Exchange the 'band' dim values

    Returns
    -------
    ds: xr.Dataset
        Loaded xarray object
    """
    ds = xr.load_dataset(file, engine='rasterio')

    # Split the band dimension
    if bands:
        ds['band'] = list(bands)
        ds = ds['band_data'].to_dataset('band')

    # Rename dimensions
    if rename:
        ds = ds.rename(**rename)

    return ds


def load_netcdf(file):
    """
    Loads a netcdf file using emit_tools.emit_xarray

    Parameters
    ----------
    file: pathlib.Path
        Path to file to load

    Returns
    -------
    ds: xr.Dataset
        Loaded xarray object
    """
    Logger.info(f'Loading using emit_xarray: {file}')
    ds = emit_xarray(file, ortho=True)

    return ds


def load(file):
    """
    Switches the loading function depending on the input file

    Parameters
    ----------
    file: pathlib.Path
        Path to file to load

    Returns
    -------
    ds: xr.Dataset
        Loaded xarray object
    """
    if (file := Path(file)).suffix == '.nc':
        ds = load_netcdf(file)

        split = re.findall(r'(EMIT_L\d[AB]_[A-Z]+)_(\w+)', file.name)
        if split:
            product, granule = split[0]

            for product in C.input.netcdf.merge:
                product = file.with_stem(f'{product}_{granule}')
                if product.exists():
                    ps = load_netcdf(product)
                else:
                    Logger.error(f'Could not find product: {product}')

                Logger.debug(f'Merging product: {product}')
                ds = xr.merge([ds, ps])
        elif C.input.netcdf.merge:
            Logger.error('Failed to parse EMIT product from input file, cannot load additional products for merging')
    else:
        Logger.info(f'Loading using load_raster: {file}')
        ds = load_raster(file, **C.input.raster)

    return ds
