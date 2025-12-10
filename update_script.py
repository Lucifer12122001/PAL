import requests
import sys
import os
import time


MAIN_SCRIPT_NAME = "pal_assistant_final.py"


# !!! ACTION REQUIRED: This URL MUST point to the raw, latest version of your code !!!
# Example: a direct link to the raw content of your GitHub Gist or repository file.
UPDATE_URL = "https://example.com/raw/latest/pal_assistant_final.py" 


def perform_update():
    """Downloads the latest version and replaces the current file."""
    try:
        print(f"[{MAIN_SCRIPT_NAME}]: Initiating download of new version...")
        
        # 1. Download the new code
        response = requests.get(UPDATE_URL, allow_redirects=True, timeout=10)
        response.raise_for_status() 
        new_code = response.content


        # 2. Write the new code to the main script file, replacing the old one
        with open(MAIN_SCRIPT_NAME, 'wb') as f:
            f.write(new_code)
            
        print(f"[{MAIN_SCRIPT_NAME}]: Update file successful. Proceeding to restart.")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"[{MAIN_SCRIPT_NAME}]: ERROR - Could not download update. Check UPDATE_URL. Error: {e}")
        return False
    except IOError as e:
        print(f"[{MAIN_SCRIPT_NAME}]: ERROR - Could not write to file. Check permissions. Error: {e}")
        return False




def restart_pal():
    """Stops the current process and executes a new process."""
    print(f"[{MAIN_SCRIPT_NAME}]: Stopping current P.A.L. instance...")
    time.sleep(2) # Wait briefly to ensure file is closed/flushed
    
    # os.execl replaces the current process with a new one, inheriting the arguments (sys.argv)
    # This is the cleanest way to restart a Python script.
    os.execl(sys.executable, sys.executable, *sys.argv)
    
    # Execution stops here, and the new process starts.


if __name__ == '__main__':
    if perform_update():
        restart_pal()
    else:
        sys.exit(1)