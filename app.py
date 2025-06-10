from flask import Flask, render_template, request, redirect, flash
import os
from werkzeug.utils import secure_filename
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

GOOGLE_DRIVE_FOLDER_ID = '1AORGxaPtjID9xdY--ezEKaWc-PZgQm4O'  # Replace with your actual folder ID
SERVICE_ACCOUNT_FILE = 'service_account.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

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
    if request.method == 'POST':
        if 'images' not in request.files:
            flash('No files found in request')
            return redirect(request.url)

        files = request.files.getlist('images')
        if not files or all(file.filename == '' for file in files):
            flash('No files selected')
            return redirect(request.url)

        for file in files:
            if file and allowed_file(file.filename) and file.content_type.startswith('image/'):
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

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
