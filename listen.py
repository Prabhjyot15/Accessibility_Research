import speech_recognition as sr

def takeCommand():
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        print("Listening...")
        # Maximum amount of silence that the recognizer will allow before considering a phrase as complete
        recognizer.pause_threshold = 0.75
        recognizer.adjust_for_ambient_noise(source)  # Adjust for background noise before recording
        audio = recognizer.listen(source) # Can make it (source, 0, x) to listen for 'x' seconds

    try:
        print("Recognizing...")
        recognized_text = recognizer.recognize_google(audio, language="en-in") # add expected language for accurate results
        print(f"\nUser: {recognized_text}")
    
    except sr.UnknownValueError:
        print("\nSorry, could not understand audio.")
        return None
    
    except sr.RequestError as e:
        print(f"\nCould not request results from Google Web Speech API; {e}")
        return None
    
    return str(recognized_text).lower()

# Listen()
