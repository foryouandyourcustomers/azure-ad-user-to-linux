#!/bin/bash

#
# wrapper script to ensure venv is used when the script
# is executed
#

SCRIPT_DIR="$(/usr/bin/dirname "$0")"
SCRIPT="${SCRIPT_DIR}/azure-ad-users-to-linux.py"
[ ! -d "${SCRIPT_DIR}/venv" ] && echo "virtual env not found. aborting." && exit 1
[ ! -f "${SCRIPT}" ] && echo "script ${SCRIPT} not found. aborting." && exit 1

exec "${SCRIPT_DIR}/venv/bin/python3" "${SCRIPT}" "$@"