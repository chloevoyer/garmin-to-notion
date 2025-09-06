import os

from dotenv import load_dotenv
from garminconnect import Garmin


def get_garmin_client() -> Garmin:
    load_dotenv()

    # Initialize Garmin and Notion clients using environment variables
    garmin_email = os.getenv("GARMIN_EMAIL")
    garmin_password = os.getenv("GARMIN_PASSWORD")
    garmin_auth_token = os.getenv("GARMIN_AUTH_TOKEN")

    has_basic_auth = bool(garmin_email) and bool(garmin_password)
    has_token_auth = bool(garmin_auth_token)

    if not (has_basic_auth or has_token_auth):
        raise ValueError("Could not find Garmin authentication credentials in environment variables.")

    # Create the client
    garmin_client = Garmin(garmin_email, garmin_password)

    # Authenticate the client
    if has_token_auth:
        print("Using token-based authentication for Garmin Connect.")
        # Could optionally just use the GARMINTOKENS env variable, but used a dedicated one for clarity and flexibility.
        garmin_client.login(tokenstore=garmin_auth_token)
    else:
        print("Using basic authentication for Garmin Connect.")
        garmin_client.login()

    print("Garmin client authenticated successfully.")

    return garmin_client
