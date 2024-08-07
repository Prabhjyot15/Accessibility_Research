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
from sklearn.utils import resample
from botFunc import get_channel_members,get_current_user_id,list_active_channels,extract_channel_name, provide_channel_link,create_channel,get_active_users,navigate_messages, switch_channel, read_all_shortcuts,read_shortcut_create_channel,read_shortcut_open_direct_messages,read_shortcut_open_drafts,read_shortcut_open_mentions_reactions,read_shortcut_open_threads,switch_channel,scrape_slack_dom_elements,provide_help,answer_general_question,get_workspace_info,get_context_from_web

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

    df = pd.DataFrame(data)

    max_class_size = df['intent'].value_counts().max()
    df_balanced = pd.concat([
        resample(df[df['intent'] == intent], replace=True, n_samples=max_class_size, random_state=42)
        for intent in df['intent'].unique()
    ])
    df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)

    X = df_balanced['text']
    y = df_balanced['intent']

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

def determine_intent(query):
    query = query.lower().strip() 
    predicted_intent = model.predict([query])
    return predicted_intent[0]


@app.route('/api/command', methods=['POST'])
def command():
    data = request.json
    query = data.get('query', '').lower()
    response_text = ""
    print(conversation_state.get('awaiting_follow_up') )
    # Determining intent
    intent = determine_intent(query)
    print(intent)
    print(conversation_state.get('awaiting_follow_up') )
    if query == "where am i":
        response_text = workspace_information()

    elif conversation_state.get('awaiting_follow_up') == 'create_channel':
        print("right state")
        if "yes" in query:
            channel_name = query.split()[-1].strip()
            channel_name = extract_channel_name(channel_name)
            channel_id = create_channel(channel_name)
            print(channel_id)
            if channel_id:
                response_text = f"Channel {channel_name} created successfully."
            else:
                response_text = "Failed to create channel."
        elif "no" in query:
            say("Okay, I won't create the channel.")
            response_text = "Okay, I won't create the channel."
        conversation_state['awaiting_follow_up'] = None

        return jsonify({"response": response_text})
    # elif conversation_state.get('awaiting_follow_up') == 'channel_members':
    #     workspace_info = conversation_state.get('workspace_info', {})
    #     print(workspace_info)
    #     channel_members = workspace_info.get('channel_members', [])
    #     if "yes" in query:
    #         if channel_members:
    #             response_text = f"Channel members: {', '.join(channel_members)}\nDo you want me to tell you who is online? Please say yes or no"
    #             conversation_state['awaiting_follow_up'] = 'online_users'
    #         else:
    #             response_text = "Failed to fetch channel members.\nDo you want me to tell you who is online? Please say yes or no"
    #             conversation_state['awaiting_follow_up'] = 'online_users'
    elif conversation_state.get('awaiting_follow_up') == 'channel_members':
        channel_name = query.strip()
        res = get_channel_members(channel_name)
    
        if res:
            response_text = f"The members in {channel_name} are: {', '.join(res)}"
        else:
            response_text = f"Unable to fetch members for channel '{channel_name}'."
    
        conversation_state['awaiting_follow_up'] = None


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
            response_text = ("Okay, I won't read out the names of online users.")
            conversation_state['awaiting_follow_up'] = None

    elif "no" in query and conversation_state.get('awaiting_follow_up') == 'channel_members':
        response_text = "Okay, I won't read out the channel members.\nDo you want me to tell you who is online? Please say yes or no"
        conversation_state['awaiting_follow_up'] = 'online_users'

    elif conversation_state.get('awaiting_follow_up') == 'read_shortcut':
        if "yes" in query:
            read_shortcut_create_channel()
            say("Do you want me to create the channel for you? Please say 'yes' with the channel name or 'no' to cancel.")
            conversation_state['awaiting_follow_up'] = 'create_channel'
        elif "no" in query:
            say("Do you want me to create the channel for you? Please say 'yes' with the channel name or 'no' to cancel.")
            conversation_state['awaiting_follow_up'] = 'create_channel'

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

    elif intent == "list active channels":
        userid = get_current_user_id()
        res = list_active_channels(userid)
        response_text = "The user is active in the following channels:", res

    elif intent == "list channel members":
        conversation_state['awaiting_follow_up'] = 'channel_members'
        say("Please enter the channel name for which you want the member list:")   

    # Handling follow-up response for reading shortcuts

    elif intent == "workspace overview":
        response_text = workspace_information()

    #WIP
    elif intent == "general":
        response_text = "How can I help you"

    elif intent == "keyboard_shortcut":
        response_text = "Which shortcut do you need help with?"    

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
if __name__ == "__main__":
    app.run(port=3000)
    takeCommand()
