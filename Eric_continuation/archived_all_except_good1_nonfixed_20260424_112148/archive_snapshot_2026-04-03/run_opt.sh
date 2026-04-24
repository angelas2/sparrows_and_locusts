#!/bin/bash
while true; do
  python3 famine_model.py
  if [ $? -eq 0 ]; then
    echo "Target R2 reached. Exiting loop."
    break
  else
    echo "Target not met. Cursor, analyze the logs and FIX the bounds in famine_model.py now."
    # This empty line and echo triggers the Agent's "Observer" 
    sleep 2
  fi
done