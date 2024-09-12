import logging
import re

from pathlib import Path

import xarray as xr


class Raster:
    """
    EMIT raster manager
    """
    ds   = None
    mask = None

    bands = [
        'group_1_band_depth',
        'group_1_mineral_id',
        'group_2_band_depth',
        'group_2_mineral_id'
    ]
    rename = {
        'y': 'latitude',
        'x': 'longitude'
    }

    def __init__(self, raster, dir='.', bands=None, rename=None):
        """
        Parameters
        ----------
        raster : str
            EMIT raster name
        dir : str, default='.'
            Path to directory to search for the raster
        bands : list, default=None
            Unpacks the `band_data` variable into independent variables. None uses the built-in default:
                [
                    'group_1_band_depth',
                    'group_1_mineral_id',
                    'group_2_band_depth',
                    'group_2_mineral_id'
                ]
        rename : dict, default=None
            Renames dimensions/variables to something else. None uses the built-in default:
                {
                    'y': 'latitude'
                    'x': 'longitude'
                }
        """
        self.raster = raster
        self.file   = Path(dir) / raster

        # Raster input
        if not self.file.suffix:
            self.header = self.file.with_suffix('.hdr')

        # Header input
        elif self.file.suffix == '.hdr':
            self.header = self.file
            self.file   = self.header.with_suffix('')

        # Verify files exist
        if not self.file.exists():
            raise AttributeError(f'Input raster file does not exist: {self.file}')
        if not self.header.exists():
            raise AttributeError(f'Header file not found for raster file: {self.header}')

        if bands is not None:
            self.bands = bands
        if rename is not None:
            self.rename = rename

        self.log = logging.getLogger(f'Raster[{self.raster}]')

    def __repr__(self):
        return f'<EMIT Raster({self.raster})'

    def load(self, var=None):
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
        if self.ds is None:
            self.log.debug(f'Loading raster {self.file}')
            ds = xr.load_dataset(self.file, engine='rasterio')

            # Split the band dimension
            if self.bands:
                self.log.debug(f'Unpacking `band_data` variable along the `band` dimension as: {self.bands}')
                ds['band'] = list(self.bands)
                ds = ds['band_data'].to_dataset('band')

            # Rename dimensions
            if self.rename:
                self.log.debug(f'Renaming variables/coords: {self.rename}')
                ds = ds.rename(**self.rename)

            self.ds = ds

        if var:
            return self.ds[var]
        return self.ds

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
            if var in self.bands:
                self.log.info('Filtering conditional')
                self.filterConditional(var, strat)
            else:
                self.log.error(f'Invalid filter provided: {var}: {strat}')

        return self.mask
