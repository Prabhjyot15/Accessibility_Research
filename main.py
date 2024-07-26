import os
from speak import say
from listen import takeCommand
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from greeting import greetMe

# Constants
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')


# Setup Slack client
client = WebClient(token=SLACK_BOT_TOKEN)

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

if __name__ == "__main__":
    while True:
        query = takeCommand()
        if query is None:
            say("Sorry, could not understand audio.")
            continue

        if "hello" in query or "hi" in query or "hey" in query or "wake up" in query:
            greetMe()

            while True:
                query = takeCommand()
                if query is None:
                    say("Sorry, could not understand audio.")
                    continue

                if ("thank you" in query) or ("bye" in query) or ("take a break" in query):
                    say("You're welcome! If you have any more questions or if there's anything else you'd like to know, feel free to ask. I'm here to help!")
                    exit()

                elif "create channel" in query:
                    say("Do you want me to read aloud the keyboard shortcuts for creating a channel?")
                    response = takeCommand()
                    if response is None:
                        say("Sorry, could not understand audio.")
                        continue

                    response = response.lower()
                    if "yes" in response or "sure" in response:
                        read_shortcut_create_channel()
                    else:
                        channel_name = query.split("create channel")[-1].strip()
                        channel_id = create_channel(channel_name)
                        if channel_id:
                            say(f"Channel {channel_name} created successfully.")
                        else:
                            say("Failed to create channel.")

                elif "open threads" in query:
                    say("Do you want me to read aloud the keyboard shortcuts for opening threads?")
                    response = takeCommand()
                    if response is None:
                        say("Sorry, could not understand audio.")
                        continue

                    response = response.lower()
                    if "yes" in response or "sure" in response:
                        read_shortcut_open_threads()
                    else:
                        # Implement the functionality for opening threads if available
                        say("Functionality for opening threads is not implemented yet.")

                elif "open mentions and reactions" in query:
                    say("Do you want me to read aloud the keyboard shortcuts for opening mentions and reactions?")
                    response = takeCommand()
                    if response is None:
                        say("Sorry, could not understand audio.")
                        continue

                    response = response.lower()
                    if "yes" in response or "sure" in response:
                        read_shortcut_open_mentions_reactions()
                    else:
                        # Implement the functionality for opening mentions and reactions if available
                        say("Functionality for opening mentions and reactions is not implemented yet.")

                elif "open drafts" in query:
                    say("Do you want me to read aloud the keyboard shortcuts for opening drafts?")
                    response = takeCommand()
                    if response is None:
                        say("Sorry, could not understand audio.")
                        continue

                    response = response.lower()
                    if "yes" in response or "sure" in response:
                        read_shortcut_open_drafts()
                    else:
                        # Implement the functionality for opening drafts if available
                        say("Functionality for opening drafts is not implemented yet.")

                elif "open direct messages" in query:
                    say("Do you want me to read aloud the keyboard shortcuts for opening direct messages?")
                    response = takeCommand()
                    if response is None:
                        say("Sorry, could not understand audio.")
                        continue

                    response = response.lower()
                    if "yes" in response or "sure" in response:
                        read_shortcut_open_direct_messages()
                    else:
                        # Implement the functionality for opening direct messages if available
                        say("Functionality for opening direct messages is not implemented yet.")

                elif "active users" in query:
                    active_users = get_active_users()
                    if active_users:
                        say(f"Active users are: {', '.join(active_users)}.")
                    else:
                        say("Failed to fetch active users.")
