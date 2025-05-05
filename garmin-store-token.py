#!/usr/bin/env python3
"""
Garmin Connect Token Generator

This script handles the Garmin Connect login process, including 2FA if enabled,
and saves the authentication tokens for future use. Run this script manually
when you need to generate new tokens (they last for about a year).

Usage:
  python garmin_store_token.py

Environment variables:
  GARMIN_EMAIL - Your Garmin Connect email
  GARMIN_PASSWORD - Your Garmin Connect password
  GARMIN_TOKEN_STORE - Path to store the tokens (default: ~/.garmin_tokens) 735891
"""

import os
import sys
from getpass import getpass
from pathlib import Path
import garth
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Get credentials (either from environment or prompt)
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    token_store = os.getenv("GARMIN_TOKEN_STORE", "~/.garmin_tokens")
    token_store = os.path.expanduser(token_store)
    
    if not email:
        email = input("Enter Garmin Connect email: ")
    if not password:
        password = getpass("Enter Garmin Connect password: ")
    
    # Make sure token store directory exists
    token_dir = os.path.dirname(token_store)
    if token_dir and not os.path.exists(token_dir):
        os.makedirs(token_dir)
    
    print(f"Attempting to log in to Garmin Connect as {email}")
    
    try:
        # First try the normal login which will prompt for MFA code if needed
        result = garth.login(email, password)
        garth.save(token_store)
        print(f"Login successful! Tokens saved to {token_store}")
        print("These tokens should be valid for approximately 1 year.")
        return 0
    except Exception as e:
        # If the normal login fails, try the two-step approach
        print(f"Standard login failed: {e}")
        print("Trying manual 2FA flow...")
        
        try:
            # Step 1: Request MFA
            result = garth.login(email, password, return_on_mfa=True)
            
            if isinstance(result, tuple) and result[0] == "needs_mfa":
                print("\nYour account requires 2FA authentication.")
                mfa_code = input("Enter the MFA code from your authenticator app: ")
                
                # Step 2: Complete login with MFA code
                client_state = result[1]
                garth.resume_login(client_state, mfa_code)
                garth.save(token_store)
                print(f"2FA login successful! Tokens saved to {token_store}")
                print("These tokens should be valid for approximately 1 year.")
                return 0
            else:
                print("Unexpected response during login")
                return 1
        except Exception as e:
            print(f"Error during 2FA login: {e}")
            return 1

if __name__ == "__main__":
    sys.exit(main())
