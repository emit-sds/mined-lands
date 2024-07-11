# Builtin
import logging

from pathlib import Path

# External
import click
import mlky

from mlky.ext.ray import Config as C

# Internal
from amd import utils


Logger = logging.getLogger('amd/cli')


@click.group(name='amd')
def cli():
    """\
    EMIT Applications Support for the Assessment of Mined Lands Remediation
    """
    ...


# Path to the mlky definitions file
defs = Path(__file__).parent / 'configs/defs/defs.yml'


@cli.command(name='run', context_settings={'show_default': True})
@mlky.cli.config
@mlky.cli.patch
@mlky.cli.defs(default=defs)
@mlky.cli.override
@click.option('-dv', '--disableValidate', is_flag=True, help='Disables the validation requirement. Validation will still be occur, but execution will not be prevented')
@click.option("-pc", "--printConfig", is_flag=True, help="Prints the configuration to terminal and continues")
@click.option("-po", "--printOnly", is_flag=True, help="Prints the configuration to terminal and exits")
def main(disablevalidate, **kwargs):
    """\
    Executes AMD scripts
    """
    utils.initConfig(**kwargs, print=click.echo)
    utils.initLogging()

    if C.validateObj() or disablevalidate:
        from amd.minerals import main
        main()
    else:
        Logger.error('Please correct the configuration errors before proceeding')


# Add mlky as subcommands
mlky.cli.setDefaults(patch='generated', defs=defs)
cli.add_command(mlky.cli.commands)


if __name__ == '__main__':
    main()
