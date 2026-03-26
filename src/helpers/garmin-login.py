import os
import time
from pathlib import Path
from dotenv import load_dotenv
import garminconnect

load_dotenv()

email = os.environ["GARMIN_EMAIL"]
password = os.environ["GARMIN_PASSWORD"]
token_path = os.path.expanduser("~/.garth")


def login_and_save(client):
    for attempt in range(3):
        try:
            client.login()
            client.garth.dump(token_path)
            print("Login successful, session cached.")
            break
        except Exception as e:
            if attempt < 2:
                print(f"Login attempt {attempt + 1} failed, retrying in 30s...")
                time.sleep(30)
            else:
                raise


client = garminconnect.Garmin(email, password)

if Path(token_path).exists():
    try:
        client.garth.load(token_path)
        client.get_full_name()  # Quick test to verify token is still valid
        print("Loaded cached Garmin session.")
    except Exception:
        print("Cached session expired, logging in again...")
        login_and_save(client)
else:
    print("No cached session found, logging in...")
    login_and_save(client)
