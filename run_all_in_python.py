import subprocess
import threading
import time
import re
import sys
import traceback
import signal  # Added import for signal handling
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
import json  # Add import for JSON handling

from playwright.sync_api import sync_playwright

class HTTPToolkitClient:
    def __init__(self, url="https://app.httptoolkit.tech"):
        self.url = url

    def launch_and_intercept(self):
        """
        Launch HTTP Toolkit and initiate Android interception using Playwright
        with a fresh, cacheless browser session. Returns a dictionary of
        extracted values.
        """
        with sync_playwright() as p:
            # Create a temporary directory for user data (not used directly since unsupported)
            with tempfile.TemporaryDirectory() as user_data_dir:
                browser = p.chromium.launch(
                    headless=True
                )
                context = browser.new_context()
                
                # Handle dialogs by dismissing them and reloading the page
                def handle_dialog(dialog):
                    dialog.dismiss()
                    dialog.page.reload()
                
                context.on("dialog", handle_dialog)
                
                page = context.new_page()
                try:
                    # Navigate to HTTP Toolkit intercept page
                    print("Navigating to HTTP Toolkit...")
                    page.goto(self.url, wait_until="networkidle")

                    # Wait for and click the Android ADB option
                    print("Looking for Android ADB interceptor...")
                    page.wait_for_selector('h1:text("Android Device via ADB")')
                    page.click('h1:text("Android Device via ADB")')
                    print("Clicked Android ADB interceptor")

                    # Wait for and monitor the count value
                    print("Waiting for count value to change...")
                    max_attempts = 300  # ~30 seconds total
                    attempt = 0
                    
                    while attempt < max_attempts:
                        try:
                            # Look for the count element and get its value
                            count_element = page.locator('.count')
                            current_count = count_element.text_content()
                            
                            # Click the tap coordinates
                            subprocess.run([ADB, 'shell', 'input', 'tap', '1200', '1540'])
                            print(f"Executed tap command, current count: {current_count}")
                            
                            # Wait a shorter time between attempts
                            time.sleep(0.1)
                            
                            # Check if count changed to "2"
                            if current_count != "2":
                                print("Count value reached 2, proceeding...")
                                break
                                
                            attempt += 1
                        except Exception as e:
                            print(f"Error during tap attempt: {e}")
                            attempt += 1

                    if attempt >= max_attempts:
                        raise Exception("Failed to detect count change after maximum attempts")

                    # Type the TikTok device register URL into the filter input
                    print("Typing TikTok device register URL into filter...")
                    page.wait_for_selector('.react-autosuggest__input')
                    page.fill(
                        '.react-autosuggest__input',
                        'https://log16-normal-useast5.tiktokv.us/service/2/device_register/'
                    )

                    # Now that everything is set up, launch TikTok
                    print("HTTP Toolkit setup complete. Opening TikTok app...")
                    time.sleep(5)
                    subprocess.run([ADB, 'shell', 'monkey', '-p', 'com.zhiliaoapp.musically', '1'])
                    print("TikTok app launched.")

                    # Wait for the specific request to appear
                    print("Waiting for successful device register request...")
                    selector = 'div[role="row"]:has-text("/service/2/device_register/"):has(div:text-is("200"))'
                    page.wait_for_selector(selector)
                    print("Found successful device register request!")

                    # Click on the request row
                    page.click(selector)

                    # Wait for the request details to load
                    print("Waiting for request details to load...")
                    page.wait_for_selector('div.view-line:has-text("device_id_str")')
                    page.wait_for_selector('div.view-line:has-text("new_user")')
                    page.wait_for_selector('div.view-line:has-text("install_id_str")')

                    # Extract values using regex
                    print("Extracting values...")

                    def extract_value(key):
                        key_selector = f'div.view-line:has-text("{key}")'
                        text = page.text_content(key_selector)
                        match = re.search(f'"{key}":\\s*"?(\\d+)"?', text)
                        return match.group(1) if match else None

                    values = {
                        'device_id_str': extract_value('device_id_str'),
                        'new_user': int(extract_value('new_user')),
                        'install_id_str': extract_value('install_id_str')
                    }

                    print("\nExtracted values:")
                    print(f"Device ID: {values['device_id_str']}")
                    print(f"New User: {values['new_user']}")
                    print(f"Install ID: {values['install_id_str']}")

                    # Append the extracted values to a JSONL file
                    with open('extracted_values.jsonl', 'a') as jsonl_file:
                        json.dump(values, jsonl_file)
                        jsonl_file.write('\n')

                    return values
                finally:
                    context.close()
                    browser.close()

