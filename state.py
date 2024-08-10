import os


# Global conversation state for message follow ups
conversation_state = {}

# Global state to track processed messages
processed_messages = set()

# Global state to track last channel/DM
last_active_channel = {}
LAST_ACTIVE_CHANNEL_FILE = 'last_active_channel.json'

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_USER_ID = os.getenv('SLACK_USER_ID')
BATCH_FILE_PATH = 'OpenSlackbotChat.bat' 