#!/bin/bash
# Samples GPU utilisation and host memory every 5 s until the file STOP appears next to the log.
# usage: sample_gpu.sh <log file>
log=$1
while [ ! -e "$(dirname "$log")/STOP" ]; do
  echo "$(date +%T) $(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader) | $(nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv,noheader | tr '\n' ';') | used_GB=$(free -g | awk '/Mem:/{print $3}') avail_GB=$(free -g | awk '/Mem:/{print $7}')" >> "$log"
  sleep 5
done
