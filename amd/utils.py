# Builtins
import logging
import os
import sys

from pathlib import Path

# External
import earthaccess
import ray

from mlky.ext.ray import Config as C


Logger = logging.getLogger('amd/utils')


def initConfig(config, patch, defs, override, printconfig=False, printonly=False, print=print):
    """
    Initializes the mlky Config object

    Parameters
    ----------
    mlky.cli options
    """
    C(config, _patch=patch, _defs=defs, _override=override)

    # Print configuration to terminal
    if printconfig or printonly:
        print(f'Config({config!r}, _patch={patch!r}, _defs={defs})')
        print('-'*100)
        print(C.toYaml(comments=None, listStyle='short', header=False))
        print('-'*100)

        if printonly:
            sys.exit()

    ray.init(**C.ray)
    C.initRay()


def initLogging(mode=None):
    """
    Initializes the logging module per the config
    """
    # Logging handlers
    handlers = []

    # Create console handler
    sh = logging.StreamHandler(sys.stdout)

    if (level := C.log.terminal):
        sh.setLevel(level)

    handlers.append(sh)

    if (file := C.log.file):
        if (mode or C.log.mode) == 'write' and os.path.exists(file):
            os.remove(C.log.file)

        # Add the file logging
        fh = logging.FileHandler(file)
        fh.setLevel(C.log.level or logging.DEBUG)

        handlers.append(fh)

    logging.basicConfig(
        level    = C.log.get('level', 'DEBUG'),
        format   = C.log.get('format', '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'),
        datefmt  = C.log.get('format', '%m-%d %H:%M'),
        handlers = handlers,
    )


def download(urls, output='./downloads', overwrite=False):
    """
    Downloads files from a URL

    Parameters
    ----------
    urls: list
        URLs to download
    output: str, default='./downloads'
        Output directory
    overwrite: bool, default=False
        Overwrite existing files
    """
    Logger.info('Logging into earthaccess')
    earthaccess.login()
    session = earthaccess.get_requests_https_session()

    output = Path(output)
    output.mkdir(exist_ok=True, parents=True)
    Logger.debug(f'Downloads output: {output}')

    for url in urls:
        name = url.split('/')[-1]
        file = output / name

        if overwrite or not file.exists():
            Logger.debug(f'Retrieving {url} => {file}')
            try:
                with session.get(url, stream=True) as stream:
                    with open(file, 'wb') as dst:
                        for chunk in stream.iter_content(chunk_size=64*2**20):
                            dst.write(chunk)
            except Exception as e:
                Logger.error(f'Failed to retrieve file: {url}\nReason: {e}')
        else:
            Logger.debug(f'File already exists, skipping: {file}')
