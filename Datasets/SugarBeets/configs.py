from rosbags.typesys import Stores
from pathlib import Path

PATH_TO_BAGS = Path.home() / "rosbags/SugarBeets"
ROS_DISTRO = Stores.ROS1_NOETIC
TOPICS_TO_FILTER = [
    "/camera/*",
    "/gps/*",
    "!/gps/leica/time_reference",
    "/laser/fx8/points",
    "/odometry/*",
]
