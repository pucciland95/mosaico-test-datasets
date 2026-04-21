"""
ROS Datasets Injector for the Mosaico platform.

This module provides the ``RosDatasetsInjestor`` class, which automates the
discovery, ingestion and deletion of ROS bag files into the Mosaico platform. It scans
a base directory for dataset folders (each identified by a ``configs.py``
file), loads per-dataset configuration with optional overrides on top of
global defaults, and sequentially injects every rosbag it finds into the
configured Mosaico instance via the ``RosbagInjector`` SDK component.
"""

# Mosaico SDK Imports
from mosaicolabs import SessionLevelErrorPolicy, MosaicoClient
from mosaicolabs.ros_bridge import RosbagInjector, ROSInjectionConfig
from mosaicolabs.ros_bridge.loader import ROSLoader

from pathlib import Path
from typing import Optional
import json

from rich.console import Console
from rich.panel import Panel

import importlib
import importlib.util


# Initialize Rich Console for beautiful terminal output
console = Console()


class RosDatasetsInjestor:
    """Discovers dataset folders and injects their ROS bags into Mosaico.

    A *dataset* is any sub-directory of the script's parent directory that
    contains a ``configs.py`` file.
    """

    DATASET_CONFIG_FILENAME = "configs.py"

    CONFIG_KEY_NAMES = [
        "MOSAICO_HOST",
        "MOSAICO_PORT",
        "PATH_TO_BAGS",
        "ROS_DISTRO",
        "TOPICS_TO_FILTER",
        "API_KEY",
        "ENABLE_TLS",
        "TLS_CERT_PATH",
    ]

    def __init__(self):
        """Initialise the injector loading global config."""

        self.global_configs_: dict[str, str] = {}
        self.global_configs_ = self._load_dataset_config()

    def _is_valid_dataset(self, path_to_dataset: Path) -> bool:
        """Check whether a path represents a valid dataset directory.

        A path is considered a valid dataset when it is a directory **and**
        it contains a ``configs.py`` file (the file may be empty).

        Args:
            path_to_dataset (Path): Filesystem path to evaluate.

        Returns:
            bool: ``True`` if the path is a directory containing
            ``configs.py``, ``False`` otherwise.
        """

        return (
            path_to_dataset.is_dir()
            and (path_to_dataset / self.DATASET_CONFIG_FILENAME).is_file()
        )

    def _discover_datasets(
        self, base_dir: Path, dataset_names_to_load: Optional[list[str]] = None
    ) -> list[Path]:
        """Discover all valid dataset directories under ``base_dir``.

        Args:
            base_dir (Path): Root directory to search for dataset folders.
            dataset_names_to_load (list[str] | None): Optional whitelist of
                folder names.  Folder names must match exactly (case-sensitive).
                Pass ``None`` to return all discovered datasets.

        Returns:
            list[Path]: Paths to the discovered (and optionally filtered)
            dataset directories.
        """

        all_datasets = [
            entry for entry in base_dir.iterdir() if self._is_valid_dataset(entry)
        ]

        if dataset_names_to_load is None:
            return all_datasets

        # Filtering accordingly to the passed datasets to load.
        # Notice that to filter effectively, the passed dataset names
        # need to coincide with the folder names
        remaining_datasets = list(
            filter(lambda dt_path: dt_path.name in dataset_names_to_load, all_datasets)
        )
        return remaining_datasets

    def _get_config_module(self, path_to_module: Optional[Path]):
        """Dynamically load a ``configs.py`` file as a Python module.

        Args:
            path_to_module (Path | None): Directory that contains the
                ``configs.py`` to load.  Pass ``None`` to load the global
                defaults from the script's own directory.

        Returns:
            types.ModuleType | None: The loaded module object, or ``None``
            if no ``configs.py`` could be found at the resolved path.
        """

        # Check whether it is necessary loading the default configs
        if path_to_module is None:
            path_to_module = Path(__file__).resolve().parent

        spec = importlib.util.spec_from_file_location(
            "cfg", path_to_module / self.DATASET_CONFIG_FILENAME
        )

        # Checking that config.py exists for the dataset, otherwise return
        if spec is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    def _load_dataset_config(
        self, dataset_dir_path: Optional[Path] = None
    ) -> Optional[dict[str, str]]:
        """Build the effective configuration dictionary for a dataset.

        Args:
            dataset_dir_path (Path | None): Directory of the dataset whose
                ``configs.py`` should be applied as overrides.  Pass ``None``
                (default) to load only the global defaults.

        Returns:
            dict[str, str] | None: Merged configuration dictionary, or
            ``None`` if the ``configs.py`` module could not be loaded for the
            given path.
        """

        # 1. Deep copy default configs
        config = {key: value for key, value in self.global_configs_.items()}

        # 2. Load the dataset's configs.py as a module
        module = self._get_config_module(dataset_dir_path)

        if module is None:
            return None

        # 3. Override configs
        for cfg_key in self.CONFIG_KEY_NAMES:
            if hasattr(module, cfg_key):
                config[cfg_key] = getattr(module, cfg_key)

        return config

    def _get_metadata(self, dataset_path: Path, rosbag_name: str) -> Optional[dict]:

        # Find requested metadata associated to rosbag name
        path_to_dataset_metadata = dataset_path / "metadata"

        rosbag_metadata_path = next(
            (
                mtp
                for mtp in path_to_dataset_metadata.glob("*.json")
                if mtp.name.removesuffix(".json") == rosbag_name
            ),
            None,
        )

        if rosbag_metadata_path is None or rosbag_metadata_path.exists() is False:
            console.print(
                f"Impossible to find metadata for {rosbag_name} in {path_to_dataset_metadata}"
            )
            return None

        with open(rosbag_metadata_path) as f:
            return json.load(f)

    def _get_name_from_rosbag(self, rosbag_path: Path) -> str:
        return rosbag_path.with_suffix("").name

    def delete_datasets(
        self,
        dataset_to_delete_name: list[str],
        n_bags_to_delete: Optional[int] = None,
    ):

        abs_path_to_this_file = Path(__file__).resolve().parent

        dataset_to_delete_paths_ = self._discover_datasets(
            abs_path_to_this_file, dataset_to_delete_name
        )

        if not dataset_to_delete_paths_:
            console.print(
                f"[bold red] Impossible to delete {dataset_to_delete_name}. These are not valid dataset names[/bold red]"
            )

        for dt_path in dataset_to_delete_paths_:
            configs = self._load_dataset_config(dt_path)

            if configs is None:
                console.print(
                    f"[bold red]Failed loading dataset {dt_path}. Are you sure there is a config.py file? [/bold red]"
                )
                continue

            # Sequence names coincide with rosbag names
            rosbag_names_to_delete = [
                self._get_name_from_rosbag(bp)
                for ext in ROSLoader.ACCEPTED_EXTENSIONS
                for bp in Path(configs["PATH_TO_BAGS"]).rglob(f"*{ext}")
            ]

            with MosaicoClient.connect(
                host=configs["MOSAICO_HOST"],
                port=configs["MOSAICO_PORT"],
                api_key=configs["API_KEY"],
                enable_tls=configs["ENABLE_TLS"],
            ) as client:
                all_loaded_sequences = client.list_sequences()

                sequences_to_delete = list(
                    set(all_loaded_sequences) & set(rosbag_names_to_delete)
                )

                if n_bags_to_delete is not None:
                    sequences_to_delete = sequences_to_delete[:n_bags_to_delete]

                console.print(
                    f"[bold]Deleting {len(sequences_to_delete)} sequences [/bold]"
                )

                for seq in sequences_to_delete:
                    console.print(f"[bold]Deleting loaded sequence {seq} [/bold]")
                    client.sequence_delete(seq)

    def load_datasets(
        self,
        datasets_name_to_load: Optional[list[str]] = None,
        n_bags_to_load: Optional[int] = None,
    ) -> None:
        """Ingest all discovered datasets into Mosaico.

        Args:
            datasets_name_to_load (list[str] | None): Optional whitelist of
                dataset folder names to process.  When ``None`` (default) all
                discovered datasets are loaded.
            n_bags_to_load (int | None): Optional number stating how many rosbags
            should be uploaded for each dataset. When ``None``, all rosbags
            for each dataset are loaded.

        Returns:
            None
        """

        abs_path_to_this_file = Path(__file__).resolve().parent

        dataset_to_load_paths_ = self._discover_datasets(
            abs_path_to_this_file, datasets_name_to_load
        )

        for dataset_path in dataset_to_load_paths_:
            console.print(
                Panel(
                    f"[bold green] Started loading datasets {dataset_path.name} [/bold green]"
                )
            )

            # 0) overriding default configuration for dataset loading
            configs = self._load_dataset_config(dataset_path)

            if configs is None:
                console.print(
                    f"[bold red]Failed loading dataset {dataset_path}. Are you sure there is a config.py file? [/bold red]"
                )
                continue

            # 1) Getting the rosbags (if present)
            ros_bag_paths = [
                bp
                for ext in ROSLoader.ACCEPTED_EXTENSIONS
                for bp in Path(configs["PATH_TO_BAGS"]).rglob(f"*{ext}")
            ]

            if not ros_bag_paths:
                console.print(
                    f"[bold yellow]No rosbags found at path {configs['PATH_TO_BAGS']}. Skipping this... [/bold yellow]"
                )
                continue

            # 2) Get already loaded sequences so to avoid loading them again
            all_loaded_sequences = []
            with MosaicoClient.connect(
                host=configs["MOSAICO_HOST"],
                port=configs["MOSAICO_PORT"],
                api_key=configs["API_KEY"],
                enable_tls=configs["ENABLE_TLS"],
            ) as client:
                all_loaded_sequences.extend(client.list_sequences())

            filtered_rosbags = [
                bag_pt
                for bag_pt in ros_bag_paths
                if self._get_name_from_rosbag(bag_pt) not in all_loaded_sequences
            ]

            if n_bags_to_load is not None:
                filtered_rosbags = filtered_rosbags[:n_bags_to_load]

            console.print(
                f"[bold green]Loading {len(filtered_rosbags)} from {len(ros_bag_paths)} found bags from {configs['PATH_TO_BAGS']} [/bold green]"
            )

            # 3) Injesting rosbags
            loaded_bags = 0
            for bag_path in filtered_rosbags:
                if not bag_path.is_file():
                    console.print(
                        f"[bold yellow]{bag_path} is not a rosbag file. Skipping injestion[/bold yellow]"
                    )
                    continue

                sequence_name = self._get_name_from_rosbag(bag_path)

                injestor_config = ROSInjectionConfig(
                    file_path=bag_path,
                    sequence_name=sequence_name,
                    metadata=self._get_metadata(dataset_path, sequence_name) or {},
                    host=configs["MOSAICO_HOST"],
                    port=configs["MOSAICO_PORT"],
                    log_level="WARNING",
                    topics=configs["TOPICS_TO_FILTER"],
                    ros_distro=configs["ROS_DISTRO"],
                    on_error=SessionLevelErrorPolicy.Delete,
                    mosaico_api_key=configs["API_KEY"],
                    enable_tls=configs["ENABLE_TLS"],
                    tls_cert_path=configs["TLS_CERT_PATH"],
                )

                console.print(
                    f"[bold green]Starting ROS injestion {injestor_config.sequence_name} - Size (MB): {bag_path.stat().st_size / (1024 * 1024):.2f} - bag number {loaded_bags + 1}/{len(filtered_rosbags)} [/bold green]"
                )

                injestor = RosbagInjector(injestor_config)

                try:
                    injestor.run()
                except Exception as e:
                    console.print(f"[bold red]Injection Failed:[/bold red] {e}")
                    continue

                loaded_bags += 1
                console.print(
                    f"[bold green]Finished ROS injestion {injestor_config.sequence_name} of {loaded_bags}/{len(filtered_rosbags)} [/bold green]"
                )

            console.print(
                Panel(
                    f"[bold green]Finished loading datasets {dataset_path.name}[/bold green]"
                )
            )


if __name__ == "__main__":
    injestor = RosDatasetsInjestor()
    injestor.load_datasets()
