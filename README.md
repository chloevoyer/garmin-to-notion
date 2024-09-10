# Garmin to Notion Integration
This project connects your Garmin activities and personal records to your Notion database, allowing you to keep track of your performance metrics in one place.

## Features :star:
- Automatically sync Garmin activities to Notion.
- Extract Garmin personal records such as fastest 1K and longest ride.
- Easy setup with clear instructions and minimal coding required.

## Prerequisites
- A Notion account with API access.
- A Garmin Connect account to pull activity data.

## Getting Started
Follow these steps to set up the integration:
### 1. Set Environment Secrets
Ensure that your environment secrets are correctly configured for secure data access.
### 2. Create Notion Token
* Go to [Notion Integrations](https://www.notion.so/profile/integrations).
* [Create](https://developers.notion.com/docs/create-a-notion-integration) a new integration and copy the integration token.
* [Share](https://www.notion.so/help/add-and-manage-connections-with-the-api#enterprise-connection-settings) the integration with the target database in Notion.
### 3. Run Scripts (if not using automatic workflow)
* Run [garmin-activities.py](https://github.com/chloevoyer/garmin-to-notion/blob/main/garmin-activities.py) to sync your Garmin activities to Notion.  
`python garmin-activities.py`
* Run [person-records.py](https://github.com/chloevoyer/garmin-to-notion/blob/main/personal-records.py) to extract activity records (e.g., fastest run, longest ride).  
`python personal-records.py` 
## Example Configuration
You can customize the scripts to fit your needs by modifying environment variables and Notion database settings.

## Acknowledgements
- Reference dictionary and examples can be found in [cyberjunky/python-garminconnect](https://github.com/cyberjunky/python-garminconnect.git).
- This project was inspired by [n-kratz/garmin-notion](https://github.com/n-kratz/garmin-notion.git).
## Contributing
Contributions are welcome! If you find a bug or want to add a feature, feel free to open an issue or submit a pull request. Financial contributions are also greatly appreciated :blush:    

<a href="https://www.buymeacoffee.com/cvoyer" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>   

## License
This project is licensed under the MIT License. See the LICENSE file for more details.


