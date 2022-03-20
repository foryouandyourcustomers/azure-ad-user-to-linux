#!/bin/bash

#
# wrapper script to ensure venv is used when the script
# is executed
#

SCRIPT_DIR="$(/usr/bin/dirname "$0")"
[ ! -d "${SCRIPT_DIR}/venv" ] && echo "virtual env not found. aborting." && exit 1
[ ! -f "${SCRIPT_DIR}/azure-ad-user-to-linux.py" ] && echo "script azure-ad-user-to-linux.py not found. aborting." && exit 1

"${SCRIPT_DIR}/venv/bin/python3" "${SCRIPT_DIR}/azure-ad-user-to-linux.py" "$@"