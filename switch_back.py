import os
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_USER_ID = os.getenv('SLACK_USER_ID')

client = WebClient(token=SLACK_BOT_TOKEN)

def load_last_active_channel():
    try:
        with open('last_active_channel.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def switch_back_to_last_channel():
    last_active_channel = load_last_active_channel()
    last_channel = last_active_channel.get(SLACK_USER_ID)
    if last_channel:
        try:
            client.conversations_join(channel=last_channel)
            print(f"Switched back to the last channel: <#{last_channel}>")
        except SlackApiError as e:
            print(f"Error switching back to the last channel: {e.response['error']}")
    else:
        print("No last channel found.")

if __name__ == "__main__":
    switch_back_to_last_channel()
