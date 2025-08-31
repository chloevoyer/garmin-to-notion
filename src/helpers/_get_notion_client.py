import os
from dataclasses import dataclass

from notion_client import Client

@dataclass(frozen=True)
class NotionDatabases:
    activities: str
    personal_records: str
    sleep: str
    daily_steps: str


def get_notion_client() -> tuple[Client, NotionDatabases]:
    print("Initializing Notion client...")

    notion_databases = NotionDatabases(
        activities=os.getenv("NOTION_DB_ID"),
        personal_records=os.getenv("NOTION_PR_DB_ID"),
        sleep=os.getenv("NOTION_SLEEP_DB_ID"),
        daily_steps=os.getenv("NOTION_STEPS_DB_ID"),
    )

    notion_token = os.getenv("NOTION_TOKEN")
    notion_client = Client(auth=notion_token)

    print("Notion client initialized.")

    return notion_client, notion_databases