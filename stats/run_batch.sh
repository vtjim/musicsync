#!/bin/bash
# run_batch.sh <log> <id> <spec> [<id> <spec> ...] : runs run_show.sh on each pair sequentially.
log=$1; shift
while [ $# -ge 2 ]; do echo "##### $1"; ~/dev/musicsync/stats/run_show.sh "$1" "$2" || echo "STOPPED on $1"; shift 2; done > "$log" 2>&1
echo BATCH_FINISHED >> "$log"
