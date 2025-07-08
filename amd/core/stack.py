import logging
import re
from datetime  import datetime as dtt
from functools import partial
from glob      import glob
from pathlib   import Path

import numpy  as np
import xarray as xr
from mlky import Config

from amd.core.amd import AMD

# Generic AMD object to access its functions
amd = AMD(None)

Logger = logging.getLogger("AMD[Stack]")


def subselect(ds, **sel):
    """
    Subselects along dimensions. Auto discover which way the sel slice should be
    constructed

    Parameters
    ----------
    ds : xr.Dataset, xr.DataArray
        Xarray object to operate on
    **sel : dict
        Dimensions to select on and the values to select between

    Returns
    -------
    xr.Dataset, xr.DataArray
        Subselected xarray object
    """
    sels = {}
    for key, vals in sel.items():
        i, j = sorted(vals)

        # Discover which way to create the slice
        a, b = ds[key][[0, -1]]

        # Increasing
        if a < b:
            sels[key] = slice(i, j)
        # Decreasing
        elif a > b:
            sels[key] = slice(j, i)

    return ds.sel(**sels)


def uniques(data, ignore=[], skipna=False):
    """
    Retrieves the unique values and the count of these values for a given array

    Parameters
    ----------
    data : xr.DataArray
        Object to operate on
    skipna : bool, default=False
        Skips NaN values
    ignore : list, default=[]
        Values to ignore

    Returns
    -------
    values, counts : tuple[np.array]
        Values are the unique values, counts are the corresponding count of the unique
        values
    """
    values, counts = np.unique(data, return_counts=True)

    if skipna and np.isnan(values[-1]):
        values = values[:-1]
        counts = counts[:-1]

    if ignore:
        arrays = [values == i for i in ignore]
        remove = np.bitwise_or.reduce(arrays)
        values = values[~remove]
        counts = counts[~remove]

    return values, counts


def count(x, Nth=0, type='value', mincount=0, **kwargs):
    """
    Retrieves the Nth (zero-indexed) most frequent value in an array

    Parameters
    ----------
    x : np.array
        Object to operate on
    mincount : int, default=0
        The minimum count for a value to be valid
    skipna : bool, default=False
        Skips NaN values
    ignore : list, default=[]
        Values to ignore

    Returns
    -------
    float
        Nth most frequent value or NaN if there isn't one
    """
    assert type in (opts := {'value', 'count'}), f"Type must be one of: {opts}, got: {type}"

    values, counts = uniques(x, **kwargs)

    if len(counts) >= Nth:
        index = np.argsort(counts)[-Nth]

        if counts[index] > mincount:
            if type == 'count':
                return counts[index]
            return values[index]

    return np.nan


def frequency(ds, ignore=[], skipna=False, mincount=0, type='value'):
    """
    Retrieves the Nth highest value count over a 2D array. Expected input shape is
    (product, *location), where *location is one or more dimensions

    If two values tie in their counts, they will be sorted in decreasing order.

    Parameters
    ----------
    ds : xr.Dataset | xr.DataArray
        Object to operate on
    mincount : int, default=0
        The minimum count for a value to be valid
    skipna : bool, default=False
        Skips NaN values
    ignore : list, default=[]
        Values to ignore

    Returns
    -------
    xr.Dataset | xr.DataArray
    """
    # Run this function for each variable in the dataset
    if isinstance(ds, xr.Dataset):
        return xr.Dataset({
            key: frequency(data, ignore, skipna, mincount, type)
            for key, data in ds.items()
        })

    values, counts = uniques(ds, ignore, skipna)

    hold = []
    for i in range(values.size):
        func = partial(count,
            Nth      = i,
            ignore   = ignore,
            skipna   = skipna,
            mincount = mincount,
            type     = type
        )
        hold.append(
            xr.apply_ufunc(func, ds, input_core_dims=[['product']], vectorize=True)
        )

    if hold:
        return xr.concat(hold, dim='freq')


def parseDate(file):
    """
    Parses the date string from an AMD file

    Parameters
    ----------
    file : str
        File path to parse

    Returns
    -------
    str
        Parsed date string
    """
    return file.split('/')[-1].split('_')[1]


def to_datetime(emit):
    """
    Parses an emit file name into a datetime object

    Parameters
    ----------
    emit : str
        Filename of an EMIT product

    Returns
    -------
    datetime.datetime
        Parsed datetime object
    """
    ts = emit.split('/')[-1].split('_')[0][4:]
    split = re.findall(r"(\d\d\d\d)(\d\d)(\d\d)t(\d\d)(\d\d)(\d\d)", ts)[0]
    split = [int(part) for part in split]

    return dtt(*split)


def build(files, **sel):
    """
    Builds a temporal product

    Parameters
    ----------
    files : list
        List of files in order to load
    **sel : dict
        Dimensions to subselect with

    Returns
    -------
    xr.Dataset
    """
    merge = []
    for file in files:
        ds = xr.open_dataset(file)
        ds = subselect(ds, **sel)
        merge.append(ds)

    return xr.concat(merge, dim='product', join='override', compat='override', coords='all')


def stack(files):
    """
    Stacks products together

    Parameters
    ----------
    files : list[str]
        List of files to load

    Returns
    -------
    info, colors, count : xr.Dataset, xr.Dataset, xr.Dataset
    """
    # Load the files along a new dimension
    ds = xr.open_mfdataset(files, concat_dim="product", combine="nested")
    ds.load()

    # Extract useful information
    info = ds.count("product")
    info["products"] = ds.product.size
    try:
        info["dates"] = [to_datetime(file) for file in files]
    except:
        pass

    # Get the frequency dataset
    freqs = frequency(ds, type='value', **Config.stack)
    count = frequency(ds, type='count', **Config.stack)

    # Colorize it
    colors = amd.colorize(freqs, Config.colors)

    return info, colors, count


def main():
    """
    Reads the output directory of an AMD run and stacks the classified groups
    """
    for group in Config.classify:
        Logger.info(f"Processing {group}")
        files = glob(f"{Config.output.dir}/**/*{group}.tiff")

        Logger.debug(f"{len(files)} files: {files}")
        info, colors, counts = stack(files)

        # Save out
        info.to_netcdf(f"{Config.output.dir}/{group}.freq-info.nc")

        for var, vs in colors.items():
            for freq, fs in vs.groupby("freq"):
                amd.name = f"{group}.freq-{freq}.colors"
                amd.save(fs.squeeze(), dir=Config.output.dir, subdir=False, netcdf=False, geotiff=True)

        for var, vs in counts.items():
            for freq, fs in vs.groupby("freq"):
                amd.name = f"{group}.freq-{freq}.counts"
                amd.save(fs.squeeze(), dir=Config.output.dir, subdir=False, netcdf=False, geotiff=True)

    Logger.info("Finished")
