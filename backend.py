import os
import threading
import queue
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from nltk.corpus import wordnet
from nltk import download
from model import load_and_train_model
from state import SLACK_BOT_TOKEN
from botFunc import (open_bot_dm, load_last_active_channel, get_channel_members, 
                     get_current_user_id, extract_channel_name, provide_channel_link, 
                     create_channel, get_active_users, navigate_messages, switch_channel, 
                     read_all_shortcuts, read_shortcut_create_channel, 
                     read_shortcut_open_direct_messages, read_shortcut_open_drafts, 
                     read_shortcut_open_mentions_reactions, read_shortcut_open_threads, 
                     scrape_slack_dom_elements, provide_help, answer_general_question, 
                     get_workspace_info, get_context_from_web)
from eventHandler import (handle_message_event, handle_channel_created_event, 
                          handle_channel_creation, handle_direct_message, 
                          handle_member_joined_channel_event, handle_reaction_event)

download('wordnet')
download('punkt')
load_dotenv()
import pyttsx3
engine = pyttsx3.init()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

client = WebClient(token=SLACK_BOT_TOKEN)

load_and_train_model()

event_queue = queue.Queue()

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.json
    if 'challenge' in data:
        return jsonify({'challenge': data['challenge']})

    if 'event' in data:
        event_type = data['event']['type']
        if event_type in ['message', 'reaction_added', 'channel_created', 'member_joined_channel']:
            event_queue.put(data)
            return jsonify({'status': 'ok'})
    return jsonify({'status': 'ok'})

@app.route('/slack/command', methods=['POST'])
def slack_command():
    data = request.form
    if data.get('command') == '/slackally':
        open_bot_dm()
        return jsonify({
            "response_type": "ephemeral",
            "text": "Opening a DM with the bot..."
        })

def process_events():
    while True:
        event_data = event_queue.get()
        event_type = event_data['event']['type']
        if event_type == 'message':
            handle_message_event(event_data, event_data['event'])
        elif event_type == 'reaction_added':
            handle_reaction_event(event_data['event'])
        elif event_type == 'channel_created':
            handle_channel_created_event(event_data['event'])
        elif event_type == 'member_joined_channel':
            handle_member_joined_channel_event(event_data['event'])
        event_queue.task_done()

if __name__ == "__main__":
    load_last_active_channel()
    event_processing_thread = threading.Thread(target=process_events)
    event_processing_thread.daemon = True
    event_processing_thread.start()
    app.run(port=3000)
