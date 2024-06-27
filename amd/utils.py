# Builtins
import logging
import sys

from pathlib import Path

# External
import earthaccess
import requests

from mlky import Config


Logger = logging.getLogger('amd/utils')


def initLogging():
    """
    Initializes the logging module per the config
    """
    # Logging handlers
    handlers = []

    # Create console handler
    sh = logging.StreamHandler(sys.stdout)

    if Config.log.terminal:
        sh.setLevel(getattr(logging, Config.log.terminal))

    handlers.append(sh)

    if Config.log.file:
        if Config.log.mode == "write" and os.path.exists(Config.log.file):
            os.remove(Config.log.file)

        # Add the file logging
        fh = logging.FileHandler(Config.log.file)
        fh.setLevel(Config.log.level or logging.DEBUG)
        handlers.append(fh)

    logging.basicConfig(
        level    = getattr(logging, Config.log.level or 'DEBUG'),
        format   = Config.log.format or "%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
        datefmt  = Config.log.datefmt or "%m-%d %H:%M",
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
