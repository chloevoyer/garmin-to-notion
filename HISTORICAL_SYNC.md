# Historical Data Sync

## Overview

This feature allows you to sync your historical Garmin data to Notion when you first set up the integration. It's designed to run **once** after forking the repository to import your existing data.

## What Gets Synced

| Data Type | Default | Description |
|-----------|---------|-------------|
| **Activities** | Last 100 | Workouts, runs, rides, etc. |
| **Daily Steps** | Last 365 days | Step counts and goals |
| **Sleep Data** | Last 365 days | Sleep duration and quality |

## Quick Start

### Option 1: GitHub Actions (Recommended)

1. Fork this repository
2. Set up your secrets (see main README)
3. Go to **Actions** → **Initial Historical Sync**
4. Click **Run workflow**
5. Adjust days/activities if needed
6. Click **Run workflow** button

### Option 2: Run Locally

```bash
# Sync with default settings (90 days, 1000 activities)
python sync_historical_data.py

# Sync more data
python sync_historical_data.py --days 365 --activities 2000
```

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--days` | 365 | Days of steps/sleep to sync |
| `--activities` | 100 | Max activities to sync |

## Example Output

```
==================================================
🚀 GARMIN TO NOTION - HISTORICAL SYNC
==================================================
📅 Days to sync: 365
🏃 Max activities: 100
✅ Logged in to Garmin Connect
✅ Connected to Notion

📊 SYNCING ACTIVITIES
========================================
   Fetching up to 100 activities...
   Found 250 activities
   ✅ Created: 250, Skipped: 0

👣 SYNCING DAILY STEPS
========================================
   Fetching last 365 days...
   Found 365 days of data
   ✅ Created: 365, Skipped: 0

😴 SYNCING SLEEP DATA
========================================
   Fetching last 365 days...
   Found 365 days of data
   ✅ Created: 365, Skipped: 0

==================================================
✅ HISTORICAL SYNC COMPLETED!
==================================================
📊 Total created: 365
⏭️  Total skipped: 0

💡 Use the daily sync workflow for regular updates
```

## After Historical Sync

Once completed, the daily sync workflow (`sync_garmin_to_notion.yml`) will automatically keep your data up to date. It runs daily and only syncs new data.

## Troubleshooting

### Missing Data
- Check if data exists in Garmin Connect
- Some days may have no sleep/step data recorded
- Activities older than your sync range won't be included

### Rate Limiting
- The script includes delays to avoid Garmin API limits
- Large syncs may take several minutes

### Duplicate Entries
- The script checks for existing data before creating entries
- Running multiple times is safe - duplicates are skipped

## Contributing

This feature was added to solve the initial setup problem. Feel free to:
- Report issues with specific activity types
- Suggest improvements to the sync logic
- Add support for additional data types
