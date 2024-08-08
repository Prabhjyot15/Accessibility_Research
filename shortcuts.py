import nltk
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize
from fuzzywuzzy import process, fuzz
nltk.download('punkt')

ps = PorterStemmer()

shortcuts_map = {
    "Switch to the previous workspace": "Ctrl + Shift + Tab",
    "Switch to the next workspace": "Ctrl + Tab",
    "Switch to a specific workspace": "Ctrl + (workspace number)",
    "Jump to a conversation": "Ctrl + K",
    "Open the Threads view": "Ctrl + Shift + T",
    "Open the Mentions & reactions view": "Ctrl + Shift + M",
    "Open the All unreads view": "Ctrl + Shift + A",
    "Open the People view": "Ctrl + Shift + E",
    "Open the Saved items view": "Ctrl + Shift + S",
    "Open the Files view": "Ctrl + Shift + F",
    "Open the Direct messages view": "Ctrl + Shift + K",
    "Open the Drafts view": "Ctrl + Shift + D",
    "Open the Preferences menu": "Ctrl + ,",
    "Open or close the right pane": "Ctrl + .",
    "Go to the previous channel or DM": "Alt + Up Arrow",
    "Go to the next channel or DM": "Alt + Down Arrow",
    "Toggle the left pane": "Ctrl + Shift + L",
    "Toggle the full screen mode": "Ctrl + Shift + F",
    "Search the current channel or conversation": "Ctrl + F",
    "Set a reminder": "/remind",
    "Mark all messages as read": "Esc",
    "Edit your last message": "↑ (up arrow)",
    "Add a reaction to the last message": "+ (plus)",
    "Open or close the emoji picker": "Ctrl + Shift + \\",
    "Move focus to the next section": "F6",
    "Move focus to the previous section": "Shift + F6",
    "Create a new direct message": "Ctrl + Shift + K",
    "Upload a file": "Ctrl + U",
    "Start a call": "Ctrl + Shift + Enter",
    "Toggle mute": "Ctrl + Shift + M",
    "Toggle video": "Ctrl + Shift + V",
    "Share your screen": "Ctrl + Shift + S",
    "Leave the call": "Ctrl + Shift + H"
}

def preprocess_text(text):
    tokens = word_tokenize(text.lower())
    stemmed_tokens = [ps.stem(token) for token in tokens]
    return ' '.join(stemmed_tokens)

preprocessed_actions = {
    preprocess_text(action): action for action in shortcuts_map.keys()
}

def get_best_match(query):
    query_processed = preprocess_text(query)
    actions = list(preprocessed_actions.keys())
    print(f"Processed Query: {query_processed}")  # Debugging line
    best_match, score = process.extractOne(query_processed, actions, scorer=fuzz.token_sort_ratio)
    print(f"Best Match: {best_match}, Score: {score}")  # Debugging line
    # Adjusting threshold for better matching
    if score >= 60:
        return preprocessed_actions.get(best_match, None)
    return None