def wait_for_device_ready(adb_path, timeout=60):
    """
    Repeatedly checks for device readiness with a timeout.
    Returns True if device becomes ready, False if timeout occurs.
    """
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        try:
            # Suppress output by using capture_output=True
            result = subprocess.run(
                [adb_path, 'shell', 'echo', 'Device is ready'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, Exception):
            pass
        time.sleep(0.5)
    return False

def run_npm_start():
    """
    Runs 'npm start' in a non-blocking call (Popen).
    Returns the process object so it can be terminated later.
    """
    proc = subprocess.Popen(["npm", "start"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Start threads to continuously read and print npm output
    def log_output(pipe, prefix):
        for line in iter(pipe.readline, b''):
            print(f"{prefix}: {line.decode().strip()}")
    
    threading.Thread(target=log_output, args=(proc.stdout, "npm stdout"), daemon=True).start()
    threading.Thread(target=log_output, args=(proc.stderr, "npm stderr"), daemon=True).start()
    
    return proc

def kill_npm_proc(npm_proc):
    """
    Attempts to gracefully stop the npm process, escalating signals as needed.
    """
    if not npm_proc or npm_proc.poll() is not None:
        return  # Already stopped or invalid process
    print("Attempting graceful npm termination by sending SIGINT (Ctrl+C)...")
    try:
        npm_proc.send_signal(signal.SIGINT)
        try:
            npm_proc.wait(timeout=5)
            print("npm process terminated gracefully with SIGINT.")
        except subprocess.TimeoutExpired:
            print("npm process didn't terminate gracefully after SIGINT, sending SIGTERM...")
            npm_proc.terminate()
            try:
                npm_proc.wait(timeout=5)
                print("npm process terminated gracefully after SIGTERM.")
            except subprocess.TimeoutExpired:
                print("npm process didn't terminate gracefully after SIGTERM, sending SIGKILL...")
                npm_proc.kill()
                try:
                    npm_proc.wait(timeout=5)
                    print("npm process forcefully killed.")
                except subprocess.TimeoutExpired:
                    print("Warning: npm process seems stuck, trying system-level termination...")
                    if sys.platform == "win32":
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(npm_proc.pid)], capture_output=True)
                    else:
                        subprocess.run(['pkill', '-KILL', '-P', str(npm_proc.pid)], capture_output=True)
    except Exception as e:
        print(f"Error during npm process cleanup: {e}")

def kill_emulator(adb_path):
    """
    Attempts to stop the emulator gracefully, escalating if needed.
    """
    print("Stopping emulator (final cleanup)...")
    try:
        # Try normal emulator kill
        subprocess.run([adb_path, 'emu', 'kill'], timeout=10)

        # Wait and verify emulator is actually stopped
        max_attempts = 10
        for attempt in range(max_attempts):
            result = subprocess.run([adb_path, 'devices'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if not any('emulator' in line for line in result.stdout.decode('utf-8').splitlines()):
                print("Emulator successfully stopped.")
                break
            if attempt < max_attempts - 1:
                print(f"Emulator still running, retry {attempt + 1}/{max_attempts}...")
                time.sleep(2)
                # Try force-stop on subsequent attempts
                subprocess.run([adb_path, 'kill-server'])
                time.sleep(1)
                subprocess.run([adb_path, 'start-server'])
        else:
            print("Warning: Could not verify emulator shutdown!")
    except Exception as e:
        print(f"Failed to kill emulator: {e}")

def home_directory():
    """
    Returns the user's HOME directory in a cross-platform way.
    """
    import os
    return os.path.expanduser('~')

def run_all():
    """
    Main orchestration function
    """
    ANDROID_HOME = f"{sys.argv[1]}" if len(sys.argv) > 1 else f"{home_directory()}/Library/Android/sdk"
    EMULATOR = f"{ANDROID_HOME}/emulator/emulator"
    global ADB
    ADB = f"{ANDROID_HOME}/platform-tools/adb"

    npm_proc = None
    emu_proc1 = None
    emu_proc2 = None

    try:
        # Configure ADB for headless operation
        subprocess.run([ADB, 'start-server'])  # Ensure ADB server is running
        
        print("Starting emulator with wipe data...")
        env = {
            **os.environ,
            'ANDROID_EMULATOR_WAIT_TIME_BEFORE_KILL': '0',
            'ANDROID_AVD_HOME': f"{home_directory()}/.android/avd",  # Explicit AVD path
            'ANDROID_EMU_HEADLESS': '1'  # Enable headless mode
        }
        emu_proc1 = subprocess.Popen(
            [
                EMULATOR, '-no-snapshot', '-wipe-data', '@Pixel_XL_API_31-v2',
                '-no-window',  # Run without a window
                '-no-boot-anim',  # Disable boot animation
                '-no-audio',      # Disable audio
                '-gpu', 'swiftshader_indirect',
                '-no-skin'        # Don't load device skin
            ],
            env=env
        )

        # Wait for device with timeout
        print("Waiting for emulator to start (checking ADB)...")
        if not wait_for_device_ready(ADB, timeout=60):
            raise Exception("Emulator failed to start within timeout")
        print("Emulator is ready.")

        # 3. Root the emulator with timeout
        print("Running rootAVD.sh script to root the emulator...")
        rootavd_proc = subprocess.Popen(
            ['/Users/anirudhrahul/Tiktok-SSL-Pinning-Bypass/rootAVD/rootAVD.sh', 
             'system-images/android-31/google_apis/arm64-v8a/ramdisk.img'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        try:
            rootavd_proc.communicate(input=b"1\n", timeout=30)
        except subprocess.TimeoutExpired:
            rootavd_proc.kill()
            raise Exception("rootAVD script timed out")

        # 4. Kill emulator more aggressively
        print("Stopping emulator after root step...")
        subprocess.run([ADB, 'emu', 'kill'])
        subprocess.run([ADB, 'kill-server'])
        
        # Wait for emulator to stop with shorter timeout
        start_time = time.time()
        while time.time() - start_time < 20:
            result = subprocess.run([ADB, 'devices'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if not any('emulator' in line for line in result.stdout.decode('utf-8').splitlines()):
                break
            time.sleep(0.5)

        # 5. Restart emulator
        print("Restarting emulator (no-snapshot)...")
        emu_proc2 = subprocess.Popen(
            [
                EMULATOR, '-no-snapshot', '@Pixel_XL_API_31-v2',
                '-no-window',     # Run without a window
                '-no-boot-anim',
                '-no-audio',
                '-gpu', 'swiftshader_indirect',
                '-no-skin'        # Don't load device skin
            ],
            env=env
        )

        # Wait for restart with timeout
        print("Waiting for emulator to restart...")
        if not wait_for_device_ready(ADB, timeout=60):
            raise Exception("Emulator failed to restart within timeout")
        print("Emulator restarted & ready.")

        # 6. Install TikTok APK
        print("Installing TikTok APK...")
        while True:
            install_proc = subprocess.run([ADB, 'install', 'tiktok-v30.1.2.apk'],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if install_proc.returncode == 0:
                break
            time.sleep(1)
        print("TikTok installation complete.")

        # 7. Launch Playwright interception
        print("Launching Playwright interception...")
        client = HTTPToolkitClient()
        result = client.launch_and_intercept()
        
        if result:
            print(f"\nSuccessful extraction:")
            print(f"Device ID: {result['device_id_str']}")
            print(f"New User: {result['new_user']}")
            print(f"Install ID: {result['install_id_str']}")
        else:
            print("\nFailed to extract values.")

    except Exception as e:
        print(f"Error in run_all: {e}")
        raise  # Re-raise the exception to be caught by the outer try-catch

    finally:
        print("\nInitiating cleanup of background processes...")
        
        # First kill npm process
        # if npm_proc:
        #     kill_npm_proc(npm_proc)
            
        # Then kill ADB and emulator processes
        try:
            # Kill ADB server first
            subprocess.run([ADB, 'kill-server'], timeout=10)
            
            # Kill any remaining emulator processes
            kill_emulator(ADB)
            
            # Force kill any remaining emulator processes
            if emu_proc1 and emu_proc1.poll() is None:
                emu_proc1.kill()
            if emu_proc2 and emu_proc2.poll() is None:
                emu_proc2.kill()
                
            # Additional cleanup for any stray emulator processes
            if sys.platform == "win32":
                subprocess.run('taskkill /F /IM emulator.exe', shell=True, capture_output=True)
            else:
                subprocess.run('pkill -9 emulator', shell=True, capture_output=True)
                
        except Exception as cleanup_error:
            print(f"Error during cleanup: {cleanup_error}")

        print("Cleanup complete.")


if __name__ == "__main__":
    """
    Usage (if you have a custom Android SDK path):
       python run_all_in_python.py /path/to/android/sdk
    If you omit the path, it defaults to ~/Library/Android/sdk (common on macOS).
    """
    try:
        run_all()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error in run_all: {e}")
        traceback.print_exc()
        sys.exit(1) 