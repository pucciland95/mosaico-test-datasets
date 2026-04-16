from rosbags.typesys import Stores
from pathlib import Path

PATH_TO_BAGS = Path.home() / "rosbags/Autoware"
ROS_DISTRO = Stores.ROS2_JAZZY
TOPICS_TO_FILTER = [
    "/applanix/*",
    "!/applanix/lvx_client/autoware_orientation",
    "/localization/twist_estimator/twist_with_covariance",
    "/pandar_points",
    "/tf_static",
]
