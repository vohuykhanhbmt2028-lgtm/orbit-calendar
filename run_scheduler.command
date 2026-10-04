#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python scheduler.py
echo ""
echo "Press any key to close..."
read -n 1