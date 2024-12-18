import logging
import re

import ray

from mlky import (
    Config,
    Sect
)
from mlky.utils import Track

from amd.core.amd import AMD
from amd.loaders import (
    Granule,
    Raster
)


Logger = logging.getLogger('batch')


def parseGlob(products):
    """
    Parses globbed products for granule strings

    Parameters
    ----------
    products : list[pathlib.Path]
        Products to parse

    Returns
    -------
    set
        Unique set of granule IDs
    """
    def parse(string):
        if match := re.findall(r'EMIT_L[1A,2B]\D+(\w+).nc', string):
            return match[0]
        return string

    return {parse(file.name) for file in products}


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
            if products.endswith('.txt'):
                Logger.info(f'Reading products from file: {products}')
                with open(products, 'r') as file:
                    products = file.read().split('\n')
            else:
                Logger.info(f'Using glob to discover products: {flags.dir / products}')
                products = parseGlob(flags.dir.glob(products))

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
        # ray.get(done)
        report(jobs)

    Logger.info('Finished')


if __name__ == '__main__':
    Logger.error('Calling this script directly is not supported, please use the AMD CLI')
