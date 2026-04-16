#!/usr/bin/env bash
# download_ijrr_sugar_beet_2016.sh
# Downloads the IJRR Sugar Beet 2016 rosbag dataset.
#
# Usage: ./download_ijrr_sugar_beet_2016.sh [dest_dir]
#
# dest_dir: optional path where bags will be saved.
#           Defaults to ${HOME}/rosbags/SugarBeet-2016

set -euo pipefail

DEST_DIR="${1:-${HOME}/rosbags/SugarBeet-2016}"

METADATA_DIR="$(cd "$(dirname "$0")"; pwd)/metadata"
SERVER="http://www.ipb.uni-bonn.de/datasets_IJRR2017/rosbags"

DAYS=(
    160420 160421 160422 160425 160426 160427 160428 160429
    160502 160503 160504 160505 160506 160509 160510 160511
    160512 160513 160517 160518 160519 160523 160527 160531
    160606 160610 160614
)

mkdir -p "${DEST_DIR}"
echo "Destination : ${DEST_DIR}"
echo "-------------------------------------------"

FAILED=()

for day in "${DAYS[@]}"; do
    day_chunks_list="${METADATA_DIR}/${day}.txt"
    day_dir="${DEST_DIR}/${day}"
    mkdir -p "${day_dir}"

    while read -r chunk || [[ -n "${chunk}" ]]; do
        dest_file="${day_dir}/${chunk}.bag"

        if [[ -f "${dest_file}" ]]; then
            echo "[SKIP]  ${day}/${chunk}.bag (already exists)"
            continue
        fi

        url="${SERVER}/${day}/${chunk}.bag"
        echo "[GET]   ${url}"
        if wget \
            --continue \
            --show-progress \
            --progress=bar:force \
            --no-check-certificate \
            --output-document="${dest_file}" \
            "${url}"; then
            echo "[OK]    ${dest_file}"
        else
            echo "[FAIL]  ${url}" >&2
            FAILED+=("${url}")
            rm -f "${dest_file}"
        fi
        echo ""

    done < "${day_chunks_list}"
done

echo "==========================================="
if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo "Some downloads failed:"
    for f in "${FAILED[@]}"; do echo "  - ${f}"; done
    exit 1
else
    echo "All downloads completed successfully."
fi