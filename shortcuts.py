import nltk
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer, PorterStemmer
from fuzzywuzzy import process, fuzz
import Levenshtein

ps = PorterStemmer()
# Download necessary NLTK resources
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('stopwords')

# Initialize stemmer and lemmatizer
lemmatizer = WordNetLemmatizer()
stopwords = set(nltk.corpus.stopwords.words('english'))
shortcuts_map = {
    "Compose a new message": "To DM a user, Press ⌘ K on Mac or Ctrl K on (Windows or Linux). Type the name of a channel or person into the search field. Press Enter to open the conversation",
    "Unsend a message": "Ctrl + Z",
    "Set your status": "/status",
    "Open your preferences": "Ctrl + ,",
    "Show or hide the left sidebar": "Ctrl + Shift + L",
    "Resize the left sidebar": "Alt + F6",
    "Hide the right sidebar": "Ctrl + .",
    "Create a new canvas": "Ctrl + Shift + N",
    "Upload a file": "Ctrl + U",
    "View all downloaded files": "Ctrl + J",
    "Create a new snippet": "Ctrl + Shift + Enter",
    "Add an emoji reaction to a message": "Ctrl + Shift + \\",
    "Start a search": "Ctrl + F",
    "Start, join, leave, or end a huddle": "Ctrl + Shift + H",
    "Toggle mute on a huddle": "Ctrl + Shift + M",
    "Toggle full screen view": "Ctrl + Shift + F",
    "Close window": "Ctrl + W",
    "Reopen last closed window": "Ctrl + Shift + T",
    "Open the People view": "Ctrl + Shift + E",
    "Quit Slack": "Ctrl + Q",
    "Jump to a conversation": "Ctrl + K",
    "Jump to the most recent unread message in a conversation": "Alt + Shift + Down Arrow",
    "Jump to previous unread channel or DM": "Alt + Shift + Up Arrow",
    "Jump to next unread channel or DM": "Alt + Shift + Down Arrow",
    "Jump to previous channel or DM in the sidebar": "Alt + Up Arrow",
    "Jump to next channel or DM in the sidebar": "Alt + Down Arrow",
    "Go back in history": "Alt + Left Arrow",
    "Go forward in history": "Alt + Right Arrow",
    "Open the Home view": "Ctrl + 1",
    "Browse DMs": "Ctrl + Shift + K",
    "Open the Activity view": "Ctrl + Shift + A",
    "View items in Later": "/remind",
    "Open the More view": "Ctrl + Shift + .",
    "Open the Threads view": "Ctrl + Shift + T",
    "Open conversation details": "Ctrl + Shift + C",
    "Move focus to the next section": "F6",
    "Move focus to the previous section": "Shift + F6",
    "Expand or collapse all sidebar sections": "Ctrl + Shift + A",
    "Mark all messages in current conversation as read": "Esc",
    "Mark all messages as read": "Ctrl + Shift + Esc",
    "Mark a message as unread": "Alt + Left Arrow",
    "Mark a group of messages as unread": "Shift + Esc",
    "Open or collapse a group of messages": "Ctrl + Shift + I",
    "Expand or collapse the workspace switcher": "Ctrl + Shift + W",
    "Switch to previous workspace": "Ctrl + Shift + Tab",
    "Switch to next workspace": "Ctrl + Tab",
    "Switch to a specific workspace": "Ctrl + [1-9]",
    "Switch to the previous tab": "Ctrl + Shift + [",
    "Switch to the next tab": "Ctrl + Shift + ]",
    "Edit a message you sent": "↑ (up arrow)",
    "Delete a message you sent": "Ctrl + Shift + Delete",
    "Open or reply to a thread": "Ctrl + Shift + T",
    "Forward a message": "Ctrl + F",
    "Pin or unpin a message": "Ctrl + Shift + P",
    "Save a message": "Ctrl + S",
    "Mark all messages above the one in focus as unread": "Ctrl + Shift + U",
    "Create a reminder about a message": "/remind",
    "Select text to beginning of current line": "Shift + Home",
    "Select text to end of current line": "Shift + End",
    "Create a new line": "Shift + Enter",
    "Bold selected text": "Ctrl + B",
    "Italicize selected text": "Ctrl + I",
    "Strikethrough selected text": "Ctrl + Shift + X",
    "Hyperlink selected text": "Ctrl + K",
    "Quote selected text": "Ctrl + Shift + 9",
    "Code selected text": "Ctrl + Shift + C",
    "Codeblock selected text": "Ctrl + Shift + Alt + C",
    "Format selected text as a bulleted list": "Ctrl + Shift + 8",
    "Format selected text as a numbered list": "Ctrl + Shift + 7",
    "Apply markdown formatting": "Ctrl + Shift + M",
    "Undo formatting": "Ctrl + Z",
    "Format selected text as paragraph": "Ctrl + Shift + P",
    "Format selected text as big heading": "Ctrl + Shift + 1",
    "Format selected text as medium heading": "Ctrl + Shift + 2",
    "Format selected text as small heading": "Ctrl + Shift + 3",
    "Format selected text as checklist": "Ctrl + Shift + L",
    "Toggle heading and list styles": "Ctrl + Shift + H",
    "View comment thread": "Ctrl + Shift + C",
    "Show reader or edit view": "Ctrl + Shift + E",
    "Open context menu": "Ctrl + Shift + M",
    "Find text in the canvas": "Ctrl + F",
    "Find next": "Ctrl + G",
    "Find previous": "Ctrl + Shift + G",
    "Find and replace": "Ctrl + H",
    "Copy anchor link to section": "Ctrl + Shift + K",
    "Undo last action": "Ctrl + Z",
    "Redo last action": "Ctrl + Y",
    "Move item in a formatted list up": "Alt + Shift + Up Arrow",
    "Move item in a formatted list down": "Alt + Shift + Down Arrow"
}


