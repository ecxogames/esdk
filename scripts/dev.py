import os
import time
import subprocess
import sys

# Directories and files to watch for changes
WATCH_PATHS = ['engine', 'server', 'ui', 'properties.config', 'CMakeLists.txt']
BUILD_CMD = ['cmake', '--build', 'build']

def get_exe_path():
    """Find the compiled executable based on OS and CMake generator type."""
    bases = [
        os.path.join('build', 'Debug', 'ESDEngine.exe'),
        os.path.join('build', 'Release', 'ESDEngine.exe'),
        os.path.join('build', 'ESDEngine.exe'),
        os.path.join('build', 'ESDEngine')
    ]
    for b in bases:
        if os.path.exists(b):
            return b
    return None

def get_latest_mtime():
    """Scan all tracked files and return the most recent modification timestamp."""
    max_ts = 0
    for path in WATCH_PATHS:
        if not os.path.exists(path):
            continue
        if os.path.isfile(path):
            max_ts = max(max_ts, os.path.getmtime(path))
        else:
            for root, _, files in os.walk(path):
                for f in files:
                    try:
                        filepath = os.path.join(root, f)
                        max_ts = max(max_ts, os.path.getmtime(filepath))
                    except FileNotFoundError:
                        pass
    return max_ts

def start_app():
    """Builds the project and launches the executable."""
    print("[Dev] Building project...")
    result = subprocess.run(BUILD_CMD)
    if result.returncode != 0:
        print("[Dev] Build failed. Waiting for changes to try again...")
        return None
    
    exe = get_exe_path()
    if not exe:
        print("[Dev] Could not find compiled executable. Waiting for changes...")
        return None
        
    print(f"[Dev] Starting {exe}...")
    # Launch the executable
    return subprocess.Popen([exe])

def main():
    print("[Dev] Starting live development watcher...")
    print(f"[Dev] Watching for changes in: {', '.join(WATCH_PATHS)}")
    
    last_mtime = get_latest_mtime()
    app_process = start_app()
    
    try:
        while True:
            time.sleep(1) # Poll interval
            current_mtime = get_latest_mtime()
            
            # If modification timestamp updated
            if current_mtime > last_mtime:
                print("\n[Dev] Detected file changes! Restarting...")
                last_mtime = current_mtime
                
                # Terminate running app gracefully
                if app_process and app_process.poll() is None:
                    app_process.terminate()
                    app_process.wait()
                    
                # Rebuild and restart
                app_process = start_app()
                
    except KeyboardInterrupt:
        print("\n[Dev] Shutting down watcher...")
        if app_process and app_process.poll() is None:
            app_process.terminate()
            app_process.wait()
        sys.exit(0)

if __name__ == '__main__':
    main()