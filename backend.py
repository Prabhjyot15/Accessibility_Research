import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from flask import Flask, request, jsonify

app = Flask(__name__)

# Replace with your Slack bot token
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')

client = WebClient(token=SLACK_BOT_TOKEN)

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.json

    # Handle Slack URL verification challenge
    if 'challenge' in data:
        return jsonify({'challenge': data['challenge']})

    # Process events
    if 'event' in data:
        event = data['event']
        if event['type'] == 'message' and 'subtype' not in event:
            user = event['user']
            text = event['text']
            channel = event['channel']
            print(f"Message from {user} in {channel}: {text}")

            # Example: Reply to the message
            try:
                response = client.chat_postMessage(
                    channel=channel,
                    text=f"Hello <@{user}>, you said: {text}"
                )
            except SlackApiError as e:
                print(f"Error posting message: {e.response['error']}")

    return jsonify({'status': 'ok'})

if __name__ == "__main__":
    app.run(port=3000)
