import os
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
client = WebClient(token=SLACK_BOT_TOKEN)

# Global state to perform follow-ups
conversation_state = {}

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.json
    print("Received request:", data)  # Log incoming requests for debugging

    # Handle Slack URL verification challenge
    if 'challenge' in data:
        return jsonify({'challenge': data['challenge']})

    # Process events
    if 'event' in data:
        event = data['event']
        event_type = event['type']

        if event_type == 'message' and 'subtype' not in event:
            user = event['user']
            text = event['text'].strip().lower()
            channel = event['channel']

            # Check if the message is from the bot itself
            if user == data['authorizations'][0]['user_id']:
                return jsonify({'status': 'ok'})

            print(f"Message from {user} in {channel}: {text}")

            if channel not in conversation_state:
                conversation_state[channel] = {'responded': False, 'awaiting_channel_name': False}

            if conversation_state[channel]['awaiting_channel_name']:
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
            elif not conversation_state[channel]['responded']:
                handle_message(user, text, channel)
            else:
                print(f"Already responded to a greeting in channel {channel}.")

        elif event_type == 'reaction_added':
            user = event['user']
            reaction = event['reaction']
            item = event['item']
            channel = item['channel']
            print(f"Reaction {reaction} added by {user} in {channel}")

        elif event_type == 'channel_created':
            channel = event['channel']
            channel_id = channel['id']
            channel_name = channel['name']
            creator = channel['creator']
            print(f"Channel {channel_name} created by {creator}")

        elif event_type == 'member_joined_channel':
            user = event['user']
            channel = event['channel']
            print(f"User {user} joined channel {channel}")

        # Add more event handlers as needed

    return jsonify({'status': 'ok'})

def handle_message(user, text, channel):
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

def send_message(channel, text):
    try:
        response = client.chat_postMessage(
            channel=channel,
            text=text
        )
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

# Additional functionalities

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
        # Fetch current workspace (team) info
        auth_response = client.auth_test()
        workspace_name = auth_response['team']

        # Fetch the number of unread messages
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

        # Fetching the number of online users
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

        # Fetching current user's profile info
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

@app.route('/api/command', methods=['POST'])
def command():
    data = request.json
    query = data.get('query', '').lower()
    response_text = "Failed to process command."
    if "hello" in query or "hi" in query or "hey" in query or "wake up" in query:
        response_text = "Hello! How can I assist you today?"

    elif "fetch slack elements" in query:
        print(f"Received command: {query}")  # Debugging print
        scrape_slack_dom_elements()
        response_text = "Slack elements fetched. Check the console for details."

    elif "create channel" in query:
        response_text = "What do you want to name the channel?"
        conversation_state['awaiting_channel_name'] = True

    elif "open threads" in query:
        response_text = "Do you want me to read aloud the keyboard shortcuts for opening threads?"

    elif "open mentions and reactions" in query:
        response_text = "Do you want me to read aloud the keyboard shortcuts for opening mentions and reactions?"

    elif "open drafts" in query:
        response_text = "Do you want me to read aloud the keyboard shortcuts for opening drafts?"

    elif "open direct messages" in query:
        response_text = "Do you want me to read aloud the keyboard shortcuts for opening direct messages?"

    elif "active users" in query:
        active_users = get_active_users()
        if active_users:
            response_text = f"Active users are: {', '.join(active_users)}."
        else:
            response_text = "Failed to fetch active users."

    elif "channel link" in query:
        channel_name = query.split("channel link")[-1].strip()
        response_text = provide_channel_link(channel_name)

    elif "switch to" in query:
        channel_name = query.split("switch to")[-1].strip()
        response_text = switch_channel(channel_name)

    elif "read previous message" in query:
        response_text = navigate_messages("previous")

    elif "read next message" in query:
        response_text = navigate_messages("next")

    elif any(phrase in query for phrase in ["where am i", "overview", "workspace info", "workspace information"]):
        workspace_info = get_workspace_info()
        if workspace_info:
            response_text = (
                f"You are currently in the workspace: {workspace_info['workspace']}\n"
                f"Number of unread messages: {workspace_info['unread_messages']}\n"
                f"Number of online users: {len(workspace_info['online_users'])}\n"
                f"Current user: {workspace_info['current_user']['name']}, {workspace_info['current_user']['title']}\n"
                f"Status: {workspace_info['current_user']['status']}\n"
                f"Channels:\n"
                + '\n'.join(f"- {channel['name']} ({channel['purpose']}) - Messages: {channel['num_messages']}, Unread: {channel['unread_messages']}" for channel in workspace_info['channels']) + '\n'
                f"Do you want me to read out who is online? (yes/no)"
            )
            conversation_state['awaiting_follow_up'] = True
            conversation_state['workspace_info'] = workspace_info
        else:
            response_text = "Failed to fetch workspace information."
    elif "yes" in query and conversation_state.get('awaiting_follow_up'):
        workspace_info = conversation_state.get('workspace_info', {})
        online_users = workspace_info.get('online_users', [])
        if online_users:
            response_text = f"Online users: {', '.join(online_users)}"
        else:
            response_text = "No users are currently online."
        conversation_state['awaiting_follow_up'] = False

    elif "no" in query and conversation_state.get('awaiting_follow_up'):
        response_text = "Okay, I won't read out the names of online users."
        conversation_state['awaiting_follow_up'] = False

    else:
        response_text = answer_general_question(query)
    
    return jsonify({'response': response_text})

if __name__ == "__main__":
    app.run(port=3000)
