#!/bin/bash
# Copy processed data snapshots from data/ to web/public/data/
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/../data"
DEST="$SCRIPT_DIR/../web/public/data"

if [ ! -d "$SRC" ]; then
  echo "Error: data/ directory not found. Run the notebook first."
  exit 1
fi

mkdir -p "$DEST/manhattan"

cp "$SRC/correlation_matrix.json" "$DEST/"
cp "$SRC/network_graph.json" "$DEST/"
cp "$SRC/metadata.json" "$DEST/"
cp "$SRC/manhattan/"*.json "$DEST/manhattan/"

echo "Data copied to $DEST"
ls -lh "$DEST"