def preprocess_text(text, lowercase=True):
    if lowercase:
        text = text.lower()
    tokens = word_tokenize(text)
    tokens = [word for word in tokens if word.isalpha()]  # Remove punctuation
    tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stopwords]
    return ' '.join(tokens)

def get_contextual_synonyms(word, context="message"):
    synonyms = set()
    for synset in wordnet.synsets(word):
        for lemma in synset.lemmas():
            # Basic filtering based on context
            if context in synset.definition():
                synonyms.add(lemma.name())
    return synonyms

def expand_query(query, max_synonyms=5):
    words = query.split()
    expanded_query = query
    for word in words:
        synonyms = get_contextual_synonyms(word)
        expanded_query += " " + " ".join(sorted(synonyms)[:max_synonyms])
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    expanded_query += " " + " ".join(bigrams)
    return expanded_query

def get_best_match(query):
    query_processed = preprocess_text(query)
    expanded_query = expand_query(query_processed)
    actions = list(shortcuts_map.keys())
    
    # Perform fuzzy matching with combined scoring functions
    best_match, score_token_sort = process.extractOne(expanded_query, actions, scorer=fuzz.token_sort_ratio)

    # Calculate Levenshtein distance and normalize
    max_len = max(len(query_processed), len(max(actions, key=len)))
    score_levenshtein = max([1 - (Levenshtein.distance(query_processed, action) / max_len) for action in actions])
    
    # Combine scores with weights
    combined_score = 0.7 * score_token_sort + 0.3 * score_levenshtein
    
    # Debugging outputs
    print(f"Processed Query: {query_processed}")
    print(f"Expanded Query: {expanded_query}")
    print(f"Best Match: {best_match}")
    print(f"Token Sort Score: {score_token_sort}")
    print(f"Levenshtein Score: {score_levenshtein}")
    print(f"Combined Score: {combined_score}")

    # Return the action if combined score meets the threshold
    if score_token_sort >= 50:
        response_text = f"The shortcut for '{query}' is {shortcuts_map.get(best_match, None)}."
        return response_text
    
    # If the score is < 50, finding closest matches
    else:
        close_matches = process.extract(query, actions, scorer=fuzz.token_sort_ratio, limit=5)
        close_matches = [match for match, score in close_matches if score >= 30]

        if close_matches:
            response_text = f"No exact shortcut found for '{query}'. Did you mean:\n"
            response_text += "\n".join([f"- {match}: {shortcuts_map.get(match, None)}" for match in close_matches])
        else:
            response_text = "No close matches found. Please try again."

        return response_text
