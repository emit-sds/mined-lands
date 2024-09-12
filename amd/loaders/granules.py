import logging
import re
import tempfile

from pathlib import Path

import xarray as xr

from emit_tools import emit_xarray

from amd import utils


ProductVariables = {
    'RFL': ['reflectance'],
    'RFLUNCERT': ['reflectance_uncertainty'],
    'MASK': ['mask', 'band_mask'],
    'MIN': [
        'group_1_band_depth',
        'group_1_mineral_id',
        'group_2_band_depth',
        'group_2_mineral_id'
    ],
    'MINUNCERT': [
        'group_1_band_depth_unc',
        'group_1_fit',
        'group_2_band_depth_unc',
        'group_2_fit'
    ]
}
# Create a hashtable the dim: product source
VariableSources = {var: source for source, varis in ProductVariables.items() for var in varis}


class Granule:
    """
    EMIT granule manager
    """
    session = None
    mask    = None

    # For user reference
    productVariables = ProductVariables
    variableSources  = VariableSources

    def __init__(self, granule, dir='.', subdir=False, download=True, tmp=False):
        """
        Parameters
        ----------
        granule : str
            EMIT granule
        dir : str, default='.'
            Path to directory to search for the products of the granule
        subdir : bool, default=False
            Products are within a subdirectory of the same name, eg. dir/granule/products
            If products need to be downloaded, they'll be placed in this subdir
        download : bool, default=True
            Download missing products
        tmp : bool, default=False
            Use a temp directory for downloading products
        """
        self.granule  = granule
        self.download = download

        self.dir = Path(dir)
        if subdir:
            self.dir /= granule

        if tmp:
            self.tmp = Path(tempfile.gettempdir()) / f'amd/{granule}'
        else:
            self.tmp = self.dir

        # Reference dictionary
        self.products = {
            'RFL'      : Path(f'EMIT_L2A_RFL_{granule}.nc'),
            'RFLUNCERT': Path(f'EMIT_L2A_RFLUNCERT_{granule}.nc'),
            'MASK'     : Path(f'EMIT_L2A_MASK_{granule}.nc'),
            'MIN'      : Path(f'EMIT_L2B_MIN_{granule}.nc'),
            'MINUNCERT': Path(f'EMIT_L2B_MINUNCERT_{granule}.nc')
        }

        # Will cache loaded products
        self.cache = {}

        self.log = logging.getLogger(f'Granule[{granule}]')

    def __repr__(self):
        return f'<EMIT Granule({self.granule})'

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

    def load(self, product, merge=False):
        """
        Loads an EMIT product using emit_tools. If the product doesn't presently exist
        then it will be downloaded. A loaded product will remain in memory in the
        self.cache dict.

        Parameters
        ----------
        product : str, Path, list[str], 'all'
            Product of interest. This can also be a variable from a product which will
            load that product. If 'all' or a list, loads multiple products.
        merge : bool, default=False
            If multiple products are loaded, merge them together into a single dataset

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
                data.append(self.load(prod))

            if merge:
                return xr.merge(data)
            return data

        path = self.getProduct(product)

        if (file := path).exists():
            pass
        elif (file := self.dir / path).exists():
            pass
        elif (file := self.tmp / path).exists():
            pass
        else:
            if self.session is None:
                self.session = utils.getEarthAccessSession()

            # Download the product if it doesn't presently exist
            file.parent.mkdir(exist_ok=True, parents=True)
            utils.download(
                url = self.url(path),
                output = file.parent,
                session = self.session
            )

        if file.exists():
            if path not in self.cache:
                self.log.info(f'Loading product {file}')
                self.cache[path] = emit_xarray(file, ortho=True)

            # Return a variable of the product if that was the original request
            data = self.cache[path]
            if product in data:
                return data[product]
            return data
        else:
            raise FileNotFoundError(f'Product could not be found or downloaded: {product}')

    def url(self, product):
        """
        Generates the URL to download the desired product

        Parameters
        ----------
        product : str, Path
            Product of interest

        Returns
        -------
        str
            URL to download
        """
        product = self.getProduct(product)

        if 'L2A' in product.stem:
            return f'https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/EMITL2ARFL.001/EMIT_L2A_RFL_{self.granule}/{product}'

        if 'L2B' in product.stem:
            return f'https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/EMITL2BMIN.001/EMIT_L2B_MIN_{self.granule}/{product}'

    def filterClouds(self, bands, reset=False):
        """
        Masks out cloud bands using the L2A_MASK product

        Parameters
        ----------
        bands : int, list[int]
            Bands along the `mask_bands` dimension to filter out
        reset : bool, default=False
            Reset the existing internal self.mask

        Returns
        -------
        self.mask
            Applied mask & any previous masks
        """
        assert max(bands) <= 4, 'Mask bands must be between 0 and 4 inclusive'
        assert min(bands) >= 0, 'Mask bands must be between 0 and 4 inclusive'

        mask = ~self.load('mask').isel(mask_bands=bands).sum('mask_bands').astype(bool)

        if reset or self.mask is None:
            self.mask = mask
        else:
            self.mask &= mask

        return self.mask

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
        if re.match(r'([<>]=?) ([-+]?\d*\.?\d+)', cond):
            prod = self.load(var)
            mask = eval(f'prod {cond}')

            if reset or self.mask is None:
                self.mask = mask
            else:
                self.mask &= mask

            return self.mask
        else:
            self.log.error(f'Invalid conditional "{var} {cond}", must be of regex form "([<>]=?) ([-+]?\d*\.?\d+)"')

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
            if var == 'clouds':
                self.log.info('Filtering clouds')
                self.filterClouds(strat)
            elif var in VariableSources:
                self.log.info('Filtering conditional')
                self.filterConditional(var, strat)
            else:
                self.log.error(f'Invalid filter provided: {var}: {strat}')

        return self.mask

    def process(self, hashmap, process):
        merge = []
        for var, opts in process.items():
            self.createFilter(opts.filter)
            data = self.classify(var, hashmap, **opts)
            merge.append(data)

        ds = xr.merge(merge)

        return ds
