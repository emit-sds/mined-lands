import logging

from pathlib import Path

import numpy as np
import xarray as xr


Logger = logging.getLogger('AMD')


class AMD:
    products = None

    def __init__(self, loader, name=None):
        """
        Parameters
        ----------
        loader : amd.loaders
            A supported data loader
        name : str, default=None
            Optional alternative name to use
        """
        self.data = loader

        # Retrieve an identifier for this product
        if hasattr(loader, 'granule'):
            self.name = name or loader.granule
            self.log  = logging.getLogger(f'AMD[Granule={self.name}]')
        elif hasattr(loader, 'raster'):
            self.name = name or loader.raster
            self.log  = logging.getLogger(f'AMD[Raster={self.name}]')
        else:
            self.name = name or str(loader)
            self.log  = logging.getLogger(f'AMD[Generic={self.name}]')

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.name})>"

    def classify(self, ds, hashmap, mask=None, mask_class=0, default=0):
        """
        Classifies each value in a 2D xarray object to a value defined by a hashmap.

        Parameters
        ----------
        var : str
            Variable to classify
        mask_class : int, float, default=0
            Value to replace when using the mask
        default : int, float, default=0
            Default value to replace with if a value is not present in the hashmap

        Returns
        -------
        data : xr.Dataset, xr.DataArray
            Mapped xarray object
        """
        self.log.debug(f"Non-class values will default to {default}")
        func = np.vectorize(lambda x: hashmap.get(x, default))

        # File path given, load it
        if isinstance(ds, str):
            ds = self.data.load(ds)

        data = xr.apply_ufunc(func, ds)

        if mask is not None:
            self.log.debug(f"Replacing mask with {mask_class}")

            # ~mask because we want to set where the mask didn't apply as mask_class
            data = data.where(~mask, mask_class)

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

    def createMask(self, *args, **kwargs):
        """
        Calls the data loader's createMask, if it has one

        Parameters
        ----------
        *args : list
            Passthrough to self.data.createMask
        *kwargs : dict
            Passthrough to self.data.createMask
        """
        if hasattr(self.data, 'createMask'):
            return self.data.createMask(*args, **kwargs)

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
        subname : str, default=None
            Appends a subname to the product name, ie. f"{self.name}-{subname}"
        netcdf : bool, default=True
            Write out as a NetCDF4 file
        geotiff : bool, default=False
            Write out as a GeoTIFF file
        crs : str, default='epsg:4326'
            The CRS to use for GeoTIFF output
        """
        if not any([netcdf, geotiff]):
            self.log.warning('Neither netcdf nor geotiff were enabled, nothing to save out')
            return

        path = Path(dir)
        if subdir:
            path /= self.name

        path.mkdir(exist_ok=True, parents=True)

        name = self.name
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

            ds.rio.to_raster(file)

            self.log.info(f'Wrote geotiff to: {file}')

    def process(self, hashmap, classify, colorize=None, merge=False, save=True, exit=True, **kwargs):
        """
        Processes the AMD pipeline for this data loader

        Parameters
        ----------
        classify : dict
            Variables to process through the classify algorithm in the form of
            {variable: masks}
        colorize : dict, default=None
            Colorize processed variables
        merge : bool, default=False
            Merge processed variables together
        save : bool, default=True
            Save processed variables
        exit : bool, default=True
            Calls self.exit to exit this object if it is a ray actor
        kwargs : dict
            Output parameters passed directly to the `save` function

        Returns
        -------
        self.products : dict
            Products generated by the pipeline
        """
        # Reset products
        self.prods  = {}
        self.colors = {}

        for var, opts in classify.items():
            self.log.info(f'Classifying {var}')
            self.createMask(opts.mask)
            self.prods[var] = self.classify(
                ds         = var,
                hashmap    = hashmap,
                mask       = self.data.mask,
                mask_class = opts.get('mask_class', 0),
                default    = opts.get('default', 0),
            )

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

        if exit:
            self.exit()

        return self.products

    def exit(self):
        """
        Calls ray.actor.exit_actor
        """
        import ray

        ray.actor.exit_actor()

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
