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
from state import SLACK_BOT_TOKEN, user_state
from botFunc import (format_event_response, get_nvda_focus, nvda_speak, open_bot_dm, load_last_active_channel, get_channel_members, 
                     get_current_user_id, extract_channel_name, provide_channel_link, 
                     create_channel, get_active_users, navigate_messages, switch_channel, 
                     read_all_shortcuts, read_shortcut_create_channel, 
                     read_shortcut_open_direct_messages, read_shortcut_open_drafts, 
                     read_shortcut_open_mentions_reactions, read_shortcut_open_threads, 
                     scrape_slack_dom_elements, provide_help, answer_general_question, 
                     get_workspace_info, get_context_from_web, workspace_information)
from eventHandler import (handle_message_event, handle_channel_created_event, 
                          handle_member_joined_channel_event, handle_reaction_event)
from calendar_integration import authenticate_google_calendar, create_event
import datetime
import dateparser
import pytz

# download('wordnet')
# download('punkt')
load_dotenv()


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

client = WebClient(token=SLACK_BOT_TOKEN)

load_and_train_model()

event_queue = queue.Queue()

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.json
    if data and 'event' in data and 'user' in data['event']:
        user_id = data['event']['user']
        print(user_id)
        user_state['user_id'] = user_id
    if 'challenge' in data:
        return jsonify({'challenge': data['challenge']})

    if 'event' in data:
        event_type = data['event']['type']
        if data.get('type') == 'message' and 'user' in data['event']:
            user_state['user_id'] = data['event']['user']
        if event_type in ['message', 'reaction_added', 'channel_created', 'member_joined_channel']:
            event_queue.put(data)
            return jsonify({'status': 'ok'})
    return jsonify({'status': 'ok'})

@app.route('/slack/command', methods=['POST'])
def slack_command():
    data = request.form
    text = data.get('text').lower()
    if data.get('command') == '/slackally':
        open_bot_dm()
        return jsonify({
            "response_type": "ephemeral",
            "text": "Opening a DM with the bot..."
        })
    elif data.get('command') == '/whereami':
        message = "You have executed the where am I command."
        nvda_speak(message)  # Make NVDA speak the message

        response_text = f"NVDA is speaking: {message}"
        return jsonify({
            "response_type": "ephemeral",
            "text": response_text
        })
        # current_focus = get_nvda_focus()
        # # response_text = f"Current NVDA Focus: {current_focus}"
        # return jsonify({
        #     "response_type": "ephemeral",
        #     "text": current_focus
        # })
    elif data.get('command') == '/setupevent':
        print("Processing the command...")
        service = authenticate_google_calendar()

        # Split the text to extract the event details and date-time part
        parts = text.split(" on ")
        if len(parts) == 2:
            event_info = parts[0].strip()
            event_date_time = parts[1].strip()

            # Further split the date and time range
            date_time_parts = event_date_time.split(" from ")
            if len(date_time_parts) == 2:
                event_date = date_time_parts[0].strip()
                time_range = date_time_parts[1].strip()

                # Split the time range into start and end times
                start_time_str, end_time_str = time_range.split(" to ")

                # Parse the date and time
                parsed_date = dateparser.parse(event_date)
                parsed_start_time = dateparser.parse(start_time_str)
                parsed_end_time = dateparser.parse(end_time_str)

                if parsed_date and parsed_start_time and parsed_end_time:
                    # Combine date with start and end times
                    start_datetime = datetime.datetime.combine(parsed_date.date(), parsed_start_time.time())
                    end_datetime = datetime.datetime.combine(parsed_date.date(), parsed_end_time.time())

                    # Assume the event is in PST time zone
                    timezone = pytz.timezone('America/Los_Angeles')
                    start_time = timezone.localize(start_datetime)
                    end_time = timezone.localize(end_datetime)

                    # Use the part before "on" as the summary for the event
                    summary = event_info  # This takes whatever the user wrote before "on"
                    description = "Scheduled via Slack bot."

                    # Create the event
                    event = create_event(service, summary, description, start_time.isoformat(), end_time.isoformat())

                    # Format the event response using the separate function
                    response_text = format_event_response(event, summary, start_time, end_time)

                    return jsonify({
                        "response_type": "ephemeral",
                        "text": response_text
                    })
        
        return jsonify({
            "response_type": "ephemeral",
            "text": "Could not parse the date/time. Please ensure the command is in the correct format."
        })

    return jsonify({
        "response_type": "ephemeral",
        "text": "Command not recognized."
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
