from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from speak import say
from listen import takeCommand
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from greeting import greetMe
from config import Config
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

print(f"SLACK_BOT_TOKEN from .env: {os.getenv('SLACK_BOT_TOKEN')}")
print(f"SLACK_BOT_TOKEN from config: {app.config['SLACK_BOT_TOKEN']}")

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')

# Setup Slack client
client = WebClient(token=SLACK_BOT_TOKEN)
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

def create_channel(channel_name):
    try:
        response = client.conversations_create(name=channel_name)
        print(response)
        return response['channel']['id']
    except SlackApiError as e:
        print(f"SLACK_BOT_TOKEN: {SLACK_BOT_TOKEN}")
        print(f"Error creating channel: {e.response['error']}")
        return None

def get_active_users():
    try:
        response = client.users_list()
        active_users = [user['name'] for user in response['members'] if user.get('presence') == 'active']
        return active_users
    except SlackApiError as e:
        print(f"Error fetching users: {e.response['error']}")
        return None

def read_shortcut_create_channel():
    say("To create a channel, use Ctrl + Shift + K")

def read_shortcut_open_threads():
    say("To open threads, use Ctrl + Shift + T")

def read_shortcut_open_mentions_reactions():
    say("To open mentions and reactions, use Ctrl + Shift + M")

def read_shortcut_open_drafts():
    say("To open drafts, use Ctrl + Shift + D")

def read_shortcut_open_direct_messages():
    say("To open direct messages, use Ctrl + Shift + J")

def read_all_shortcuts():
    read_shortcut_create_channel()
    read_shortcut_open_threads()
    read_shortcut_open_mentions_reactions()
    read_shortcut_open_drafts()
    read_shortcut_open_direct_messages()

def scrape_slack_dom_elements():
    print("scrape_slack_dom_elements() called")
    try:
        response = requests.get('https://slack.com', headers={'User-Agent': 'Mozilla/5.0'})
        print(f"HTTP Status Code: {response.status_code}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            print(soup.prettify())
        else:
            print(f"Failed to retrieve Slack page. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")


@app.route('/api/command', methods=['POST'])
def command():
    data = request.json
    query = data.get('query', '').lower()
    response_text = "Failed to process command."

    if "hello" in query or "hi" in query or "hey" in query or "wake up" in query:
        greetMe()
        response_text = "Hello! How can I assist you today?"

    elif "fetch slack elements" in query:
        print(f"Received command: {query}")  # Debugging print
        scrape_slack_dom_elements()
        response_text = "Slack elements fetched. Check the console for details."

    elif "create channel" in query:
        say("Do you want me to read aloud the keyboard shortcuts for creating a channel?")
        read_shortcut_create_channel()
        channel_name = query.split("create channel")[-1].strip()
        channel_id = create_channel(channel_name)
        if channel_id:
            response_text = f"Channel {channel_name} created successfully."
        else:
            response_text = "Failed to create channel."

    elif "open threads" in query:
        say("Do you want me to read aloud the keyboard shortcuts for opening threads?")
        read_shortcut_open_threads()
        response_text = "Functionality for opening threads is not implemented yet."

    elif "open mentions and reactions" in query:
        say("Do you want me to read aloud the keyboard shortcuts for opening mentions and reactions?")
        read_shortcut_open_mentions_reactions()
        response_text = "Functionality for opening mentions and reactions is not implemented yet."

    elif "open drafts" in query:
        say("Do you want me to read aloud the keyboard shortcuts for opening drafts?")
        read_shortcut_open_drafts()
        response_text = "Functionality for opening drafts is not implemented yet."

    elif "open direct messages" in query:
        say("Do you want me to read aloud the keyboard shortcuts for opening direct messages?")
        read_shortcut_open_direct_messages()
        response_text = "Functionality for opening direct messages is not implemented yet."

    elif "active users" in query:
        active_users = get_active_users()
        if active_users:
            response_text = f"Active users are: {', '.join(active_users)}."
        else:
            response_text = "Failed to fetch active users."

    return jsonify({'response': response_text})

if __name__ == "__main__":
    app.run(port=3000)
