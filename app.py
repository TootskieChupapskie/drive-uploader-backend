import os
import pickle
from flask import Flask, request, redirect
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

app = Flask(__name__)
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'client_secret.json'
TOKEN_FILE = 'token.pickle'

def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

@app.route('/')
def index():
    return '✅ Drive uploader is running.'

@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files or 'username' not in request.form:
            return '❌ Missing file or username', 400

        file = request.files['file']
        username = request.form['username'].strip().upper()
        filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"

        service = get_drive_service()

        # Check or create folder
        folder_query = (
            f"name = '{username}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        )
        results = service.files().list(q=folder_query, fields="files(id, name)").execute()
        folders = results.get('files', [])

        if not folders:
            folder_metadata = {
                'name': username,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder['id']
        else:
            folder_id = folders[0]['id']

        media = MediaInMemoryUpload(file.read(), mimetype='text/csv')
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }

        uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        return f"✅ File uploaded to Drive with ID: {uploaded.get('id')}", 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ Internal error: {str(e)}", 500

if __name__ == '__main__':
    app.run(port=5000)
