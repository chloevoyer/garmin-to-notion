from datetime import date, timedelta
from garminconnect import Garmin
from notion_client import Client
from dotenv import load_dotenv
import os

class GarminConnector:
    def __init__(self):
        load_dotenv()
        
        # Initialize configuration from environment variables
        self.garmin_email = os.getenv("GARMIN_EMAIL")
        self.garmin_password = os.getenv("GARMIN_PASSWORD")
        self.garmin_token_store = os.getenv("GARMIN_TOKEN_STORE", "~/.garmin_tokens")
        self.mfa_enabled = os.getenv("GARMIN_MFA_ENABLED", "false").lower() == "true"
        
        # Initialize Garmin client
        self.garmin = Garmin(self.garmin_email, self.garmin_password)
    
    def login(self, mfa_code=None):
        """
        Login to Garmin Connect with support for 2FA
        
        Args:
            mfa_code: Optional MFA code if using non-interactive mode
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            # Try to login using token store if available
            token_store = os.path.expanduser(self.garmin_token_store)
            
            # Check if token store exists
            if os.path.exists(token_store):
                print(f"Found existing token store at {token_store}")
                # Use existing tokens
                self.garmin.login(tokenstore=token_store)
                print("Login successful using stored tokens")
                return True
            
            # No token store, need a fresh login
            print("No stored tokens found, performing a fresh login")
            
            if self.mfa_enabled and mfa_code:
                # Non-interactive 2FA flow with provided MFA code
                print("Using provided MFA code for authentication")
                client_state, _ = self.garmin.login(return_on_mfa=True)
                if client_state == "needs_mfa":
                    # Resume login with the MFA code
                    self.garmin.resume_login(client_state, mfa_code)
                    print("MFA authentication successful")
                else:
                    print("MFA was expected but not requested by Garmin")
            else:
                # Regular login (interactive 2FA if enabled on the account)
                self.garmin.login()
                print("Login successful")
            
            # Save tokens for future use
            if not os.path.exists(os.path.dirname(token_store)):
                os.makedirs(os.path.dirname(token_store))
            
            # If we have tokens, save them
            if hasattr(self.garmin, 'garth') and self.garmin.garth:
                self.garmin.garth.save(token_store)
                print(f"Saved authentication tokens to {token_store}")
            
            return True
            
        except Exception as e:
            print(f"Error during login: {e}")
            return False

def main():
    # Example usage
    connector = GarminConnector()
    
    # If you're running this as a scheduled task and 2FA is enabled,
    # you'll need to provide the MFA code somehow
    # For example, you might store it temporarily in an environment variable
    mfa_code = os.getenv("GARMIN_MFA_CODE")
    
    success = connector.login(mfa_code)
    
    if success:
        print("Garmin Connect login successful!")
        # Now you can use connector.garmin to access Garmin data
        # For example:
        daily_steps = connector.garmin.get_daily_steps(date.today().isoformat(), date.today().isoformat())
        print(f"Steps today: {daily_steps}")
    else:
        print("Failed to login to Garmin Connect")

if __name__ == "__main__":
    main()
