import pyttsx3

def say(text):
    # Initialize the TTS engine using the "sapi5" backend
    engine = pyttsx3.init("sapi5")
    voices = engine.getProperty('voices') # Available voices
    engine.setProperty('voices',voices[0].id) # Set the first voice
    engine.setProperty('rate',170) # Speech Rate- Words per minute
    print(f"\nAssistant: {text}")
    engine.say(text)
    engine.runAndWait()

# say("Hello!")