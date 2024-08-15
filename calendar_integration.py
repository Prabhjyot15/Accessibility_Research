import datetime
import os
import pickle
import time
import google.auth
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_google_calendar():
    """Shows basic usage of the Google Calendar API.
    Returns a service object to interact with the calendar API."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    return service

def create_event(service, summary, description, start_time, end_time, attendees=[]):
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time,
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'America/Los_Angeles',
        },
        'attendees': [{'email': email} for email in attendees],
        'conferenceData': {
            'createRequest': {
                'requestId': f"meet-{int(time.time())}",
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet'
                }
            }
        },
    }

    event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1).execute()
    return event
if __name__ == '__main__':
    service = authenticate_google_calendar()
    event = create_event(
        service,
        'Meeting with Bob',
        'Discuss the quarterly report',
        '2024-08-20T15:00:00',
        '2024-08-20T16:00:00'
    )
    print('Event created: %s' % (event.get('htmlLink')))
