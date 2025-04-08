import logging
import re
from datetime import datetime as dtt
from glob import glob
from pathlib import Path

import numpy as np
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


def nCount(ds, mincount=0, skipna=False):
    """
    Retrieves the Nth highest value count over a 2D array. Expected input shape is
    (product, *location), where *location is one or more dimensions

    If two values tie in their counts, they will be sorted in decreasing order.

    Parameters
    ----------
    ds : xr.DataArray
        Object to operate on
    mincount : int, default=0
        The minimum count for a value to be valid
    skipna : bool, default=False

    Returns
    -------
    xr.DataArray
    """
    def count(x):
        nonlocal uniques

        values, counts = np.unique(x, return_counts=True)

        if skipna and np.isnan(values[-1]):
            values = values[:-1]
            counts = counts[:-1]

        uniques = max(len(counts), uniques)

        if len(counts) >= n:
            index = np.argsort(counts)[-n]

            if counts[index] > mincount:
                return values[index]

        return np.nan

    uniques = 2
    n = 1

    hold = []
    while n < uniques:
        hold.append(xr.apply_ufunc(count, ds, input_core_dims=[['product']], vectorize=True))
        n += 1

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
    info, colors : xr.Dataset, xr.Dataset
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
    ds = nCount(ds)

    # Colorize it
    colors = amd.colorize(ds, Config.colors)

    return info, colors


def main():
    """
    Reads the output directory of an AMD run and stacks the classified groups
    """
    for group in Config.classify:
        Logger.info(f"Processing {group}")
        files = glob(f"{Config.output.dir}/**/*{group}.tiff")
        info, colors = stack(files)

        # Save out
        info.to_netcdf(f"{Config.output.dir}/{group}.freq-info.nc")
        for var, vs in colors.items():
            for freq, fs in vs.groupby("freq"):
                amd.name = f"{group}.freq-{freq}.colors"
                amd.save(fs, dir=Config.output.dir, subdir=False, netcdf=False, geotiff=True)

    Logger.info("Finished")
