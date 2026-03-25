import os
import garminconnect

email = os.environ["GARMIN_EMAIL"]
password = os.environ["GARMIN_PASSWORD"]

client = garminconnect.Garmin(email, password)
client.login()

# Save the session tokens to a local directory
client.garth.dump("~/.garth")
print("Login successful, session saved.")
