import os
import json
import subprocess
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from transformers import pipeline

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_USER_ID = os.getenv('SLACK_USER_ID')  # Your bot user ID
BATCH_FILE_PATH = 'OpenSlackbotChat.bat'  # Path to the existing batch file to open the bot's DM
client = WebClient(token=SLACK_BOT_TOKEN)

# Global state to perform follow-ups
conversation_state = {}
# Global state to track last channel/DM
last_active_channel = {}
LAST_ACTIVE_CHANNEL_FILE = 'last_active_channel.json'

def save_last_active_channel():
    with open(LAST_ACTIVE_CHANNEL_FILE, 'w') as f:
        json.dump(last_active_channel, f)

def load_last_active_channel():
    global last_active_channel
    try:
        with open(LAST_ACTIVE_CHANNEL_FILE, 'r') as f:
            last_active_channel = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        last_active_channel = {}

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.json
    print("Received request:", data)  # Log incoming requests for debugging

    if 'challenge' in data:
        return jsonify({'challenge': data['challenge']})

    if 'event' in data:
        event = data['event']
        event_type = event['type']

        if event_type == 'message' and 'subtype' not in event:
            handle_message_event(data, event)
        elif event_type == 'reaction_added':
            handle_reaction_event(event)
        elif event_type == 'channel_created':
            handle_channel_created_event(event)
        elif event_type == 'member_joined_channel':
            handle_member_joined_channel_event(event)

    return jsonify({'status': 'ok'})

@app.route('/slack/command', methods=['POST'])
def slack_command():
    data = request.form
    print("Received command:", data)  # Log incoming commands for debugging

    if data.get('command') == '/slackally':
        open_bot_dm()
        return jsonify({
            "response_type": "ephemeral",
            "text": "Opening a DM with the bot..."
        })

    return jsonify({'status': 'ok'})

def open_bot_dm():
    # Use the existing batch file to open the bot's DM
    try:
        subprocess.run([BATCH_FILE_PATH], check=True)
        print(f"Opened bot DM with user ID: {SLACK_USER_ID}")
        
        # Greet the user with a message
        greet_user(SLACK_USER_ID)
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to open bot DM: {e}")

def greet_user(channel_id):
    try:
        client.chat_postMessage(
            channel=channel_id,
            text="Hi, how can I help you?"
        )
        print("Greeted the user in the bot's DM.")
    except SlackApiError as e:
        print(f"Error sending greeting message: {e.response['error']}")

def handle_message_event(data, event):
    user = event['user']
    text = event['text'].strip().lower()
    channel = event['channel']
    channel_type = event.get('channel_type')

    if user == data['authorizations'][0]['user_id']:
        return

    print(f"Message from {user} in {channel}: {text}")

    # Update the last active channel for the user
    last_active_channel[SLACK_USER_ID] = channel
    save_last_active_channel()

    if channel_type == 'im':
        if channel not in conversation_state:
            conversation_state[channel] = {'responded': False, 'awaiting_channel_name': False}

        if conversation_state[channel]['awaiting_channel_name']:
            handle_channel_creation(channel, text)
        elif not conversation_state[channel]['responded']:
            handle_direct_message(user, text, channel)
        else:
            print(f"Already responded to a greeting in channel {channel}.")
    else:
        print(f"Ignoring message from channel {channel_type} channel {channel}")

def handle_reaction_event(event):
    user = event['user']
    reaction = event['reaction']
    item = event['item']
    channel = item['channel']
    print(f"Reaction {reaction} added by {user} in {channel}")

def handle_channel_created_event(event):
    channel = event['channel']
    channel_id = channel['id']
    channel_name = channel['name']
    creator = channel['creator']
    print(f"Channel {channel_name} created by {creator}")

def handle_member_joined_channel_event(event):
    user = event['user']
    channel = event['channel']
    print(f"User {user} joined channel {channel}")

def handle_direct_message(user, text, channel):
    if "hello" in text or "hi" in text or "hey" in text:
        send_message(channel, f"Hello <@{user}>, how can I assist you today?")
        conversation_state[channel]['responded'] = False
    elif "create channel" in text:
        send_message(channel, "What do you want to name the channel?")
        conversation_state[channel]['awaiting_channel_name'] = True
        conversation_state[channel]['responded'] = False
    elif "active users" in text:
        active_users = get_active_users()
        if active_users:
            send_message(channel, f"Active users are: {', '.join(active_users)}.")
        else:
            send_message(channel, "Failed to fetch active users.")
        conversation_state[channel]['responded'] = False
    elif "thank you" in text:
        send_message(channel, "You're welcome! If you have any more questions or if there's anything else you'd like to know, feel free to ask. I'm here to help!")
        if channel in conversation_state:
            del conversation_state[channel]
    elif "help" in text:
        help_text = (
            "Here are the commands you can use:\n"
            "- 'Hello', 'Hi', 'Hey' to greet the bot.\n"
            "- 'Create channel' to create a new channel (you will be asked for the channel name).\n"
            "- 'Active users' to get a list of active users.\n"
            "- 'Help' to see this help message.\n"
            "- 'Thank you' to end the conversation."
        )
        send_message(channel, help_text)
        conversation_state[channel]['responded'] = False
    else:
        send_message(channel, f"<@{user}>, I didn't understand that command.")
        conversation_state[channel]['responded'] = False

