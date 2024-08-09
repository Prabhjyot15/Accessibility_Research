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
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from speak import say
from listen import takeCommand
from greeting import greetMe
from shortcuts import shortcuts_map,get_best_match
from config import Config
from nltk.tokenize import word_tokenize
from sklearn.linear_model import LogisticRegression
from botFunc import conversation_state
from dotenv import load_dotenv
from transformers import pipeline
import requests
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.ensemble import VotingClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from bs4 import BeautifulSoup
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report
import json
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from nltk.corpus import wordnet
import random
from nltk.tokenize import word_tokenize
from nltk import download
from sklearn.utils import resample
from shortcuts import shortcuts_map, ps
from botFunc import get_channel_members,get_current_user_id,list_active_channels,extract_channel_name, provide_channel_link,create_channel,get_active_users,navigate_messages, switch_channel, read_all_shortcuts,read_shortcut_create_channel,read_shortcut_open_direct_messages,read_shortcut_open_drafts,read_shortcut_open_mentions_reactions,read_shortcut_open_threads,switch_channel,scrape_slack_dom_elements,provide_help,answer_general_question,get_workspace_info,get_context_from_web
download('wordnet')
download('punkt')
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

def augment_text(text, num_augmented=1):
    words = word_tokenize(text)
    augmented_texts = []
    
    for _ in range(num_augmented):
        new_words = words.copy()
        word_idx = random.randint(0, len(words) - 1)
        synonym_list = wordnet.synsets(words[word_idx])
        
        if synonym_list:
            synonym = random.choice(synonym_list).lemmas()[0].name()
            if synonym != words[word_idx]:
                new_words[word_idx] = synonym
                augmented_texts.append(' '.join(new_words))
    
    return augmented_texts

def load_and_train_model():
    with open('data.json', 'r') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    max_class_size = df['intent'].value_counts().max()
    df_balanced = pd.concat([
        resample(df[df['intent'] == intent], replace=True, n_samples=max_class_size, random_state=42)
        for intent in df['intent'].unique()
    ])
    df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)

    augmented_data = []
    for _, row in df_balanced.iterrows():
        text = row['text']
        intent = row['intent']
        augmented_texts = augment_text(text, num_augmented=3) 
        augmented_data.extend([(text, intent) for text in augmented_texts])

    augmented_df = pd.DataFrame(augmented_data, columns=['text', 'intent'])
    df_augmented = pd.concat([df_balanced, augmented_df]).drop_duplicates().reset_index(drop=True)

    X = df_augmented['text']
    y = df_augmented['intent']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipeline = Pipeline([
        ('vectorizer', TfidfVectorizer(lowercase=True, stop_words='english', ngram_range=(1, 2), max_features=5000)),
        ('classifier', LogisticRegression(max_iter=1000))
    ])

    param_grid = {
        'classifier__C': [0.1, 1, 10, 100],
        'classifier__solver': ['liblinear', 'saga'],
    }

    grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring='accuracy')
    grid_search.fit(X_train, y_train)

    return grid_search.best_estimator_

model = load_and_train_model()


def preprocess_query(query):
    tokens = word_tokenize(query.lower())
    stemmed_tokens = [ps.stem(token) for token in tokens]
    return set(stemmed_tokens)

def determine_intent(query):
    query = query.lower().strip() 
    predicted_intent = model.predict([query])
    return predicted_intent[0]

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
                f"Channels:\n"
                + '\n'.join(f" Channel Name: {channel['name']} and Unread messages: {channel['unread_messages']}" for channel in workspace_data['channels']) + '\n'
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

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.json
    
    if 'challenge' in data:
        return jsonify({'challenge': data['challenge']})

    if 'event' in data:
        event = data['event']
        event_type = event['type']

        if event_type == 'message' and 'subtype' not in event:
            print("here")
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
    print(data)


    if data.get('command') == '/slackally':
        open_bot_dm()
        return jsonify({
            "response_type": "ephemeral",
            "text": "Opening a DM with the bot..."
        })


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
    intent = determine_intent(text)

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
            print("here in nested if")
            handle_direct_message(user, text, channel,intent)
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

