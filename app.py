import time
import json
from flask import Flask, render_template, request, redirect, flash
import os
from werkzeug.utils import secure_filename
import boto3

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv'}

with open('service_account.json') as f:
    creds = json.load(f)

os.environ['AWS_ACCESS_KEY_ID'] = creds['AWS_ACCESS_KEY_ID']
os.environ['AWS_SECRET_ACCESS_KEY'] = creds['AWS_SECRET_ACCESS_KEY']
os.environ['AWS_DEFAULT_REGION'] = creds['AWS_DEFAULT_REGION']

# Initialize the S3 client globally (once)
s3 = boto3.client('s3', region_name=os.getenv('AWS_DEFAULT_REGION'))

BUCKET_NAME = 'wedding-photo-uploader'


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
            if file and allowed_file(file.filename) and (file.content_type.startswith('image/') or file.content_type.startswith('video/')):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)

                # Upload the file to S3
                try:
                    s3.upload_file(filepath, BUCKET_NAME, filename)
                    flash(f'{filename} uploaded.')
                except Exception as e:
                    flash(f'Failed to upload {filename} to S3. Error: {str(e)}')
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

