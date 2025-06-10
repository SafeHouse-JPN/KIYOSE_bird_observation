from flask import Flask, request, render_template, redirect, session
from flask import send_from_directory
import csv, os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'bird-secret'
UPLOAD_FOLDER = "uploads"
CSV_FILE = "data.csv"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template("form.html")
    
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/confirm', methods=['POST'])
def confirm():
    form = request.form.to_dict()
    file = request.files.get('file')
    if file and file.filename:
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        form['file'] = filename
        form['file_ext'] = file_ext
    else:
        form['file'] = ""
        form['file_ext'] = ""

    required = ['species', 'date', 'observer', 'email']
    if not all(form.get(k) for k in required):
        return "必須項目が不足しています。戻って修正してください。"
    if not form.get('location_text') and (not form.get('latitude') or not form.get('longitude')):
        return "観察場所（テキストまたは座標）のいずれかを入力してください。"

    session['form'] = form
    return render_template("confirm.html", data=form)

@app.route('/submit', methods=['POST'])
def submit():
    data = session.pop('form', None)
    if not data:
        return redirect('/')

    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)

    return "<h2>報告ありがとうございました！</h2><a href='/'>戻る</a>"

##if __name__ == '__main__':
##    app.run(debug=True)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # RenderがPORTを指定してくる
    app.run(host='0.0.0.0', port=port)
