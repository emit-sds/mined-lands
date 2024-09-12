import logging

from pathlib import Path

import numpy as np
import ray
import xarray as xr

from mlky import (
    Config,
    Sect
)
from mlky.utils import Track

from amd.loaders import (
    Granule,
    Raster
)


Logger = logging.getLogger('AMD')


class AMD:
    products = None

    def __init__(self, loader):
        """
        Parameters
        ----------
        loader : amd.loaders
            A supported data loader
        """
        self.data = loader

        # Retrieve an identifier for this product
        if hasattr(loader, 'granule'):
            self.name = loader.granule
            self.log  = logging.getLogger(f'AMD[Granule={self.name}]')
        elif hasattr(loader, 'raster'):
            self.name = loader.raster
            self.log  = logging.getLogger(f'AMD[Raster={self.name}]')

    def classify(self, ds, hashmap, mask=None, default=np.nan, **kwargs):
        """
        Classifies each value in a 2D xarray object to a value defined by a hashmap.

        Parameters
        ----------
        var : str
            Variable to classify
        default : int, float, default=np.nan
            Default value to replace with if a value is not present in the hashmap

        Returns
        -------
        data : xr.Dataset, xr.DataArray
            Mapped xarray object
        """
        func = np.vectorize(lambda x: hashmap.get(x, default))

        if isinstance(ds, str):
            ds = self.data.load(ds)

        data = xr.apply_ufunc(func, ds)

        if mask is not None:
            data = data.where(mask, default)

        return data

    def colorize(self, ds, colors):
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
            bands.append(self.classify(ds, hashmap))

        # [C]olored [S]et
        cs = xr.concat(bands, dim='band').astype(np.uint8)
        cs['band'] = rgba

        return cs

    def createFilter(self, *args, **kwargs):
        """
        Calls the data loader's createFilter, if it has one

        Parameters
        ----------
        *args : list
            Passthrough to self.data.createFilter
        *kwargs : dict
            Passthrough to self.data.createFilter
        """
        if hasattr(self.data, 'createFilter'):
            return self.data.createFilter(*args, **kwargs)

    def save(self, ds, dir='.', subdir=True, subname=None, netcdf=True, geotiff=False, crs='epsg:4326'):
        """
        Saves out an xr.Dataset

        Parameters
        ----------
        ds : xr.Dataset, xr.DataArray
            Product produced by the process function
        dir : str, default='.'
            Directory to save the dataset to
        subdir : bool, default=True
            Create a subdirectory in the output directory with the name of the
            processed product
        """
        if not any([netcdf, geotiff]):
            self.log.warning('Neither netcdf nor geotiff were enabled, nothing to save out')
            return

        path = Path(dir)
        if subdir:
            path /= self.name

        path.mkdir(exist_ok=True, parents=True)

        if subname:
            name = f'{self.name}-{subname}'

        if netcdf:
            file = path / f'{name}.nc'
            ds.to_netcdf(file)

            self.log.info(f'Wrote netcdf to: {file}')

        if geotiff:
            file = path / f'{name}.tiff'

            if crs:
                ds = ds.rio.write_crs(crs)

            ds.rio.to_raster(path)

            self.log.info(f'Wrote geotiff to: {file}')

    def process(self, hashmap, classify, colorize=None, merge=False, save=True, **kwargs):
        """
        TODO

        Parameters
        ----------
        classify : dict
            Variables to process through the classify algorithm in the form of
            {variable: filters}
        colorize : dict, default=None
            Colorize processed variables
        merge : bool, default=False
            Merge processed variables together
        save : bool, default=True
            Save processed variables
        kwargs : dict
            Output parameters passed directly to the `save` function

        Returns
        -------
        ...
        """
        # Reset products
        self.prods  = {}
        self.colors = {}

        for var, opts in classify.items():
            self.log.info(f'Classifying {var}')
            self.createFilter(opts.filter)
            self.prods[var] = self.classify(var, hashmap, self.data.mask, **opts)

        if colorize:
            for var, prod in self.prods.items():
                self.log.info(f'Colorizing {var}')
                self.colors[var] = self.colorize(prod, colorize)

        if merge:
            self.log.info(f'Merging products')
            self.products = {
                'classified': xr.merge(self.prods.values()),
                'colorized': xr.merge(self.colors.values())
            }
        else:
            self.products = {
                'classified': self.prods,
                'colorized': self.colors
            }

        if save:
            self.log.info(f'Saving products')
            for var, prod in self.prods.items():
                try:
                    self.save(prod, subname=var, **kwargs)
                except:
                    self.log.exception(f'Failed to save {var}')
            for var, prod in self.colors.items():
                try:
                    self.save(prod, subname=f'{var}-colors', **kwargs)
                except:
                    self.log.exception(f'Failed to save {var}-colors')

        return self.products

    @staticmethod
    def makeHashmap(dict):
        """
        Converts a dict to a hashmap. The keys and values will be auto-converted to
        floats.

        Parameters
        ----------
        dict : dict
            Dictionary to convert of the form {float: [float, ...]}

        Returns
        -------
        dict
            Hashmap of {float: float}
        """
        return {float(val): float(key) for key, vals in dict.items() for val in vals}


def process():
    """
    Batch executes AMD.process in parallel using a mlky config
    """
    if True not in (Config.output.netcdf, Config.output.geotiff):
        Logger.warning('Neither output file types (netcdf, geotiff) are enabled, nothing will be saved')
    if not Config.output.save:
        Logger.warning('Config.output.save is disabled, nothing will be saved')

    Logger.info('Setting up jobs')

    # Setup job parameters
    opts = Sect(
        hashmap  = AMD.makeHashmap(Config.hashmap),
        classify = Config.classify,
        colorize = Config.colors
    ) | Config.output

    # Place into ray shared memory
    opts = {key: ray.put(val) for key, val in opts.items()}

    # Create the jobs
    worker = ray.remote(num_cpus=1)(AMD)
    actors = []
    kinds  = {
        Granule: Config.input.granules,
        Raster: Config.input.rasters
    }
    for obj, flags in kinds.items():
        Logger.debug(f'Creating jobs for {obj}, flags:\n{flags.toYaml(print=Logger.debug)}')

        products = flags.pop('products')
        if isinstance(products, str):
            Logger.info(f'Using glob to discover products: {flags.dir / products}')
            products = [path.stem for path in flags.dir.glob(products)]

        for item in products:
            Logger.debug(f'Item: {item}')
            actor = worker.remote(obj(item, **flags))
            actors.append(actor)

    jobs = [actor.process.remote(**opts) for actor in actors]

    Logger.info(f'Beginning processing of {len(jobs)} jobs')

    # Execute
    report = Track(jobs, step=1, reverse=True, print=Logger.info, message="Jobs processed")
    while jobs:
        [done], jobs = ray.wait(jobs, num_returns=1)
        ray.get(done)
        report(jobs)

    Logger.info('Finished')


if __name__ == '__main__':
    Logger.error('Calling this script directly is not supported, please use the AMD CLI')
