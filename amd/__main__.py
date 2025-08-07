# Builtin
import logging

from pathlib import Path

# External
import click
import mlky

from mlky import Config as C

# Internal
from amd import utils
from amd.core import query

# rasterio._io is very spammy
logging.getLogger("rasterio._io").setLevel(logging.ERROR)

Logger = logging.getLogger(__name__)


@click.group(name='amd')
def cli():
    """\
    EMIT Applications Support for the Assessment of Mined Lands Remediation
    """
    # utils.initLogging(C.log)


# Path to the mlky definitions file
defs = Path(__file__).parent / '../configs/defs/defs.yml'


@cli.command(name='run', context_settings={'show_default': True})
@mlky.cli.config
@mlky.cli.patch
@mlky.cli.defs(default=defs)
@mlky.cli.override
@click.option('-dv', '--disableValidate', is_flag=True, help='Disables the validation requirement. Validation will still be occur, but execution will not be prevented')
@click.option("-pc", "--printConfig", is_flag=True, help="Prints the configuration to terminal and continues")
@click.option("-po", "--printOnly", is_flag=True, help="Prints the configuration to terminal and exits")
def batch(disablevalidate, **kwargs):
    """\
    Executes AMD scripts
    """
    utils.initConfig(**kwargs)

    if C.validateObj() or disablevalidate:
        from amd.batch import process

        utils.initLogging(C.log)
        process()
    else:
        Logger.error('Please correct the configuration errors before proceeding')


@cli.command(name='stack', context_settings={'show_default': True})
@mlky.cli.config
@mlky.cli.patch
@mlky.cli.defs(default=defs)
@mlky.cli.override
@click.option('-dv', '--disableValidate', is_flag=True, help='Disables the validation requirement. Validation will still be occur, but execution will not be prevented')
@click.option("-pc", "--printConfig", is_flag=True, help="Prints the configuration to terminal and continues")
@click.option("-po", "--printOnly", is_flag=True, help="Prints the configuration to terminal and exits")
def stack(disablevalidate, **kwargs):
    """\
    Executes AMD stack script
    """
    utils.initConfig(**kwargs)

    if C.validateObj() or disablevalidate:
        from amd.core.stack import main

        utils.initLogging(C.log)
        main()
    else:
        Logger.error('Please correct the configuration errors before proceeding')


# Add mlky as subcommands
mlky.cli.setDefaults(patch='generated', defs=defs)
cli.add_command(mlky.cli.commands)
cli.add_command(query.cli)


if __name__ == '__main__':
    cli()
