from flask import Flask, render_template, request, redirect, flash, session, url_for
import os
from werkzeug.utils import secure_filename
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import time
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
import google.auth.transport.requests
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

GOOGLE_DRIVE_FOLDER_ID = '1AORGxaPtjID9xdY--ezEKaWc-PZgQm4O'  # Replace with your actual folder ID
CLIENT_SECRETS_FILE = "client_secret.json"  # Your downloaded OAuth JSON file

SCOPES = ['https://www.googleapis.com/auth/drive.file']

API_SERVICE_NAME = 'drive'
API_VERSION = 'v3'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def try_remove_file(path, retries=5, delay=0.2):
    for _ in range(retries):
        try:
            os.remove(path)
            return True
        except (PermissionError, OSError):
            time.sleep(delay)
    return False


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    creds_data = session['credentials']
    credentials = Credentials(
        token=creds_data['token'],
        refresh_token=creds_data.get('refresh_token'),
        token_uri=creds_data['token_uri'],
        client_id=creds_data['client_id'],
        client_secret=creds_data['client_secret'],
        scopes=creds_data['scopes']
    )

    drive_service = googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials)

    if request.method == 'POST':
        if 'images' not in request.files:
            flash('No files found in request')
            return redirect(request.url)

        files = request.files.getlist('images')
        if not files or all(file.filename == '' for file in files):
            flash('No files selected')
            return redirect(request.url)

        for file in files:
            if file and allowed_file(file.filename) and (file.content_type.startswith('image/') or file.content_type.startswith('video/')):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)

                try:
                    file_metadata = {
                        'name': filename,
                        'parents': [GOOGLE_DRIVE_FOLDER_ID]
                    }
                    media = MediaFileUpload(filepath, mimetype=file.content_type, resumable=True)
                    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                    flash(f'{filename} uploaded successfully!')
                except Exception as e:
                    flash(f'Error uploading {filename}: {e}')
                finally:
                    if os.path.exists(filepath):
                        try_remove_file(filepath)
            else:
                flash(f'Skipped invalid file: {file.filename}')

        return redirect('/')

    return render_template('index.html')


@app.route('/authorize')
def authorize():
    # Create flow instance to manage OAuth 2.0 Authorization Grant Flow steps
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES)

    flow.redirect_uri = url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    session['state'] = state

    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    # Save credentials in session for later use
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

    return redirect(url_for('index'))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
