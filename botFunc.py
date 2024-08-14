import re
import requests
import time
from bs4 import BeautifulSoup
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from speak import say
from listen import takeCommand
import json
from state import conversation_state,LAST_ACTIVE_CHANNEL_FILE,SLACK_USER_ID,BATCH_FILE_PATH, SLACK_BOT_TOKEN, last_active_channel
from transformers import pipeline
import subprocess


client = WebClient(token=SLACK_BOT_TOKEN)

def create_channel(channel_name):
    try:
        response = client.conversations_create(name=channel_name)
        return response['channel']['id']
    except SlackApiError as e:
        print(f"Error creating channel: {e}")
        return None

def get_active_users():
    try:
        response = client.users_list()
        active_users = [user['name'] for user in response['members'] if user.get('presence') == 'active']
        return active_users
    except SlackApiError as e:
        print(f"Error fetching users: {e.response['error']}")
        return None
    
def extract_channel_name(channel_name):

    sanitized_name = re.sub(r'[^a-z0-9-]', '', channel_name)  # Remove invalid characters
    if len(sanitized_name) == 0:
        return None  # No valid name found
    return sanitized_name
    

def read_shortcut_create_channel():
    say("To create a channel, Press Ctrl+K to open the quick launcher then type /create and Press Enter. Please follow the instructions further")

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

def get_current_user_id():
    headers = {
        'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
    }
    response = requests.get('https://slack.com/api/auth.test', headers=headers)
    
    print("Response Status Code:", response.status_code)
    print("Response Content:", response.json())

    if response.status_code == 200:
        data = response.json()
        if data.get('ok'):
            return data.get('user_id')
        else:
            print("Error:", data.get('error'))
    else:
        print("Failed to fetch user identity:", response.status_code)
    
    return None

