[![Sync Garmin to Notion](https://github.com/chloevoyer/garmin-to-notion/actions/workflows/sync_garmin_to_notion.yml/badge.svg?branch=main)](https://github.com/chloevoyer/garmin-to-notion/actions/workflows/sync_garmin_to_notion.yml)

> **Status: Archived / No longer maintained**  
> This repository is archived and read-only. I am no longer maintaining it, reviewing issues, or accepting pull requests.

# Garmin to Notion Integration :watch:

This project connects your Garmin activities and personal records to your Notion database, allowing you to keep track of your performance metrics in one place.

> [!IMPORTANT]
> **Existing users:** Garmin tightened their authentication in March 2025, breaking the previous email/password login flow. You will need to sync your fork with the latest changes and migrate to the new token-based authentication. See [README_AUTH_SETUP.md](README_AUTH_SETUP.md) for instructions. Your `GARMIN_EMAIL` and `GARMIN_PASSWORD` secrets can be removed once done.

## Features :sparkles:  
  🔄  Automatically sync Garmin activities to Notion in real-time  
  📊  Track detailed activity metrics (distance, pace, heart rate)  
  🎯  Extract and track personal records (fastest 1K, longest ride)  
  👣  Optional daily steps tracker
  😴  Optional sleep data tracker  
  🤖  Zero-touch automation once configured  
  📱  Compatible with all Garmin activities and devices  
  🔧  Easy setup with clear instructions and minimal coding required  

## Prerequisites :hammer_and_wrench:  
- A Notion account with API access.
- A Garmin Connect account to pull activity data.
- If you wish to sync your Peloton workouts with Garmin, see [peloton-to-garmin](https://github.com/philosowaffle/peloton-to-garmin)
## Getting Started :dart:
A detailed step-by-step guide is provided on my Notion template [here](https://chloevoyer.notion.site/Set-up-Guide-17915ce7058880559a3ac9f8a0720046).
For more advanced users, follow these steps to set up the integration:
### 1. Fork this GitHub Repository
### 2. Duplicate my [Notion Template](https://www.notion.so/templates/fitness-tracker-738)
* Save your Activities and Personal Records database ID (you will need it for step 4)
  * Optional: Daily Steps database ID
  * Look at the URL: notion.so/username/[string-of-characters]
  * The database ID is everything after your “username/“ and before the “?v”
### 3. Create Notion Token
* Go to [Notion Integrations](https://www.notion.so/profile/integrations).
* [Create](https://developers.notion.com/docs/create-a-notion-integration) a new integration and copy the integration token.
* [Share](https://www.notion.so/help/add-and-manage-connections-with-the-api#enterprise-connection-settings) the integration with the target database in Notion.

### 4. Generate a Garmin Authentication Token
* Follow the instructions in [README_AUTH_SETUP.md](README_AUTH_SETUP.md) to generate and configure your `GARMIN_AUTH_TOKEN`.

### 5. Set Environment Secrets
* Environment secrets to define:
  * GARMIN_AUTH_TOKEN (see step 4)
  * NOTION_TOKEN
  * NOTION_DB_ID
  * NOTION_PR_DB_ID
  * NOTION_STEPS_DB_ID (optional)
  * NOTION_SLEEP_DB_ID (optional)
### 6. Run Scripts (if not using automatic workflow)
* Run [garmin-activities.py](https://github.com/chloevoyer/garmin-to-notion/blob/main/garmin-activities.py) to sync your Garmin activities to Notion.  
`python garmin-activities.py`
* Run [person-records.py](https://github.com/chloevoyer/garmin-to-notion/blob/main/personal-records.py) to extract activity records (e.g., fastest run, longest ride).  
`python personal-records.py` 
## Example Configuration :pencil:  
You can customize the scripts to fit your needs by modifying environment variables and Notion database settings.  

Here is a screenshot of what my Notion dashboard looks like:  
![garmin-to-notion-template](https://github.com/user-attachments/assets/b37077cc-fe87-466f-9424-8ba9e4efa909)


My Notion template is available for free and can be duplicated to your Notion [here](https://www.notion.so/templates/fitness-tracker-738)

## Acknowledgements :raised_hands:  
- Reference dictionary and examples can be found in [cyberjunky/python-garminconnect](https://github.com/cyberjunky/python-garminconnect.git).
- This project was inspired by [n-kratz/garmin-notion](https://github.com/n-kratz/garmin-notion.git).
## Contributing :handshake:   
Contributions are welcome! If you find a bug or want to add a feature, feel free to open an issue or submit a pull request. Financial contributions are also greatly appreciated :blush:    

<a href="https://www.buymeacoffee.com/cvoyer" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>   

## :copyright: License  
This project is licensed under the MIT License. See the LICENSE file for more details.
