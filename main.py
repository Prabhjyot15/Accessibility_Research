from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from speak import say
from listen import takeCommand
from greeting import greetMe
from config import Config
from sklearn.linear_model import LogisticRegression
from botFunc import conversation_state
from dotenv import load_dotenv
from transformers import pipeline
import requests
from bs4 import BeautifulSoup
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, classification_report
import json
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.utils import resample
from botFunc import extract_channel_name, provide_channel_link,create_channel,get_active_users,navigate_messages, switch_channel, read_all_shortcuts,read_shortcut_create_channel,read_shortcut_open_direct_messages,read_shortcut_open_drafts,read_shortcut_open_mentions_reactions,read_shortcut_open_threads,switch_channel,scrape_slack_dom_elements,provide_help,answer_general_question,get_workspace_info,get_context_from_web

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')

#client = WebClient(token=SLACK_BOT_TOKEN)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Global state to perform follow ups

def load_and_train_model():
    with open('data.json', 'r') as f:
        data = json.load(f)

    # Convert JSON data to DataFrame
    df = pd.DataFrame(data)

    # Determine the class with the most examples
    max_class_size = df['intent'].value_counts().max()

    # Separate the data by intent
    df_majority = df[df['intent'] == 'create channel']
    df_workspace = df[df['intent'] == 'workspace overview']
    df_help = df[df['intent'] == 'help']
    df_greeting = df[df['intent'] == 'greeting']
    df_general = df[df['intent'] == 'general']

    # Resample the minority classes by duplicating them
    df_workspace_upsampled = resample(df_workspace, 
                                  replace=True,    
                                  n_samples=max_class_size,    
                                  random_state=42)

    df_help_upsampled = resample(df_help, 
                             replace=True, 
                             n_samples=max_class_size, 
                             random_state=42)

    df_greeting_upsampled = resample(df_greeting, 
                                 replace=True, 
                                 n_samples=max_class_size, 
                                 random_state=42)

    df_general_upsampled = resample(df_general, 
                                 replace=True, 
                                 n_samples=max_class_size, 
                                 random_state=42)

    # Combine the upsampled minority classes with the majority class
    df_balanced = pd.concat([df_majority, df_workspace_upsampled, df_help_upsampled, df_greeting_upsampled, df_general_upsampled])

    # Shuffle the dataset
    df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)

    # Save the balanced dataset to a new JSON file
    balanced_data = df_balanced.to_dict(orient='list')
    with open('balanced_data.json', 'w') as f:
        json.dump(balanced_data, f)


    # TF-IDF Vectorization
    vectorizer = TfidfVectorizer(lowercase=True, stop_words='english', ngram_range=(1, 2), max_features=5000)
    X = vectorizer.fit_transform(df_balanced['text'])
    y = df_balanced['intent']

    # Split data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Model training with Logistic Regression
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    return model, vectorizer

model, vectorizer = load_and_train_model()

# Function to determine user's query intent
def determine_intent(query):
    new_sentence_vectorized = vectorizer.transform([query])
    predicted_intent = model.predict(new_sentence_vectorized)
    return predicted_intent[0]