def list_active_channels(user_id):
    headers = {
        'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    active_channels = []
    cursor = None
    
    while True:
        params = {
            'types': 'public_channel,private_channel',
            'limit': 1000,
        }
        if cursor:
            params['cursor'] = cursor
        
        response = requests.get('https://slack.com/api/conversations.list', headers=headers, params=params)
        data = response.json()
        
        if not data.get('ok'):
            print("Error fetching channels:", data.get('error'))
            break
        
        channels = data.get('channels', [])
        cursor = data.get('response_metadata', {}).get('next_cursor')
        
        for channel in channels:
            channel_id = channel['id']
            members_response = requests.get('https://slack.com/api/conversations.members', headers=headers, params={
                'channel': channel_id
            })
            members_data = members_response.json()
            
            if not members_data.get('ok'):
                print(f"Error fetching members for channel {channel_id}:", members_data.get('error'))
                continue
            
            members = members_data.get('members', [])
            if user_id in members:
                active_channels.append(channel['name'])
        
        if not cursor:
            break
    
    return active_channels

def get_channel_members(channel_name):
    headers = {
        'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    params = {
        'types': 'public_channel,private_channel',
        'limit': 1000,
    }
    
    response = requests.get('https://slack.com/api/conversations.list', headers=headers, params=params)
    data = response.json()
    
    if not data.get('ok'):
        print("Error fetching channels:", data.get('error'))
        return []
    
    channels = data.get('channels', [])
    
    for channel in channels:
        if channel['name'] == channel_name:
            channel_id = channel['id']
            members_response = requests.get('https://slack.com/api/conversations.members', headers=headers, params={
                'channel': channel_id
            })
            members_data = members_response.json()
            
            if not members_data.get('ok'):
                print(f"Error fetching members for channel {channel_id}:", members_data.get('error'))
                return []
            
            member_ids = members_data.get('members', [])
            member_names = []
            
            for member_id in member_ids:
                user_response = requests.get('https://slack.com/api/users.info', headers=headers, params={
                    'user': member_id
                })
                user_data = user_response.json()
                
                if not user_data.get('ok'):
                    print(f"Error fetching user info for user {member_id}:", user_data.get('error'))
                    continue
                
                member_names.append(user_data['user']['real_name'])
            
            return member_names
    
    return ["No members found"]

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


def get_workspace_info():
    channel_info = []
    channels_members_info = {}
    try:
    # Fetch current workspace (team) info
        auth_response = client.auth_test()
        workspace_name = auth_response['team']

    # Fetch the number of unread messages
        channels_response = client.conversations_list(types='public_channel,private_channel')
        unread_messages_count = 0
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
                
                # Fetch channel members
                    members_response = client.conversations_members(channel=channel['id'])
                    channels_members_info[channel['name']] = [client.users_info(user=user_id)['user']['real_name'] for user_id in members_response['members']]

                except SlackApiError as e:
                    print(f"Error fetching history for channel {channel['name']}: {e.response['error']}")

    # Fetch the number of online users
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

    # Fetch current user's profile info
        user_profile_response = client.users_profile_get(user=auth_response['user_id'])
        user_profile = user_profile_response.get('profile', {})

        return {
        'workspace': workspace_name,
        'unread_messages': unread_messages_count,
        'online_users': online_users,
        'channels': channel_info,
        'channels_members_info': channels_members_info,
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
            say(f"Switched to the {channel_name} channel.")
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
            say(f"Here is the link to the {channel_name} channel: {channel_link}. Click it to open the channel.")
            print(f"Generated channel link: {channel_link}") 
            return f"Link to {channel_name} channel sent."
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
    return "What do you need help with?"
    # qa_pipeline = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")
    # context = get_context_from_web(question)
    # result = qa_pipeline(question=question, context=context)
    # return result['answer']

def save_last_active_channel():
    with open(LAST_ACTIVE_CHANNEL_FILE, 'w') as f:
        json.dump(last_active_channel, f)

def workspace_information():
    workspace_data = get_workspace_info()
    if workspace_data:
        response_text = (
                f"You are currently in the workspace: {workspace_data['workspace']}\n"
                f"Number of unread messages: {workspace_data['unread_messages']}\n"
                f"Number of online users: {len(workspace_data['online_users'])}\n"
                #f"Channels:\n"
                #+ '\n'.join(f" Channel Name: {channel['name']} and Unread messages: {channel['unread_messages']}" for channel in workspace_data['channels']) + '\n'
                f" To open the unread messages view please click Ctrl Shift A\n"
                f"Do you want me to read out who is online? Please say yes or no"
        )
        conversation_state['awaiting_follow_up'] = 'online_users'
        conversation_state['workspace_info'] = workspace_data
    else:
        response_text = "Failed to fetch workspace information."
    return response_text        

def load_last_active_channel():
    global last_active_channel
    try:
        with open(LAST_ACTIVE_CHANNEL_FILE, 'r') as f:
            last_active_channel = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        last_active_channel = {}

def open_direct_message_channel(user_id, recipient_id):
    try:
        # Opening a direct message channel between the users
        response = client.conversations_open(users=f"{user_id},{recipient_id}")
        return response['channel']['id']
    except SlackApiError as e:
        print(f"Error opening DM channel: {e.response['error']}")
        return None

def send_direct_message(user_id, recipient_id, message):
    try:
        print(f"Sending message from {user_id} to {recipient_id}. Message: {message}")
        channel_id = open_direct_message_channel(user_id, recipient_id)
        if channel_id is None:
            print("Failed to open DM channel.")
            return
        response = client.chat_postMessage(
            channel=channel_id,
            text=f"Message from <@{user_id}>: {message}"
        )
        print(f"Message sent to recipient successfully. Response: {response}")

        # Acknowledging to the sender
        client.chat_postMessage(
            channel=user_id,
            text="Your message has been sent successfully."
        )
        print("Acknowledgment sent to sender successfully.")

    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")
        client.chat_postMessage(
            channel=user_id,
            text="There was an error sending your message. Please try again."
        )
        print("Error notification sent to sender.")

def send_message(channel, text):
    try:
        client.chat_postMessage(channel=channel, text=str(text))
        say(text)
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

def add_member_to_channel(channel_id, user_id):
    try:
        #To add any user to some channel, bot has to be in that channel
        try:
            client.conversations_join(channel=channel_id)
            print(f"Bot joined the channel {channel_id}.")
        except SlackApiError as e:
            if e.response['error'] == 'already_in_channel':
                print(f"Bot is already in the channel {channel_id}.")
            else:
                print(f"Error joining channel: {e.response['error']}")
                return None

        # Inviting the user to the channel
        response = client.conversations_invite(channel=channel_id, users=user_id)
        print(f"User {user_id} added to channel {channel_id}.")
        
        # Notifying the user via DM
        notify_user(user_id, f"You've been added to the channel <#{channel_id}>.")
        
        return response
    except SlackApiError as e:
        if e.response['error'] == 'ratelimited':
                retry_after = int(e.response.headers['Retry-After'])
                print(f"Rate limited. Retrying after {retry_after} seconds.")
                time.sleep(retry_after)        
        elif e.response['error'] == 'already_in_channel':
            conversation_state['awaiting_follow_up'] = None
            print(f"User {user_id} is already in the channel.")
        elif e.response['error'] == 'not_in_channel':
            print(f"Bot is not in the channel {channel_id}.")
        else:
            print(f"Error adding member to channel: {e.response['error']}")
        return None

def notify_user(user_id, message):
    try:
        response = client.chat_postMessage(channel=user_id, text=message)
        print(f"Notification sent to user {user_id}.")
        return response
    except SlackApiError as e:
        print(f"Error sending notification to user: {e.response['error']}")
        return None



def get_channel_id_by_name(channel_name):
    try:
        channels_response = client.conversations_list(types='public_channel,private_channel')
        channels = channels_response['channels']
        channel = next((ch for ch in channels if ch['name'] == channel_name), None)
        return channel['id'] if channel else None
    except SlackApiError as e:
        print(f"Error retrieving channel list: {e.response['error']}")
        return None
    
def get_user_id_by_name(user_name):
    try:
        user_name = user_name.lower()
        response = client.users_list()
        users = response['members']
        
        for user in users:
            real_name = user.get('real_name')
            if real_name and real_name.lower() == user_name:
                return user['id']
        return None
    except SlackApiError as e:
        print(f"Error fetching users: {e.response['error']}")
        return None

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
