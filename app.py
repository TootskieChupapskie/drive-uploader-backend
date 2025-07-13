from datetime import datetime
from flask import Flask, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
import traceback
import os
import json

app = Flask(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.file']
PARENT_FOLDER_ID = '1SdU48QU_f2kC0prtj3Q-3a-8WTAqI_dM'  # Replace with your real parent folder ID

@app.route('/upload', methods=['POST'])
def upload():
    try:
        print("🔍 Incoming request to /upload")
        print("Headers:", dict(request.headers))
        print("Form Data:", request.form)
        print("Files:", request.files)

        if 'file' not in request.files or 'username' not in request.form:
            return '❌ Missing file or username', 400

        file = request.files['file']
        username = request.form['username'].strip().upper().rstrip(';:,.')
        filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        print(f"📁 Preparing to upload file: {filename} for user: {username}")

        # Load credentials from environment variable
        creds_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not creds_json:
            return '❌ Missing service account credentials in environment.', 500

        creds = service_account.Credentials.from_service_account_info(
            json.loads(creds_json),
            scopes=SCOPES
        )
        drive_service = build('drive', 'v3', credentials=creds)

        # Check if folder exists
        folder_query = (
            f"'{PARENT_FOLDER_ID}' in parents and "
            f"name = '{username}' and "
            f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        )
        print("🔍 Querying Drive for folder:", folder_query)
        response = drive_service.files().list(q=folder_query, fields="files(id, name)").execute()
        folders = response.get('files', [])

        if folders:
            folder_id = folders[0]['id']
            print(f"✅ Found folder ID: {folder_id}")
        else:
            print(f"📁 Folder '{username}' not found. Creating it...")
            folder_metadata = {
                'name': username,
                'parents': [PARENT_FOLDER_ID],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            created_folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = created_folder.get('id')
            print(f"✅ Created new folder with ID: {folder_id}")

        # Upload file
        media = MediaInMemoryUpload(file.read(), mimetype='text/csv')
        file_metadata = {
            'name': filename,
            'parents': [folder_id],
        }
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        print(f"✅ File uploaded successfully with ID: {uploaded_file.get('id')}")
        return '✅ Upload successful', 200

    except Exception as e:
        print("❌ Exception occurred:")
        traceback.print_exc()
        return f"Internal server error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
