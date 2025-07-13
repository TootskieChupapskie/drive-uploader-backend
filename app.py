import os
import pickle
import base64
from flask import Flask, request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime
import base64
import io
import json
from google.oauth2.credentials import Credentials

app = Flask(__name__)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    # Decode client secret from environment
    client_secret = json.loads(os.environ['CLIENT_SECRET_JSON'])

    # Decode token.pickle from base64
    token_data = base64.b64decode(os.environ['TOKEN_PICKLE_B64'])
    creds = pickle.load(io.BytesIO(token_data))

    # Use credentials to build the Drive service
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
    app.run(host="0.0.0.0", port=5000)