@app.route('/api/command', methods=['POST'])
def command():
    data = request.json
    query = data.get('query', '').lower()
    response_text = ""

    # Determining intent
    intent = determine_intent(query)
    if conversation_state.get('awaiting_follow_up') == 'create_channel':
        if "yes" in query:
            channel_name = query.split()[-1].strip()
            channel_name = extract_channel_name(channel_name)
            print("CHANNELLLL NAME")
            channel_id = create_channel(channel_name)
            print(channel_id)
            if channel_id:
                response_text = f"Channel {channel_name} created successfully."
            else:
                response_text = "Failed to create channel."
        elif "no" in query:
            response_text = "Okay, I won't create the channel."
        conversation_state['awaiting_follow_up'] = None

        return jsonify({"response": response_text})
    elif conversation_state.get('awaiting_follow_up') == 'channel_members':
        workspace_info = conversation_state.get('workspace_info', {})
        channel_members = workspace_info.get('channel_members', [])
        if channel_members:
            response_text = f"Channel members: {', '.join(channel_members)}\nDo you want me to tell you who is online? Please say yes or no"
            conversation_state['awaiting_follow_up'] = 'online_users'
        else:
            response_text = "Failed to fetch channel members.\nDo you want me to tell you who is online? Please say yes or no"
            conversation_state['awaiting_follow_up'] = 'online_users'

    elif conversation_state.get('awaiting_follow_up') == 'online_users':
        if "yes" in query and conversation_state.get('awaiting_follow_up') == 'online_users':
            workspace_info = conversation_state.get('workspace_info', {})
            online_users = workspace_info.get('online_users', [])
        if online_users:
            response_text = f"Online users: {', '.join(online_users)}"
        else:
            response_text = "No users are currently online."
        conversation_state['awaiting_follow_up'] = None

    elif "no" in query and conversation_state.get('awaiting_follow_up') == 'online_users':
        response_text = "Okay, I won't read out the names of online users."
        conversation_state['awaiting_follow_up'] = None

    elif "no" in query and conversation_state.get('awaiting_follow_up') == 'channel_members':
        response_text = "Okay, I won't read out the channel members.\nDo you want me to tell you who is online? Please say yes or no"
        conversation_state['awaiting_follow_up'] = 'online_users'

    elif intent == "greeting":
        #greetMe()
        response_text = "Hello! How can I assist you today?"

    elif intent == "fetch slack elements":
        print(f"Received command: {query}")  # Debugging print
        scrape_slack_dom_elements()
        response_text = "Slack elements fetched. Check the console for details."

    elif intent == "create channel":
        say("Do you want me to read aloud the keyboard shortcuts for creating a channel? yes or no")
        conversation_state['awaiting_follow_up'] = 'read_shortcut'
        #conversation_state['channel_name'] = query.split("create channel")[-1].strip()

    # Handling follow-up response for reading shortcuts
    elif conversation_state.get('awaiting_follow_up') == 'read_shortcut':
        if "yes" in query:
            read_shortcut_create_channel()
            say("Do you want me to create the channel for you? Please say 'yes' with the channel name or 'no' to cancel.")
            conversation_state['awaiting_follow_up'] = 'create_channel'
        elif "no" in query:
            say("Do you want me to create the channel for you? Please say 'yes' with the channel name or 'no' to cancel.")
            conversation_state['awaiting_follow_up'] = 'create_channel'

    elif intent == "workspace overview":
        workspace_info = get_workspace_info()
        if workspace_info:
            response_text = (
                f"You are currently in the workspace: {workspace_info['workspace']}\n"
                f"Number of unread messages: {workspace_info['unread_messages']}\n"
                f"Number of online users: {len(workspace_info['online_users'])}\n"
                f"Channels:\n"
                + '\n'.join(f" Unread messages: {channel['unread_messages']}" for channel in workspace_info['channels']) + '\n'
                f"Do you want me to read out the channel members? Please say yes or no"
        )
            conversation_state['awaiting_follow_up'] = 'channel_members'
            conversation_state['workspace_info'] = workspace_info
        else:
            response_text = "Failed to fetch workspace information."

# Handling follow-up response for online users
    elif "yes" in query and conversation_state.get('awaiting_follow_up') == 'online_users':
        workspace_info = conversation_state.get('workspace_info', {})
        online_users = workspace_info.get('online_users', [])
        if online_users:
            response_text = f"Online users: {', '.join(online_users)}"
        else:
            response_text = "No users are currently online."
        conversation_state['awaiting_follow_up'] = None

    elif "no" in query and conversation_state.get('awaiting_follow_up') == 'online_users':
        response_text = "Okay, I won't read out the names of online users."
        conversation_state['awaiting_follow_up'] = None

    #WIP
    elif intent == "general":
        response_text = "How can I help you"

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

    else:
        response_text = answer_general_question(query) 
    say(response_text)
    return jsonify({'response': response_text})

if __name__ == "__main__":
    app.run(port=3000)
    takeCommand()
