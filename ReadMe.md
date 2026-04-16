# Mosaico Test Datasets

A collection of scripts that download publicly available ROS bag datasets and
inject them into a running [Mosaico](https://mosaico.dev) instance. The
primary use-case is validating that the Mosaico platform correctly ingests a
variety of real-world sensor recordings (LiDAR, cameras, GPS, IMU, …) from
different ROS distributions and robot platforms.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running Mosaico Locally](#running-mosaico-locally)
- [Loading Datasets](#loading-datasets)
- [Adding a New Dataset](#adding-a-new-dataset)

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.13 |
| [Poetry](https://python-poetry.org/docs/#installation) | ≥ 2.0 |
| Docker + Docker Compose | any recent version |

---

## Project Structure

```
mosaico-test-datasets/
├── Datasets/
│   ├── configs.py              # Global default configuration
│   ├── cli.py                  # CLI entry-point (click)
│   ├── ros_datasets_injestor.py
│   ├── Autoware/
│   │   └── configs.py          # Autoware-specific overrides
│   ├── SugarBeets/
│   │   ├── configs.py
│   │   └── download_ijrr_sugar_beet_2016_rosbag_data.sh
│   └── UZH_FPV/
│       ├── configs.py
│       └── download_uzh_fpv.sh
├── Docker/
│   └── compose.mosaico.yml     # Local Mosaico stack
├── pyproject.toml
└── poetry.toml
```

---

## Installation

Install all Python dependencies with Poetry. No local Mosaico source checkout
is required — the `mosaicolabs` package is pulled from PyPI automatically.

```bash
# 1. Clone the repository
git clone <repo-url>
cd mosaico-test-datasets

# 2. Install dependencies (Poetry creates a .venv inside the project)
poetry install
```

---

## Running Mosaico Locally

The injector scripts expect a Mosaico server to be reachable. A ready-made
Docker Compose file is provided under `Docker/`.

```bash
# Start the Mosaico stack (Postgres + mosaicod daemon)
docker compose -f Docker/compose.mosaico.yml up -d

# Verify the daemon is listening on port 6726
curl http://localhost:6726
```

The default configuration in `Datasets/configs.py` already points to
`localhost:6726`, so no extra setup is needed for a local run.

> **Note** — Before ingesting a dataset make sure the rosbag files are present
> on disk at the path configured in the dataset's `configs.py`
> (see [`PATH_TO_BAGS`](#configuration-keys)). Each dataset folder that ships
> a download script can be used to fetch the bags automatically, e.g.:
>
> ```bash
> bash Datasets/UZH_FPV/download_uzh_fpv.sh
> bash Datasets/SugarBeets/download_ijrr_sugar_beet_2016_rosbag_data.sh
> ```

---

## Loading Datasets

The CLI entry-point is registered by Poetry as
`mosaicolabs.datasets.injest_rosbags`. Run it through `poetry run`:

```bash
# Show all available options
poetry run mosaicolabs.datasets.injest_rosbags --help

# Inject a single dataset
poetry run mosaicolabs.datasets.injest_rosbags --autoware
poetry run mosaicolabs.datasets.injest_rosbags --sugarbeets
poetry run mosaicolabs.datasets.injest_rosbags --uzh_fpv

# Inject all datasets in one go
poetry run mosaicolabs.datasets.injest_rosbags --load_all
```

Multiple flags can be combined:

```bash
poetry run mosaicolabs.datasets.injest_rosbags --autoware --sugarbeets
```

### Configuration Keys

Every dataset is configured through a `configs.py` file. The following keys
are recognised:

| Key | Description | Default |
|---|---|---|
| `MOSAICO_HOST` | Hostname of the Mosaico daemon | `localhost` |
| `MOSAICO_PORT` | Port of the Mosaico daemon | `6726` |
| `PATH_TO_BAGS` | Absolute path to the directory containing the rosbags | `""` |
| `ROS_DISTRO` | `rosbags` store type (e.g. `Stores.ROS2_JAZZY`) | `None` |
| `TOPICS_TO_FILTER` | List of topic patterns to include/exclude (`!` prefix to exclude) | `None` (all topics) |
| `API_KEY` | Mosaico API key for authenticated instances | `None` |
| `TLS_CERT_PATH` | Path to a TLS certificate for encrypted connections | `None` |

Global defaults live in `Datasets/configs.py`. Any key defined in a
dataset-level `configs.py` overrides the corresponding global value.

---

## Adding a New Dataset

Follow these steps to register a new ROS bag dataset.

### 1. Create the dataset folder

Create a new sub-directory under `Datasets/` whose name will be used as the
dataset identifier. The folder **must** contain a `configs.py` file (even if
empty).

```
Datasets/
└── MyDataset/
    └── configs.py
```

### 2. Configure the dataset

Edit `Datasets/MyDataset/configs.py` and set at least `PATH_TO_BAGS` and
`ROS_DISTRO`. Take `Datasets/Autoware/configs.py` as a reference:

```python
from rosbags.typesys import Stores
from pathlib import Path

PATH_TO_BAGS = Path.home() / "rosbags/MyDataset"
ROS_DISTRO   = Stores.ROS2_JAZZY   # or Stores.ROS1_NOETIC, etc.

# Optional: restrict which topics are injected.
# Prefix a pattern with '!' to exclude it.
TOPICS_TO_FILTER = [
    "/sensors/lidar/points",
    "/sensors/camera/*",
    "!/sensors/camera/raw",
]
```

Only the keys you define will override the global defaults; the rest inherit
from `Datasets/configs.py`.

### 3. Register the dataset in the CLI

Open `Datasets/cli.py` and make the following two changes:

**a) Add an entry to `AVAILABLE_DATASET_MAP`** — the key is the CLI flag name
(lowercase, underscores), the value is the exact folder name:

```python
AVAILABLE_DATASET_MAP = {
    "autoware":   "Autoware",
    "sugarbeets": "SugarBeets",
    "uzh_fpv":    "UZH_FPV",
    "mydataset":  "MyDataset",   # <-- add this
}
```

**b) Add a `@click.option` flag** and handle it inside `run_dataset_injestor`:

```python
@click.option("--mydataset", is_flag=True, help="Loads the MyDataset dataset.")
def run_dataset_injestor(autoware, sugarbeets, uzh_fpv, mydataset, load_all):
    ...
    if mydataset:
        datasets_to_load.append(AVAILABLE_DATASET_MAP["mydataset"])
```

### 4. (Optional) Add a download script

If the bags are publicly available, add a shell script to the dataset folder
so other contributors can fetch them easily:

```
Datasets/MyDataset/download_mydataset.sh
```

See `Datasets/UZH_FPV/download_uzh_fpv.sh` for an example that uses `wget`
with resume support and a success/failure summary.

### 5. Verify the setup

```bash
# Check the new dataset appears in --help
poetry run mosaicolabs.datasets.injest_rosbags --help

# Run a dry-run by pointing PATH_TO_BAGS at a folder with at least one bag
poetry run mosaicolabs.datasets.injest_rosbags --mydataset
```
