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

def upload_file_to_drive(local_path, filename):
    creds = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO)
    service = build("drive", "v3", credentials=creds)
    file_metadata = {'name': filename, 'parents': [DRIVE_FOLDER_ID]}
    media = MediaFileUpload(local_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get("id")

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
    print("フォームデータ:", form)

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

    # CSVを一時ファイルとして保存
    csv_path = "/tmp/data.csv"
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

    # DriveへCSVアップロード
    drive_csv_id = upload_file_to_drive(csv_path, "data.csv")

    return f"<h2>報告ありがとうございました！</h2><p>CSVファイル（上書き）: <a href='https://drive.google.com/file/d/{drive_csv_id}/view'>こちら</a></p><a href='/'>戻る</a>"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
