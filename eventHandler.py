from  botFunc import (
    save_last_active_channel,navigate_messages,workspace_information,
      greet_user,create_channel,extract_channel_name,provide_channel_link,send_message,
      scrape_slack_dom_elements,switch_channel,read_shortcut_create_channel,
      read_shortcut_create_channel,get_active_users,get_channel_members,
      get_context_from_web,get_current_user_id,get_workspace_info,answer_general_question,
      say,read_all_shortcuts,read_shortcut_open_direct_messages,read_shortcut_open_drafts,
      read_shortcut_open_mentions_reactions,read_shortcut_open_threads,list_active_channels)
from state import SLACK_BOT_TOKEN,conversation_state, processed_messages,BATCH_FILE_PATH,SLACK_USER_ID, last_active_channel
from model import determine_intent
from shortcuts import get_best_match
from slack_sdk import WebClient

client = WebClient(token=SLACK_BOT_TOKEN)

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
    response_text = ""
    print("conversation state", conversation_state.get('awaiting_follow_up'))
    # Ensure conversation state is initialized
    if channel not in conversation_state:
        conversation_state[channel] = {'responded': False, 'awaiting_channel_name': False}

    # Check if the bot has already responded to this specific message to avoid duplicates
    if conversation_state[channel]['responded']:
        print(f"Already responded to a greeting in channel {channel}.")
        return

    # Check for greetings
    if "hello" in text or "hi" in text or "hey" in text:
        try:
            response = client.users_info(user=user)
            user_name = response['user']['real_name'] 
        except:
            print("Error!")    
        send_message(channel, f"Hello {user_name}, how can I assist you today?")
        if channel not in conversation_state:
            conversation_state[channel] = {}

        conversation_state[channel]['responded'] = False
        return  # Early return to prevent further processing

    # Handle channel creation intent
    elif "create channel" in text or conversation_state[channel].get('awaiting_channel_name'):
        if conversation_state[channel].get('awaiting_channel_name'):
            handle_channel_creation(channel, text)
        else:
            send_message(channel, "What do you want to name the channel?")
            
        
        return  # Early return to prevent further processing

    # Handle "thank you"
    elif "thank you" in text:
        send_message(channel, "You're welcome! If you have any more questions or if there's anything else you'd like to know, feel free to ask. I'm here to help!")
        if channel in conversation_state:
            del conversation_state[channel]
        return  # Early return to prevent further processing

    # Handle help request
    # elif "help" in text:
    #     help_text = (
    #         "Here are the commands you can use:\n"
    #         "- 'Hello', 'Hi', 'Hey' to greet the bot.\n"
    #         "- 'Create channel' to create a new channel (you will be asked for the channel name).\n"
    #         "- 'Active users' to get a list of active users.\n"
    #         "- 'Help' to see this help message.\n"
    #         "- 'Thank you' to end the conversation."
    #     )
    #     send_message(channel, help_text)
        
    #     return  # Early return to prevent further processing

    # Handle workspace information request
    elif text == "where am i":
        response_text = workspace_information()
        send_message(channel, response_text)
        
        return  # Early return to prevent further processing

    # Handle follow-up actions like shortcuts
    elif conversation_state.get('awaiting_follow_up') == 'shortcut':
        matched_action = get_best_match(text)
        response_text = matched_action if matched_action else "Sorry, I couldn't find a matching shortcut."
        conversation_state['awaiting_follow_up'] = None
       # say(response_text)
        send_message(channel, response_text)
        
        return  # Early return to prevent further processing

    # Handle follow-up actions for channel members
    elif conversation_state.get('awaiting_follow_up') == 'channel_members':
        channel_name = text.strip()
        res = get_channel_members(channel_name)
        if res:
            response_text = f"The members in {channel_name} are: {', '.join(res)}"
        else:
            response_text = f"Unable to fetch members for channel '{channel_name}'."
        conversation_state['awaiting_follow_up'] = None
        send_message(channel, response_text)
        
        return  # Early return to prevent further processing
    
    elif conversation_state.get('awaiting_follow_up') == 'read_shortcut':
        if "yes" in text:
           # read_shortcut_create_channel()
            response_text = "Do you want me to create the channel for you? Please say 'yes' with the channel name or 'no' to cancel."
            conversation_state['awaiting_follow_up'] = 'create_channel'
            send_message(channel, response_text)
        elif "no" in text:
            response_text = "Do you want me to create the channel for you? Please say 'yes' with the channel name or 'no' to cancel."
            conversation_state['awaiting_follow_up'] = 'create_channel'
            send_message(channel, response_text)   
        return   

    elif conversation_state.get('awaiting_follow_up') == 'create_channel':
        if "yes" in text:
            channel_name = text.split()[-1].strip()
            channel_name = extract_channel_name(channel_name)
            channel_id = create_channel(channel_name)
            print(channel_id)
            if channel_id:
                response_text = f"Channel {channel_name} created successfully."
            else:
                response_text = "Failed to create channel."
            send_message(channel, response_text)    
        elif "no" in text:
            response_text = "Okay, I won't create the channel."
            send_message(channel, response_text)           
        conversation_state['awaiting_follow_up'] = None
        return

    # Handle follow-up actions for online users
    elif conversation_state.get('awaiting_follow_up') == 'online_users':
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
    # elif intent == "greeting":
    #     response_text = "Hello! How can I assist you today?"   
    #     send_message(channel, response_text)
    #     return
        

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
        conversation_state['awaiting_follow_up'] = 'online_users'
        send_message(channel, response_text)
        return

    elif intent == "general" or intent == "help":
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

def handle_message_event(data, event):
    message_id = event.get('client_msg_id')
    print(f"Processing message ID: {message_id}")

    if message_id in processed_messages:
        print(f"Duplicate message detected: {message_id}")
        return
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
            handle_direct_message(user, text, channel, intent)
        else:
            print(f"Already responded to a greeting in channel {channel}.")
        
        # Add the message ID to the processed set
        processed_messages.add(message_id)
    else:
        print(f"Ignoring message from channel {channel_type} channel {channel}")

