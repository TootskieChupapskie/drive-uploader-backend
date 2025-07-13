import os
import pickle
import base64
from flask import Flask, request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from datetime import datetime

app = Flask(__name__)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    creds = None

    # Load token.pickle from base64 string stored in environment
    token_b64 = os.environ.get("TOKEN_PICKLE_B64")
    if token_b64:
        creds = pickle.loads(base64.b64decode(token_b64))

    if not creds or not creds.valid:
        # Load client_secret.json from environment
        client_secret_json = os.environ.get("CLIENT_SECRET_JSON")
        if not client_secret_json:
            raise Exception("Missing CLIENT_SECRET_JSON in environment")

        # Write to temp file since InstalledAppFlow expects a file
        with open("temp_client_secret.json", "w") as f:
            f.write(client_secret_json)

        flow = InstalledAppFlow.from_client_secrets_file("temp_client_secret.json", SCOPES)
        creds = flow.run_local_server(port=0)

        # Save token as base64 to set it back in environment later
        token_data = base64.b64encode(pickle.dumps(creds)).decode("utf-8")
        print(f"🔐 TOKEN_PICKLE_B64={token_data}")
        # In production, you'd want to save this elsewhere instead of printing

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
