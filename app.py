from flask import Flask, request, render_template, redirect, session
from flask import send_from_directory
import csv, os
from werkzeug.utils import secure_filename
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json

app = Flask(__name__)
app.secret_key = 'bird-secret'

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SERVICE_JSON = os.environ.get("GOOGLE_SERVICE_JSON")
SERVICE_ACCOUNT_INFO = json.loads(SERVICE_JSON)
DRIVE_FOLDER_ID = "1thenIO-t4zaAM0aJ25PaMXSB8WnbeIdG"
DRIVE_DATA_CSV_FILE_ID = "1MFwTeNHZ7uEs-2TbOY-wOovFj64h3o3k"

def upload_file_to_drive(local_path, filename):
    creds = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO)
    service = build("drive", "v3", credentials=creds)
    file_metadata = {'name': filename, 'parents': [DRIVE_FOLDER_ID]}
    media = MediaFileUpload(local_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get("id")

def download_csv_from_drive(file_id, local_path):
    creds = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO)
    service = build('drive', 'v3', credentials=creds)
    request = service.files().get_media(fileId=file_id)
    with open(local_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

def append_to_csv(local_path, row_dict):
    file_exists = os.path.exists(local_path)
    with open(local_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=row_dict.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row_dict)

def overwrite_drive_file(local_path, file_id):
    creds = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO)
    service = build('drive', 'v3', credentials=creds)
    media = MediaFileUpload(local_path, resumable=True)
    service.files().update(fileId=file_id, media_body=media).execute()

@app.route('/')
def index():
    return render_template("form.html")
    
##@app.route('/uploads/<filename>')
##def uploaded_file(filename):
##    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/confirm', methods=['POST'])
def confirm():
    form = request.form.to_dict(flat=True)
    file = request.files.get('file')

    if file and file.filename:
        filename = secure_filename(file.filename)
        local_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(local_path)
        drive_file_id = upload_file_to_drive(local_path, filename)
        form['file'] = f"https://drive.google.com/file/d/{drive_file_id}/view"
    else:
        form['file'] = ""

    required = ['01_species', '02_date', '12_observer', '13_email']
    if not all(form.get(k) for k in required):
        return "必須項目が不足しています。戻って修正してください。"
    if not form.get('03_location_text') and (not form.get('04_latitude') or not form.get('04_longitude')):
        return "観察場所（テキストまたは座標）のいずれかを入力してください。"

    session['form'] = form
    return render_template("confirm.html", data=form)

@app.route('/submit', methods=['POST'])
def submit():
    data = session.pop('form', None)
    if not data:
        return redirect('/')

    # 1. Driveからdata.csvをダウンロード
    local_path = "/tmp/data.csv"
    download_csv_from_drive(DRIVE_DATA_CSV_FILE_ID, local_path)

    # 2. 追記
    append_to_csv(local_path, data)

    # 3. Driveへ再アップロード（上書き）
    overwrite_drive_file(local_path, DRIVE_DATA_CSV_FILE_ID)

    return "<h2>報告ありがとうございました！（Google Driveに追記しました）</h2><a href='/'>戻る</a>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
