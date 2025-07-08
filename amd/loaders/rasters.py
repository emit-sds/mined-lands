import logging
import re

from pathlib import Path

import xarray as xr


ProductVariables = {
    'min': [
        'group_1_band_depth',
        'group_1_mineral_id',
        'group_2_band_depth',
        'group_2_mineral_id'
    ],
    'minunc': [
        'group_1_band_depth_unc',
        'group_1_fit',
        'group_2_band_depth_unc',
        'group_2_fit'
    ],
    'mask': [
        'Cloud flag',
        'Cirrus flag',
        'Water flag',
        'Spacecraft Flag',
        'Dilated Cloud Flag',
        'AOD550',
        'H2O',
        'Aggregate Flag'
    ]
}
# Create a hashtable the dim: product source
VariableSources = {var: source
    for source, variable in ProductVariables.items()
        for var in variable
}


class Raster:
    """
    EMIT raster manager
    """
    ds   = None
    mask = None

    # For user reference
    productVariables = ProductVariables
    variableSources  = VariableSources

    rename = {
        'y': 'latitude',
        'x': 'longitude'
    }

    def __init__(self, raster, dir='.', rename=None):
        """
        Parameters
        ----------
        raster : str
            EMIT raster name
        dir : str, default='.'
            Path to directory to search for the raster
        rename : dict, default=None
            Renames dimensions/variables to something else. None uses the built-in default:
                {
                    'y': 'latitude',
                    'x': 'longitude'
                }
        """
        self.dir = Path(dir)

        if raster.endswith('.hdr'):
            raster = raster[:-4]

        split = raster.split('_')
        if split[0] in ProductVariables:
            raster = '_'.join(split[1:])

        self.raster = raster

        # Reference dictionary
        self.products = {
            # 'rfl'   : Path(f'rfl_{raster}'),
            # 'rflunc': Path(f'rflunc_{raster}'),
            'mask'  : Path(f'mask_{raster}'),
            'min'   : Path(f'min_{raster}'),
            'minunc': Path(f'minunc_{raster}')
        }

        # Will cache loaded products
        self.cache = {}

        if rename is not None:
            self.rename = rename

        self.log = logging.getLogger(f'Raster[{self.raster}]')

    def __repr__(self):
        return f'<EMIT Raster({self.raster})'

    def _load_raster(self, file):
        """
        Loads an EMIT raster using xarray.

        Parameters
        ----------
        var : str, list[str], default=None
            Loads the raster file. If str or list of str, returns those variables.
            None returns the entire dataset.

        Returns
        -------
        xr.Dataset, xr.DataArray, list[xr.Dataset, xr.DataArray]
            Loaded data/variable(s)
        """
        self.log.debug(f'Loading raster {file}')
        ds = xr.load_dataset(file, engine='rasterio')

        # Split the band dimension
        product = file.name.split('_')[0]
        bands = ProductVariables.get(product)
        if bands:
            self.log.debug(f'Unpacking `band_data` variable along the `band` dimension as: {bands}')
            ds['band'] = list(bands)
            ds = ds['band_data'].to_dataset('band')

        # Rename dimensions
        if self.rename:
            self.log.debug(f'Renaming variables/coords: {self.rename}')
            for key, val in self.rename.items():
                ds = ds.rename({key: val})

        return ds

    def getProduct(self, product):
        """
        Retrieves a product from the self.products reference table, otherwise returns
        the input

        Parameters
        ----------
        product : str, Path
            Product of interest. This can also be a variable from a product which will
            load that product

        Returns
        -------
        Path
            Corresponding product
        """
        if isinstance(product, str):
            if product in VariableSources:
                product = VariableSources[product]
            if product not in self.products:
                raise AttributeError(f'Unknown product {product!r}, must be one of {self.products.keys()} or a variable {list(VariableSources)}')
            return self.products[product]
        return product

    def load(self, product, merge=False, ignore=False):
        """
        Loads a product an EMIT mosaic. A loaded product will remain in memory in the
        self.cache dict.

        Parameters
        ----------
        product : str, Path, list[str], 'all'
            Product of interest. This can also be a variable from a product which will
            load that product. If 'all' or a list, loads multiple products.
        merge : bool, default=False
            If multiple products are loaded, merge them together into a single dataset
        ignore : bool, default=False
            Ignore products that do not exist (ie. do not raise)

        Returns
        -------
        xr.Dataset, xr.DataArray, list[xr.Dataset, xr.DataArray]
            Loaded data product(s)/variable(s)
        """
        if product == 'all' or isinstance(product, list):
            if product == 'all':
                product = self.products

            data = []
            for prod in product:
                load = self.load(prod, ignore=ignore)
                if load is not None:
                    data.append(load)

            if merge:
                return xr.merge(data)
            return data

        path = self.getProduct(product)

        if not (file := path).exists():
            file = self.dir / path

        if not (header := file.with_suffix('.hdr')):
            self.log.error(f'Product header file not found: {header}')
            if not ignore:
                raise FileNotFoundError(f'Product header file not found: {header}')

        if file.exists():
            if path not in self.cache:
                self.log.info(f'Loading product {file}')
                self.cache[path] = self._load_raster(file)

            # Return a variable of the product if that was the original request
            data = self.cache[path]
            if product in data:
                return data[product]
            return data
        else:
            self.log.error(f'Product file not found: {file}')
            if not ignore:
                raise FileNotFoundError(f'Product file not found: {file}')

    def filterConditional(self, var, cond, reset=False):
        """
        Creates a mask using a conditional filter on a variable

        Parameters
        ----------
        var : str
            Variable to filter on
        cond : str
            Conditional string in the regex form "([<>]=?) ([-+]?\d*\.?\d+)"
            Ie. must start with [<,>,<=,>=], following by a space, followed by a
            positive or negative int or float. Scientific notation is not supported.
        reset : bool, default=False
            Reset the existing internal self.mask

        Returns
        -------
        self.mask
            Applied mask & any previous masks
        """
        # Verify this is a valid conditional
        if re.match(r'([<>=]=?) ([-+]?\d*\.?\d+)', cond):
            prod = self.load(var)
            mask = eval(f'prod {cond}')

            if reset or self.mask is None:
                self.mask = mask
            else:
                self.mask &= mask

            return self.mask
        else:
            self.log.error(f'Invalid conditional "{var} {cond}", must be of regex form "([<>=]=?) ([-+]?\d*\.?\d+)"')

    def createFilter(self, filters):
        """
        Create a single mask filter from a combination of filters

        Parameters
        ----------
        filters : dict
            Filters to apply

        Returns
        -------
        self.mask : xr.DataArray
            Combined boolean mask of all filters using &
        """
        # Reset the current mask, if there is one
        self.mask = None

        for var, strat in filters.items():
            if var in VariableSources:
                self.log.info('Filtering conditional')
                self.filterConditional(var, strat)
            else:
                self.log.error(f'Invalid filter provided: {var}: {strat}')

        return self.mask
