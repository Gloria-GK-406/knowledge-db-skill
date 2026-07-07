#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python_script="$script_dir/kb.py"

if [ ! -f "$python_script" ]; then
    echo "Cannot find kb.py beside kb.sh: $python_script" >&2
    exit 127
fi

if [ -n "${KB_PYTHON:-}" ]; then
    exec "$KB_PYTHON" "$python_script" "$@"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 "$python_script" "$@"
fi

if command -v python >/dev/null 2>&1; then
    exec python "$python_script" "$@"
fi

echo "No Python interpreter found. Set KB_PYTHON to the Python executable path." >&2
exit 127
