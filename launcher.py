import os
import sys
import time
import subprocess
import json
from pathlib import Path

SRC_DIR = Path(__file__).parent / 'src'
STATE_FILE = Path(__file__).parent / '.dev_state.json'
WATCHED_EXTENSIONS = ['.py']


def get_mtimes():
    mtimes = {}
    for path in SRC_DIR.rglob('*'):
        if path.suffix in WATCHED_EXTENSIONS:
            mtimes[str(path)] = path.stat().st_mtime
    return mtimes

def main():
    python_exe = sys.executable
    main_py = str(SRC_DIR / 'main.py')
    process = subprocess.Popen([python_exe, main_py])
    last_mtimes = get_mtimes()
    print('Development mode: watching for changes...')
    try:
        while True:
            time.sleep(1)
            new_mtimes = get_mtimes()
            if new_mtimes != last_mtimes:
                print('Change detected. Reloading...')

                process.terminate()
                process.wait()

                process = subprocess.Popen([python_exe, main_py])
                last_mtimes = new_mtimes

    except KeyboardInterrupt:
        print('Stopping development mode.')
        process.terminate()
        process.wait()

if __name__ == '__main__':
    main()
