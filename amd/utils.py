# Builtins
import logging
import sys

from pathlib import Path

# External
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
    output = Path(output)

    for url in urls:
        name = url.split('/')[-1]
        file = output / name

        if overwrite or not file.exists():
            resp = requests.get(url)
            if resp:
                with open(file, 'rb') as f:
                    f.write(resp.content)
            else:
                Logger.error(f'Failed to retrieve file ({resp.status_code}: {resp.reason}): {url}')
