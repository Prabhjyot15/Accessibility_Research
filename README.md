# voice-assistant
    .venv/Scripts/Activate.ps1
add .env file to load the slackbot token
to run bot: python main.py
to run backend: python backend.py (for events api/ haven't implemented that completely yet)
ngrok http 3000
Enable Event Subscriptions.
Set the Request URL to your Ngrok URL followed by /slack/events (e.g., https://your-ngrok-url.ngrok.io/slack/events).

steps:
first terminal:
.venv/Scripts/Activate.ps1
python backend.py

second terminal:
.venv/Scripts/Activate.ps1
python keyboard_listener.py

<!-- third terminal:
.venv/Scripts/Activate.ps1
python switch_back.py -->


pc's terminal:
ngrok http 3000
Enable Event Subscriptions.
Set the Request URL to your Ngrok URL followed by /slack/events (e.g., https://your-ngrok-url.ngrok.io/slack/events).

we're probably not using switch_back.py. cross check