def handle_channel_creation(channel, text):
    channel_name = text.strip()
    if channel_name:
        channel_id = create_channel(channel_name)
        if channel_id:
            send_message(channel, f"Channel '{channel_name}' created successfully.")
        else:
            send_message(channel, "Failed to create channel.")
    else:
        send_message(channel, "Please provide a valid channel name.")
    conversation_state[channel]['awaiting_channel_name'] = False

def send_message(channel, text):
    try:
        client.chat_postMessage(channel=channel, text=text)
    except SlackApiError as e:
        print(f"Error posting message: {e.response['error']}")

def create_channel(channel_name):
    try:
        response = client.conversations_create(name=channel_name)
        return response['channel']['id']
    except SlackApiError as e:
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
        print(f"An unexpected error occurred: {e}")
        return None

def get_workspace_info():
    try:
        auth_response = client.auth_test()
        workspace_name = auth_response['team']

        channels_response = client.conversations_list(types='public_channel,private_channel')
        unread_messages_count = 0
        channel_info = []
        for channel in channels_response['channels']:
            if channel['is_member']:
                try:
                    history_response = client.conversations_history(channel=channel['id'], limit=100)
                    unread_count = sum(1 for message in history_response['messages'] if 'unread_count_display' in message)
                    unread_messages_count += unread_count
                    channel_info.append({
                        'name': channel['name'],
                        'purpose': channel.get('purpose', {}).get('value', 'No purpose set'),
                        'num_messages': len(history_response['messages']),
                        'unread_messages': unread_count
                    })
                except SlackApiError as e:
                    print(f"Error fetching history for channel {channel['name']}: {e.response['error']}")

        users_response = client.users_list()
        online_users = []
        for user in users_response['members']:
            if not user['is_bot']:
                try:
                    presence_response = client.users_getPresence(user=user['id'])
                    if presence_response['presence'] == 'active':
                        online_users.append(user['real_name'])
                except SlackApiError as e:
                    print(f"Error fetching presence for user {user['name']}: {e.response['error']}")

        user_profile_response = client.users_profile_get(user=auth_response['user_id'])
        user_profile = user_profile_response.get('profile', {})

        return {
            'workspace': workspace_name,
            'unread_messages': unread_messages_count,
            'online_users': online_users,
            'channels': channel_info,
            'current_user': {
                'name': user_profile.get('real_name', 'N/A'),
                'title': user_profile.get('title', 'N/A'),
                'status': user_profile.get('status_text', 'N/A')
            }
        }
    except SlackApiError as e:
        print(f"Error fetching workspace info: {e.response['error']}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def switch_channel(channel_name):
    try:
        channels_response = client.conversations_list(types='public_channel,private_channel')
        channels = channels_response['channels']
        print(f"Available channels: {[ch['name'] for ch in channels]}")
        channel = next((ch for ch in channels if ch['name'] == channel_name), None)
        if channel:
            conversation_state['current_channel_id'] = channel['id']
            print(f"Switched to channel ID: {channel['id']}")
            return f"Switched to the {channel_name} channel."
        else:
            return f"Channel {channel_name} not found."
    except SlackApiError as e:
        print(f"Error switching channel: {e.response['error']}")
        return "Failed to switch channel."

def navigate_messages(direction):
    channel_id = conversation_state.get('current_channel_id')
    if not channel_id:
        return "No channel selected. Please switch to a channel first."

    try:
        history_response = client.conversations_history(channel=channel_id, limit=2)
        messages = history_response['messages']
        if direction == "next":
            if len(messages) > 1:
                return messages[1]['text']
            else:
                return "No more messages."
        elif direction == "previous":
            if len(messages) > 0:
                return messages[0]['text']
            else:
                return "No previous messages."
        else:
            return "Invalid direction."
    except SlackApiError as e:
        print(f"Error navigating messages: {e.response['error']}")
        return "Failed to navigate messages."

def provide_help():
    help_text = (
        "Here are the commands you can use:\n"
        "- 'Switch to [channel name]' to navigate between channels.\n"
        "- 'Read previous/next message' to navigate messages.\n"
        "- 'Help' to get this help message.\n"
        "- 'Feedback [your feedback]' to provide feedback.\n"
        "- 'Channel link [channel name]' to get a link to a specific channel."
    )
    return help_text

def handle_feedback(feedback):
    with open('feedback.log', 'a') as f:
        f.write(feedback + '\n')
    return "Thank you for your feedback!"

def provide_channel_link(channel_name):
    try:
        channels_response = client.conversations_list(types='public_channel,private_channel')
        channels = channels_response['channels']
        print(f"Available channels: {[ch['name'] for ch in channels]}")
        channel = next((ch for ch in channels if ch['name'] == channel_name), None)
        if channel:
            channel_id = channel['id']
            channel_link = f"https://slack.com/app_redirect?channel={channel_id}"
            return f"Here is the link to the {channel_name} channel: {channel_link}. Click it to open the channel."
        else:
            return f"Channel {channel_name} not found."
    except SlackApiError as e:
        print(f"Error providing channel link: {e.response['error']}")
        return "Failed to provide channel link."

def get_context_from_web(query):
    search_url = f"https://www.google.com/search?q={query}"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    paragraphs = soup.find_all('p')
    context = " ".join([para.get_text() for para in paragraphs])
    return context

def answer_general_question(question):
    qa_pipeline = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")
    context = get_context_from_web(question)
    result = qa_pipeline(question=question, context=context)
    return result['answer']

if __name__ == "__main__":
    load_last_active_channel()  # Load last active channel on startup
    app.run(port=3000)
