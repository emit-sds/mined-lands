# Builtins
import logging

from pathlib import Path

# External
import earthaccess

from mlky import Config


Logger = logging.getLogger('amd/utils')


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
