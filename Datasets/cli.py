from .ros_datasets_injestor import RosDatasetsInjestor

import click
import sys

AVAILABLE_DATASET_MAP = {
    "autoware": "Autoware",
    "sugarbeets": "SugarBeets",
    "uzh_fpv": "UZH_FPV",
}

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--dataset",
    "datasets",
    multiple=True,
    type=click.Choice(list(AVAILABLE_DATASET_MAP.keys()), case_sensitive=False),
    help="Dataset to load. Can be repeated to select multiple datasets.",
)
@click.option("--load_all", is_flag=True, help="Loads all defined datasets.")
@click.option("--n_bags_to_load", default=None, type=int, help="Number of bags to upload per dataset. Omit to load all available bags.")
def run_dataset_injestor(datasets, load_all, n_bags_to_load):
    """
    Mosaico dataset loader Runner

    This utility allows you to start rosbags dataset injestion
    """
    if load_all:
        datasets_to_load = list(AVAILABLE_DATASET_MAP.values())
    else:
        datasets_to_load = [AVAILABLE_DATASET_MAP[d] for d in datasets]

    if not datasets_to_load:
        click.secho(
            "No datasets to injest requested. Please run the command with --help to see all available  Datasets",
            fg="cyan",
            bold=True,
        )
        sys.exit(0)

    click.secho(
        f"Requested injestion of {datasets_to_load} dataset(s)", fg="cyan", bold=True
    )

    try:
        injestor = RosDatasetsInjestor(datasets_to_load, n_bags_to_load)
        injestor.load_datasets()
    except Exception as e:
        click.secho(f"\nExecution failed: {e}", fg="red", bold=True)
        sys.exit(1)
