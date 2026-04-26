from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.tools.gmail_tool import GMAIL_SCOPES

creds = Credentials.from_authorized_user_file('token.json', GMAIL_SCOPES)
svc = build('gmail', 'v1', credentials=creds)

# Get the Chandrika webform email — take the unread one
results = svc.users().messages().list(userId='me', q='chandrika in:inbox', maxResults=3).execute()
msgs = results.get('messages', [])

for m in msgs:
    full = svc.users().messages().get(userId='me', id=m['id'], format='full').execute()
    headers = {h['name']: h['value'] for h in full['payload']['headers']}
    print('=' * 60)
    print('From:', headers.get('From'))
    print('Reply-To:', headers.get('Reply-To'))
    print('Return-Path:', headers.get('Return-Path'))
    print('Subject:', headers.get('Subject'))
    print('Labels:', full.get('labelIds', []))
    print()

    # Decode body
    import base64
    def get_body(part):
        if part.get('body', {}).get('data'):
            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
        for sub in part.get('parts', []):
            body = get_body(sub)
            if body:
                return body
        return ''
    
    body = get_body(full['payload'])
    print('BODY SNIPPET:')
    print(body[:500])
    print()
