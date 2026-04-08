#!/bin/bash
# Overnight runner: wait 50 minutes, then run pipeline + deploy
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$PROJECT_DIR/scripts/overnight.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "Overnight runner started. Waiting 50 minutes before starting pipeline..."
sleep 3000

log "Timer complete. Starting data pipeline..."

cd "$PROJECT_DIR"
source .venv/bin/activate

# Run the pipeline
log "Running Python pipeline..."
python scripts/run_pipeline.py 2>&1 | tee -a "$LOG"

# Copy data to frontend
log "Copying data to web/public/data/..."
./scripts/copy-data.sh 2>&1 | tee -a "$LOG"

# Deploy to Vercel
log "Deploying to Vercel..."
cd "$PROJECT_DIR/web"
vercel deploy --prod --scope jdcodes1s-projects --yes 2>&1 | tee -a "$LOG"

log "Done! Check the Vercel URL above."
