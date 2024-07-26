import datetime
from speak import say

def greetMe():
    hour  = int(datetime.datetime.now().hour)
    if hour>=0 and hour<=12:
        say("Good Morning! How may I help you?")
    elif hour >12 and hour<=18:
        say("Good Afternoon! How may I help you?")

    else:
        say("Good Evening! How may I help you?")
