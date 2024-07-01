# Builtins
import glob
import logging

from datetime import datetime as dtt
from pathlib  import Path

# External
import numpy  as np
import ray
import xarray as xr

from emit_tools import emit_xarray
from mlky       import Config as C
from mlky.utils import Track

# Internal
from amd import utils


Logger = logging.getLogger('amd/minerals')


def classify(ds, hashmap, filter=None, default=np.nan):
    """
    Classifies each value in a 2D xarray object to a value defined by a hashmap.

    Parameters
    ----------
    ds: xr.Dataset, xr.DataArray
        2D xarray object to operate on
    hashmap: dict
        Hashmap lookup such that values in ds are keys in the dict mapped to some value
        to replace with
    filter: xr.DataArray, default=None
        Condition to filter. True is where to keep values, False are replaced with the
        default
    default: int, float, default=np.nan
        Default value to replace with if a value is not present in the hashmap

    Returns
    -------
    ds: xr.Dataset, xr.DataArray
        Mapped xarray object
    """
    func = np.vectorize(lambda x: hashmap.get(x, default))

    ds = xr.apply_ufunc(func, ds)

    if filter is not None:
        ds = ds.where(filter, default)

    return ds


def colorize(ds, colors):
    """
    Converts an xarray object into a 4 band RGBA mapping of values to color values

    Parameters
    ----------
    ds: xr.Dataset, xr.DataArray
        Xarray object to map the values of to a color map
    colors: dict
        Mapping of {value: [R, G, B, A]} to convert values to

    Returns
    -------
    cs: xr.Dataset, xr.DataArray
        Xarray object with a new dimension 'band' for RGBA
    """
    bands = []
    rgba  = ['R', 'G', 'B', 'A']
    for i, band in enumerate(rgba):
        hashmap = {float(group): float(color[i]) for group, color in colors.items()}
        bands.append(classify(ds, hashmap))

    # [C]olored [S]et
    cs = xr.concat(bands, dim='band').astype(np.uint8)
    cs['band'] = rgba

    return cs


def subselect(ds):
    """
    Subselects along dimensions. Auto discover which way the sel slice should be constructed

    Parameters
    ----------
    ds: xr.Dataset, xr.DataArray
        Xarray object to operate on

    Returns
    -------
    xr.Dataset, xr.DataArray
        Subselected xarray object
    """
    sel = {}
    for key, vals in C.subselect.items():
        i, j = sorted(vals)

        # Discover which way to create the slice
        a, b = ds[key][[0, -1]]

        # Increasing
        if a < b:
            sel[key] = slice(i, j)
        # Decreasing
        elif a > b:
            sel[key] = slice(j, i)

    Logger.info(f'Subselecting using: {sel}')
    return ds.sel(**sel)


def condition(ds, string):
    """
    Converts a string from the config to a condition. Must be formatted as:
        "key op value"
    Where:
        key   = key in the Dataset to operate on
        op    = Conditional operator: >, <, >=, <=
        value = Value to cast to float

    Parameters
    ----------
    ds: xr.Dataset
        Dataset object to apply a condition function on
    string: str
        Conditional string

    Returns
    -------
    xr.DataArray
        Boolean DataArray object
    """
    match string.split(' '):
        case key, '>', val:
            return ds[key] > float(val)
        case key, '<', val:
            return ds[key] < float(val)
        case key, '>=', val:
            return ds[key] >= float(val)
        case key, '<=', val:
            return ds[key] <= float(val)


def save(C, da, base, name=None):
    """
    Saves a DataArray to netcdf and geotiff formats per the config

    Parameters
    ----------
    da: xr.DataArray
        Xarray object to save
    base: str
        Base name of the file
    name: str, default=None
        Name to append for this file. If None, uses da.name instead
    """
    out = Path(C.output.dir) / base
    out.mkdir(parents=True, exist_ok=True)

    out /= f'{base}_{name or da.name}'

    if C.output.netcdf:
        da.to_netcdf(f'{out}.nc')

        Logger.info(f'Wrote netcdf to: {out}.nc')

    if (c := C.output.geotiff):
        if c.crs:
            da = da.rio.write_crs(c.crs)
        da.rio.to_raster(f'{out}.tiff')

        Logger.info(f'Wrote geotiff to: {out}.tiff')


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

@ray.remote
def process(file=None):
    """
    Main processing function for classifying an EMIT scene into a mineral map

    Returns
    -------
    file : str, default=None
        File to process. If None, refers to Config.input.file
    """
    # Each ray process must reinitialize the logger
    utils.initLogging(mode='append')

    # Load the data
    file = Path(file or C.input.file)
    if file.suffix == '.nc':
        Logger.info(f'Loading using emit_xarray: {file}')
        ds = emit_xarray(file, ortho=True)
    else:
        Logger.info(f'Loading using load_raster: {file}')
        ds = load_raster(file, rename=C.input.rename, bands=C.input.bands)

    if C.subselect:
        ds = subselect(ds)

    Logger.info(f'Working shape: {ds.sizes}')

    # Create a hashmap from the Config dict
    hashmap = {float(val): float(key) for key, vals in C.hashmap.items() for val in vals}

    if not hashmap:
        Logger.error('No hashmap defined, returning')
        return

    merge = {'classify': [], 'colors': []}
    for key, opts in C.classify.items():
        Logger.info(f'Processing on key: {key}')

        filter = None
        if opts.filter:
            Logger.info(f'Using filter: {opts.filter}')
            filter = condition(ds, opts.filter)

        cs = classify(ds[key],
            hashmap = hashmap,
            filter  = filter,
            default = opts.get('default', np.nan)
        )

        if C.output.dir:
            if C.colors:
                Logger.info('Colorizing')
                ns = colorize(cs, C.colors)

                save(C, ns, base=file.stem, name=f'{key}-color')
                merge['colors'].append(ns)

            save(C, cs, base=file.stem)

        if C.output.merge:
            merge['classify'].append(cs)
        else:
            del cs

    if merge['classify']:
        Logger.info('Merging arrays together')

        ds = xr.merge(merge['classify'])
        if C.output.dir:
            save(C, ds, base=file.stem, name='merged')

        if merge['colors']:
            ds = xr.merge(merge['colors'])
            try:
                save(C, ds, base=file.stem, name='merged-color')
            except:
                # tiff saving merged colors is not supported, exception expected
                pass


def main():
    """\
    Executes the main processes
    """
    start = dtt.now()
    try:
        if C.download.urls:
            Logger.info(f'Downloading files')
            utils.download(**C.download)

        # If the file was a glob, process each input file separately
        if glob.has_magic(C.input.file):
            files = glob.glob(C.input.file)

            Logger.info(f'Glob pattern provided, retrieved {len(files)} files using: {C.input.file}')

            jobs   = [process.remote(file) for file in files if not file.endswith('.hdr')]
            report = Track(jobs, step=1, reverse=True, print=Logger.info, message="Files processed")
            while jobs:
                [done], jobs = ray.wait(jobs, num_returns=1)
                ray.get(done)
                report(jobs)
        else:
            ray.get(process.remote())
    except:
        Logger.exception(f'Caught a critical exception')
    finally:
        Logger.info(f'Finished in {dtt.now() - start}')


if __name__ == '__main__':
    Logger.error('Calling this script directly has been deprecated, please use the AMD CLI')
