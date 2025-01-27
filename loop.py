import subprocess
import time
import os

PORT = 45456

while True:
    try:
        # Run the main process
        process = subprocess.run(['python3', 'run_all_in_python.py'])
    except subprocess.CalledProcessError:
        # This happens if no process is using the port, which is fine
        pass
    time.sleep(1)