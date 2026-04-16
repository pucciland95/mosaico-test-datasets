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
@click.option("--autoware", is_flag=True, help="Loads the Autoware dataset.")
@click.option("--sugarbeets", is_flag=True, help="Loads the SugarBeets dataset.")
@click.option("--uzh_fpv", is_flag=True, help="Loads the UZH_FPV dataset.")
@click.option("--load_all", is_flag=True, help="Loads all defined datasets.")
def run_dataset_injestor(autoware, sugarbeets, uzh_fpv, load_all):
    """
    Mosaico dataset loader Runner

    This utility allows you to start rosbags dataset injestion
    """
    datasets_to_load: list[str] = []

    if load_all:
        datasets_to_load = list(AVAILABLE_DATASET_MAP.values())

    else:
        if autoware:
            datasets_to_load.append(AVAILABLE_DATASET_MAP["autoware"])

        if sugarbeets:
            datasets_to_load.append(AVAILABLE_DATASET_MAP["sugarbeets"])

        if uzh_fpv:
            datasets_to_load.append(AVAILABLE_DATASET_MAP["uzh_fpv"])

    if len(datasets_to_load) <= 0:
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
        injestor = RosDatasetsInjestor(datasets_to_load)
        injestor.load_datasets()
    except Exception as e:
        click.secho(f"\nExecution failed: {e}", fg="red", bold=True)
        sys.exit(1)
