from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.tools.gmail_tool import GMAIL_SCOPES

creds = Credentials.from_authorized_user_file('token.json', GMAIL_SCOPES)
svc = build('gmail', 'v1', credentials=creds)

# Search for Chandrika's email
results = svc.users().messages().list(userId='me', q='chandrika', maxResults=5).execute()
msgs = results.get('messages', [])
print('Found', len(msgs), 'messages matching chandrika')

for m in msgs:
    full = svc.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
    headers = {h['name']: h['value'] for h in full['payload']['headers']}
    labels = full.get('labelIds', [])
    print()
    print('From:', headers.get('From'))
    print('Subject:', headers.get('Subject'))
    print('Date:', headers.get('Date'))
    print('Labels:', labels)
    print('Is UNREAD?', 'UNREAD' in labels)
