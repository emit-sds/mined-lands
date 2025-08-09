import json
import logging
import ssl
from datetime import datetime as dtt
from urllib import request

import click
from shapely.geometry import Polygon


Logger = logging.getLogger(__name__)
CovURL = 'https://earth.jpl.nasa.gov/emit-mmgis-lb/Missions/EMIT/Layers/coverage/coverage_pub.json'
Info = {
    'granule' : 'L2A Reflectance Download',
    'fid' : 'fid'
}

def filter_roi(coverage, lat, lon, inplace=True):
    """
    Filters for features that intersect with a region of interest.

    Parameters
    ----------
    coverage : dict
        EMIT coverage dictionary
    lat : tuple[float, float]
        Latitude boundaries for the region of interest
    lon : tuple[float, float]
        Longitude boundaries for the region of interest
    inplace : bool, default=True
        Replace the `features` key of the coverage dictionary with the filtered list
        If False, returns the list

    Returns
    -------
    select : list
        Selected features list
    """
    features = coverage['features']
    Logger.info(f'Filtering for Region of Interest from {len(features)} features')

    target = Polygon([
        (lon[0], lat[0]),
        (lon[1], lat[0]),
        (lon[1], lat[1]),
        (lon[0], lat[1]),
        (lon[0], lat[0])
    ])
    select = []
    for feature in features:
        source = Polygon(feature['geometry']['coordinates'][0])
        if source.intersects(target):
            select.append(feature)

    Logger.info(f'Selected {len(select)}')
    if inplace:
        coverage['features'] = select

    return select


def filter_time(coverage, start=None, end=None, inplace=True):
    """
    Filters features if their start and/or stop times fall within the requested times

    Parameters
    ----------
    coverage : dict
        EMIT coverage dictionary
    start : str
        Minimum start time
    end : str
        Maximum end time
    inplace : bool, default=True
        Replace the `features` key of the coverage dictionary with the filtered list
        If False, returns the list

    Returns
    -------
    select : list
        Selected features list
    """
    features = coverage['features']
    Logger.info(f'Filtering for time ({start}, {end}) from {len(features)} features')

    select = []
    for feature in coverage['features']:
        st = dtt.strptime(feature['properties']['start_time'], '%Y-%m-%dT%H:%M:%SZ')
        ed = dtt.strptime(feature['properties']['end_time'], '%Y-%m-%dT%H:%M:%SZ')
        if start is None or start <= st:
            if end is None or ed <= end:
                select.append(feature)

    Logger.info(f'Selected {len(select)}')
    if inplace:
        coverage['features'] = select

    return select


def filter_clouds(coverage, fraction, inplace=True):
    """
    Filters features based off the `Total Cloud Fraction` property.

    Parameters
    ----------
    coverage : dict
        EMIT coverage dictionary
    fraction : float
        Fraction to filter with. Features with values beneath this value are selected
    inplace : bool, default=True
        Replace the `features` key of the coverage dictionary with the filtered list
        If False, returns the list

    Returns
    -------
    select : list
        Selected features list
    """
    features = coverage['features']
    Logger.info(f'Filtering max cloud fraction {fraction} from {len(features)} features')

    select = []
    for feature in coverage['features']:
        if feature['properties'].get('Total Cloud Fraction', 2) <= fraction:
            select.append(feature)

    Logger.info(f'Selected {len(select)}')
    if inplace:
        coverage['features'] = select

    return select


def download_coverage(file=None, no_ssl=False):
    """
    Downloads the EMIT pub_coverage.json

    Parameters
    ----------
    file : str, default=None
        Path to the local file. If provided, the pub_coverage.json will be saved to
        this path
    no_ssl : bool, default=False
        If True, disables SSL certificate validation when downloading

    Returns
    -------
    dict
        Parsed JSON content

    Raises
    ------
    HTTPError
        If the HTTP request fails
    URLError
        If there is a network-related error
    JSONDecodeError
        If the loaded content is not valid JSON
    """
    Logger.info(f'Downloading coverage from URL: {CovURL}')
    try:
        with request.urlopen(CovURL) as url:
            coverage = json.load(url)
    except Exception:
        if no_ssl:
            Logger.info('Trying without validating SSL cert')
            context = ssl._create_unverified_context()
            with request.urlopen(CovURL, context=context) as url:
                coverage = json.load(url)
        else:
            raise

    # Save JSON locally
    if file:
        Logger.info(f'Writing coverage to json: {file}')
        with open(file, "w") as f:
            json.dump(coverage, f, indent=2)

    return coverage


