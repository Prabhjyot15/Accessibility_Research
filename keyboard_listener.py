import os
import json
import subprocess
from pynput import keyboard
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load environment variables from a .env file
load_dotenv()

BATCH_FILE_PATH = os.getenv('BATCH_FILE_PATH')
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
TEAM_ID=os.getenv('TEAM_ID')
SLACK_USER_ID = os.getenv('SLACK_USER_ID')  # Ensure this is set correctly
LAST_ACTIVE_CHANNEL_FILE = 'last_active_channel.json'
LAST_CHANNEL_BAT_FILE = 'openlastchannel.bat'

client = WebClient(token=SLACK_BOT_TOKEN)

def on_activate_open():
    print('Keyboard shortcut to open Slackbot chat activated!')
    try:
        subprocess.run([BATCH_FILE_PATH], check=True)
        print('Batch file executed successfully!')
    except subprocess.CalledProcessError as e:
        print(f'Error executing batch file: {e}')

def on_activate_close():
    print('Keyboard shortcut to close Slackbot chat activated!')
    try:
        switch_back_to_last_channel()
        print('Switched back to the last channel successfully!')
    except Exception as e:
        print(f'Error executing switch back script: {e}')

def switch_back_to_last_channel():
    last_active_channel = load_last_active_channel()
    print(f"Loaded last active channel: {last_active_channel}")  # Debug statement

    last_channel = last_active_channel.get(SLACK_USER_ID)
    print(f"User ID: {SLACK_USER_ID}, Last Channel: {last_channel}")  # Debug statement

    if last_channel:
        try:
            # Write the channel ID to the batch file
            with open(LAST_CHANNEL_BAT_FILE, 'w') as bat_file:
                bat_file.write(f'start "" "slack://channel?team={TEAM_ID}&id={last_channel}"')
            
            # Execute the batch file
            subprocess.run([LAST_CHANNEL_BAT_FILE], check=True)
            print(f"Switched back to the last channel: <#{last_channel}>")
        except Exception as e:
            print(f"Error switching back to the last channel: {e}")
    else:
        print("No last channel found.")

def load_last_active_channel():
    try:
        with open(LAST_ACTIVE_CHANNEL_FILE, 'r') as f:
            data = json.load(f)
            print(f"Loaded data from JSON: {data}")  # Debug statement
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading JSON file: {e}")  # Debug statement
        return {}

def for_canonical(f):
    return lambda k: f(l.canonical(k))

hotkey_open = keyboard.HotKey(
    keyboard.HotKey.parse('<ctrl>+<alt>+l'),
    on_activate_open)

hotkey_close = keyboard.HotKey(
    keyboard.HotKey.parse('<ctrl>+<alt>+k'),
    on_activate_close)

with keyboard.Listener(
        on_press=for_canonical(hotkey_open.press),
        on_release=for_canonical(hotkey_open.release)) as l:
    with keyboard.Listener(
            on_press=for_canonical(hotkey_close.press),
            on_release=for_canonical(hotkey_close.release)) as l2:
        l.join()
        l2.join()