def handle_direct_message(user, text, channel, intent):
    print("intent: ",intent)
    # Ensure conversation state is initialized
    if channel not in conversation_state:
        conversation_state[channel] = {'responded': False, 'awaiting_channel_name': False}

    # Check if the bot has already responded to this specific message to avoid duplicates
    if conversation_state[channel]['responded']:
        print(f"Already responded to a greeting in channel {channel}.")
        return

    # Check for greetings
    if "hello" in text or "hi" in text or "hey" in text:
        send_message(channel, f"Hello <@{user}>, how can I assist you today?")
        conversation_state[channel]['responded'] = False
        return  # Early return to prevent further processing

    # Handle channel creation intent
    if "create channel" in text or conversation_state[channel].get('awaiting_channel_name'):
        if conversation_state[channel].get('awaiting_channel_name'):
            handle_channel_creation(channel, text)
        else:
            send_message(channel, "What do you want to name the channel?")
            
        
        return  # Early return to prevent further processing

    # Handle "thank you"
    if "thank you" in text:
        send_message(channel, "You're welcome! If you have any more questions or if there's anything else you'd like to know, feel free to ask. I'm here to help!")
        if channel in conversation_state:
            del conversation_state[channel]
        return  # Early return to prevent further processing

    # Handle help request
    if "help" in text:
        help_text = (
            "Here are the commands you can use:\n"
            "- 'Hello', 'Hi', 'Hey' to greet the bot.\n"
            "- 'Create channel' to create a new channel (you will be asked for the channel name).\n"
            "- 'Active users' to get a list of active users.\n"
            "- 'Help' to see this help message.\n"
            "- 'Thank you' to end the conversation."
        )
        send_message(channel, help_text)
        
        return  # Early return to prevent further processing

    # Handle workspace information request
    if text == "where am i":
        response_text = workspace_information()
        send_message(channel, response_text)
        
        return  # Early return to prevent further processing

    # Handle follow-up actions like shortcuts
    if conversation_state.get('awaiting_follow_up') == 'shortcut':
        matched_action = get_best_match(text)
        response_text = matched_action if matched_action else "Sorry, I couldn't find a matching shortcut."
        conversation_state['awaiting_follow_up'] = None
        send_message(channel, response_text)
        
        return  # Early return to prevent further processing

    # Handle follow-up actions for channel members
    if conversation_state.get('awaiting_follow_up') == 'channel_members':
        channel_name = text.strip()
        res = get_channel_members(channel_name)
        if res:
            response_text = f"The members in {channel_name} are: {', '.join(res)}"
        else:
            response_text = f"Unable to fetch members for channel '{channel_name}'."
        conversation_state['awaiting_follow_up'] = None
        send_message(channel, response_text)
        
        return  # Early return to prevent further processing

    # Handle follow-up actions for online users
    if conversation_state.get('awaiting_follow_up') == 'online_users':
        if "yes" in text:
            workspace_info = conversation_state.get('workspace_info', {})
            online_users = workspace_info.get('online_users', [])
            response_text = f"Online users: {', '.join(online_users)}" if online_users else "No users are currently online."
            conversation_state['awaiting_follow_up'] = None
            send_message(channel, response_text)
        elif "no" in text:
            response_text = "Okay, I won't read out the names of online users."
            conversation_state['awaiting_follow_up'] = None
            send_message(channel, response_text)
        
        return  # Early return to prevent further processing

    # Handle other intents
    if intent == "greeting":
        response_text = "Hello! How can I assist you today?"
        send_message(channel, response_text)
        return
        

    elif intent == "fetch slack elements":
        scrape_slack_dom_elements()
        response_text = "Slack elements fetched. Check the console for details."
        send_message(channel, response_text)
        return
        

    elif intent == "create channel":
        response_text = "Do you want me to read aloud the keyboard shortcuts for creating a channel? yes or no"
        conversation_state['awaiting_follow_up'] = 'read_shortcut'
        send_message(channel, response_text)
        return
        

    elif intent == "list active channels":
        userid = get_current_user_id()
        res = list_active_channels(userid)
        response_text = "The user is active in the following channels:", res
        send_message(channel, response_text)
        return
        

    elif intent == "list channel members":
        conversation_state['awaiting_follow_up'] = 'channel_members'
        send_message(channel, "Please enter the channel name for which you want the member list:")
        return

    elif intent == "workspace overview":
        response_text = workspace_information()
        send_message(channel, response_text)
        return

    elif intent == "general":
        response_text = "How can I help you"
        send_message(channel, response_text)
        return

    elif intent == "keyboard_shortcut":
        response_text = "Which shortcut do you need help with?"
        conversation_state['awaiting_follow_up'] = 'shortcut'
        send_message(channel, response_text)
        return

    elif "open threads" in text:
        read_shortcut_open_threads()
        response_text = "Functionality for opening threads is not implemented yet."
        send_message(channel, response_text)
        return

    elif "open mentions and reactions" in text:
        read_shortcut_open_mentions_reactions()
        response_text = "Functionality for opening mentions and reactions is not implemented yet."
        send_message(channel, response_text)
        return

    elif "open drafts" in text:
        read_shortcut_open_drafts()
        response_text = "Functionality for opening drafts is not implemented yet."
        send_message(channel, response_text)
        return

    elif "open direct messages" in text:
        read_shortcut_open_direct_messages()
        response_text = "Functionality for opening direct messages is not implemented yet."
        send_message(channel, response_text)
        return

    elif "active users" in text:
        active_users = get_active_users()
        response_text = f"Active users are: {', '.join(active_users)}." if active_users else "Failed to fetch active users."
        send_message(channel, response_text)
        return

    elif "channel link" in text:
        channel_name = text.split("channel link")[-1].strip()
        response_text = provide_channel_link(channel_name)
        send_message(channel, response_text)
        return

    elif "switch to" in text:
        channel_name = text.split("switch to")[-1].strip()
        response_text = switch_channel(channel_name)
        send_message(channel, response_text)
        return

    elif "read previous message" in text:
        response_text = navigate_messages("previous")
        send_message(channel, response_text)
        return

    elif "read next message" in text:
        response_text = navigate_messages("next")
        send_message(channel, response_text)
        return

    else:
        send_message(channel, f"<@{user}>, I didn't understand that command.")
        conversation_state[channel]['responded'] = False
        return

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