def query(
    coverage_file = None,
    lat_bounds    = (-89.9, 89.9),
    lon_bounds    = (-179.9, 179.9),
    start_date    = None,
    end_date      = None,
    fraction      = 1.,
    info          = 'granule',
    output        = None,
    no_ssl        = False
):
    """
    Queries the EMIT coverage JSON for a list of FIDs that meet filter criterias.

    Parameters
    ----------
    coverage_file : str, default=None
        Path to a local coverage file. If not provided, will automatically download it
    lat_bounds : tuple[float, float], default=(-89.9, 89.9)
        Latitude boundaries for region of interest
    lon_bounds : tuple[float, float], default=(-179.9, 179.9)
        Longitude boundaries for region of interest
    start_date : str, default=None
        Minumum start date
    end_date : str, default=None
        Maximum end date
    fraction : float, default=1.0
        Maximum cloud fraction allowed
    output : str, default=None
        Output txt file to save FIDs
    no_ssl : bool, default=False
        Allow attempting to pull coverage from URL without validating the SSL
        certificate. Will still attempt to do so by default

    Returns
    -------
    granules : list[str]
        List of filtered granule IDs
    """
    if coverage_file:
        Logger.info('Loading coverage from file')
        with open(coverage_file, 'rb') as file:
            coverage = json.load(file)
    else:
        coverage = download_coverage(no_ssl=no_ssl)

    filter_roi(coverage, lat_bounds, lon_bounds)
    filter_time(coverage, start_date, end_date)
    filter_clouds(coverage, fraction)

    data = []
    prop = Info[info]
    for feature in coverage['features']:
        data.append(feature['properties'][prop])

        if info == 'granule':
            data[-1] = data[-1][-34:-3]

    string = '\n'.join(data)

    if output:
        with open(output, 'w') as file:
            file.write(string)

        Logger.info(f'Wrote to {output}')
    else:
        Logger.info(f'Data retrieved:\n{string}')

    Logger.info('Finished')
    return data


@click.command(name='query')
@click.option('-c', '--coverage_file',
    help='Path to a local coverage file. If not provided, will automatically download it'
)
@click.option('-lat', '--lat_bounds', nargs=2, default=(-89.9, 89.9), type=float,
    help='Latitude boundaries for region of interest'
)
@click.option('-lon', '--lon_bounds', nargs=2, default=(-179.9, 179.9), type=float,
    help='Longitude boundaries for region of interest'
)
@click.option('-sd', '--start_date', type=click.DateTime(['%Y%m%dT%H:%M:%S']),
    help='Minumum start date'
)
@click.option('-ed', '--end_date', type=click.DateTime(['%Y%m%dT%H:%M:%S']),
    help='Maximum end date'
)
@click.option('-f', '--fraction', default=1, type=float,
    help='Maximum cloud fraction allowed'
)
@click.option('-i', '--info', type=click.Choice(Info), default='granule',
    help='Type of information to retrieve'
)
@click.option('-o', '--output',
    help='Output txt file to save FIDs'
)
@click.option('-ns', '--no-ssl', is_flag=True,
    help='Disable SSL cert verification [not recommended]'
)
@click.option('-do', '--download-only', type=str,
    help='Only downloads the coverage file to this path then exits'
)
def cli(download_only, **options):
    """\
    Queries the EMIT coverage JSON for a list of FIDs that meet filter criterias
    """
    logging.basicConfig(
        level    = 'DEBUG',
        format   = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt  = '%m-%d %H:%M',
    )

    if download_only:
        download_coverage(file=download_only, no_ssl=options.get("no_ssl"))
        Logger.info('Finished')
    else:
        query(**options)


if __name__ == '__main__':
    cli()
