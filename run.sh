#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -f venv/bin/activate ]; then
    echo "Creating virtual environment..."
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv venv
    else
        python -m venv venv
    fi
    # shellcheck disable=SC1091
    source venv/bin/activate
    echo "Installing dependencies..."
    python -m pip install --upgrade pip
    pip install -r requirements.txt
else
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

python -m reeview
