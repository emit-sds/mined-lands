# Builtins
import logging

from datetime import datetime as dtt
from pathlib  import Path

# External
import click
import numpy  as np
import xarray as xr

from emit_tools import emit_xarray
from mlky       import Config as C

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


def save(da, base, name=None):
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
    out = Path(C.output.dir)
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


def main(ret='yield'):
    """
    Main processing function for classifying an EMIT scene into a mineral map

    Yields
    ------
    ret: str, options=[], default='yield'
        If 'yield', converts the function into a generator that will yield each classified
        xr.DataArray
        If 'merge', merges the classified DataArrays back into a Dataset for return
        If anything else, simply deletes the DataArray from memory

    """
    # Load the data
    file = Path(C.file)
    ds = emit_xarray(file, ortho=True)

    if C.subselect:
        ds = subselect(ds)

    Logger.info(f'Working shape: {ds.sizes}')

    # Create a hashmap from the Config dict
    hashmap = {val: key for key, vals in C.hashmap.items() for val in vals}

    if not hashmap:
        Logger.error('No hashmap defined, returning')
        return

    hold = []
    for key, opts in C.classify.items():
        Logger.info(f'Processing on key: {key}')

        if opts.filter:
            Logger.info(f'Using filter: {opts.filter}')
            opts.filter = condition(ds, opts.filter)

        cs = classify(ds[key], hashmap=hashmap, **opts)

        if C.output.dir:
            save(cs, file.stem)

        if ret == 'yield':
            yield cs
        elif ret == 'merge':
            hold.append(cs)
        else:
            del cs

    if hold:
        Logger.info('Merging arrays together')
        ds = xr.merge(hold)
        if C.output.dir:
            save(ds, file.stem, name='merged')


@click.command()
@click.option("-c", "--config", required=True, help="Configuration YAML")
@click.option("-p", "--patch", help="Sections to patch with")
@click.option("--print", help="Prints the configuration to terminal", is_flag=True)
def cli(config, patch, print):
    """\
    Executes the main processes
    """
    # Initialize the global configuration object
    C(config, patch)

    utils.initLogging()

    if print:
        click.echo(C.dumpYaml(comments=None))

    if C.validate():
        start = dtt.now()
        try:
            ret = 'merge' if C.output.merge else None
            for _ in main(ret):
                pass
        except:
            Logger.exception(f'Caught a critical exception')
        finally:
            Logger.info(f'Finished in {dtt.now() - start}')
    else:
        click.echo("Please correct any configuration errors before proceeding")


if __name__ == '__main__':
    cli()
