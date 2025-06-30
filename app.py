from flask import Flask, render_template, request, redirect, flash
import os
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
                flash(f'{filename} saved locally at {filepath}')
            else:
                flash(f'Skipped invalid file: {file.filename}')

        return redirect('/')

    return render_template('index.html')


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
