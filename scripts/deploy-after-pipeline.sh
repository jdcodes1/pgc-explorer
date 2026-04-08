#!/bin/bash
# Wait for pipeline to finish, then copy data and deploy
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$PROJECT_DIR/scripts/deploy.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

# Wait for pipeline to finish
log "Waiting for pipeline (run_pipeline.py) to finish..."
while pgrep -f "run_pipeline.py" > /dev/null 2>&1; do
    sleep 30
done

log "Pipeline finished. Checking results..."

# Check if data was generated
if [ ! -f "$PROJECT_DIR/data/correlation_matrix.json" ]; then
    log "ERROR: No data generated. Check overnight.log for errors."
    exit 1
fi

log "Data generated successfully."

# Copy data to frontend
log "Copying data to web/public/data/..."
cd "$PROJECT_DIR"
./scripts/copy-data.sh 2>&1 | tee -a "$LOG"

# Deploy to Vercel
log "Deploying to Vercel..."
cd "$PROJECT_DIR/web"
DEPLOY_URL=$(vercel deploy --prod --scope jdcodes1s-projects --yes 2>&1 | tee -a "$LOG" | grep -o 'https://[^ ]*')

log "Deployed to: $DEPLOY_URL"
log "Done!"
