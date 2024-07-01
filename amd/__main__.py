# Builtin
import logging
import os
import sys

from pathlib import Path

# External
import click
import mlky

from mlky import Config as C


Logger = logging.getLogger('amd/cli')


def initConfig(config, patch, defs, override, printconfig=False, printonly=False, print=print):
    """
    Initializes the mlky Config object
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


def initLogging():
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
        if Config.log.mode == 'write' and os.path.exists(file):
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


@click.group(name='amd')
def cli():
    """\
    EMIT Applications Support for the Assessment of Mined Lands Remediation
    """
    ...


# Path to the mlky definitions file for timefed
defs = Path(__file__).parent / 'configs/defs.yml'

@cli.command(name='run', context_settings={'show_default': True})
@mlky.cli.config
@mlky.cli.patch
@mlky.cli.defs(default=defs)
@mlky.cli.override
@click.option('-dv', '--disableValidate', help='Disables the validation requirement. Validation will still be occur, but execution will not be prevented')
@click.option("-pc", "--printConfig", help="Prints the configuration to terminal and continues", is_flag=True)
@click.option("-po", "--printOnly", help="Prints the configuration to terminal and exits", is_flag=True)
def main(disablevalidate, **kwargs):
    """\
    Executes AMD scripts
    """
    initConfig(**kwargs, print=click.echo)
    initLogging()

    if Config.validateObj() or disablevalidate:
        from amd.minerals import main
        main()
    else:
        Logger.error('Please correct the configuration errors before proceeding')


# Add mlky as subcommands
mlky.cli.setDefaults(patch='generated', defs=defs)
cli.add_command(mlky.cli.commands)


if __name__ == '__main__':
    main()
