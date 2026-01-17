"""親子資訊素養工作坊 - 檔案上傳系統 (Firebase 版)"""
import os
import json
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import csv
from io import StringIO, BytesIO
import zipfile

import firebase_admin
from firebase_admin import credentials, firestore, storage
from config import Config
import dotenv

dotenv.load_dotenv()

# 初始化 Flask 應用
app = Flask(__name__)
app.config.from_object(Config)

# ============== Firebase 初始化 ==============

def init_firebase():
    """初始化 Firebase Admin SDK"""
    cred = None
    
    # 1. 嘗試從環境變數讀取 (Zeabur 部署用)
    firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
    if firebase_creds:
        # 如果是 base64 編碼的 (有些平台需要)，先解碼
        try:
            if not firebase_creds.strip().startswith('{'):
                decoded_bytes = base64.b64decode(firebase_creds)
                creds_dict = json.loads(decoded_bytes.decode('utf-8'))
            else:
                creds_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(creds_dict)
            print("✓ 已從環境變數載入 Firebase 憑證")
        except Exception as e:
            print(f"⚠️ 環境變數 Firebase 憑證解析失敗: {e}")

    # 2. 如果環境變數失敗，嘗試從本地檔案讀取 (開發用)
    if not cred and os.path.exists('serviceAccountKey.json'):
        cred = credentials.Certificate('serviceAccountKey.json')
        print("✓ 已從本地檔案載入 Firebase 憑證")

    if cred:
        try:
            # 獲取 Storage Bucket 名稱 (從環境變數或預設)
            bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET')
            if not bucket_name and 'project_id' in cred.credential.service_account_email:
                # 嘗試從憑證推斷 (project-id.appspot.com)
                project_id = cred.credential.service_account_email.split('@')[0].split('.gserviceaccount')[0]
                # 注意：這可能不準確，最好明確指定
                # 通常 service account email 是: firebase-adminsdk-xxx@project-id.iam.gserviceaccount.com
                # 但更可靠的是直接設定 FIREBASE_STORAGE_BUCKET
                pass
            
            if not bucket_name:
                 print("⚠️ 未設定 FIREBASE_STORAGE_BUCKET，檔案上傳功能可能無法運作")

            firebase_admin.initialize_app(cred, {
                'storageBucket': bucket_name
            })
            print("✓ Firebase 初始化成功")
            return firestore.client()
        except ValueError:
            # 已經初始化過
            return firestore.client()
        except Exception as e:
            print(f"❌ Firebase 初始化錯誤: {e}")
            return None
    else:
        print("❌ 找不到 Firebase 憑證 (FIREBASE_CREDENTIALS env 或 serviceAccountKey.json)")
        return None

# 初始化資料庫客戶端
db = init_firebase()

# ============== 使用者模型 (適配 Flask-Login) ==============

class AdminUser(UserMixin):
    def __init__(self, uid, username, password_hash):
        self.id = uid
        self.username = username
        self.password_hash = password_hash
    
    @staticmethod
    def get(user_id):
        if not db: return None
        doc = db.collection('admins').document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            return AdminUser(user_id, data['username'], data['password_hash'])
        return None

# ============== Login Manager ==============

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = '請先登入以訪問此頁面'

@login_manager.user_loader
def load_user(user_id):
    return AdminUser.get(user_id)


# ============== 輔助函數 ==============

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def format_file_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def ensure_admin_exists():
    """確保預設管理員存在 (類似 init_db)"""
    if not db: return
    
    admins_ref = db.collection('admins')
    # 檢查是否為空
    docs = list(admins_ref.limit(1).stream())
    
    if not docs:
        print("建立預設管理員帳號...")
        # 建立預設管理員
        new_admin = {
            'username': 'admin',
            'password_hash': generate_password_hash('admin123'),
            'created_at': datetime.utcnow()
        }
        admins_ref.add(new_admin)
        print("✓ 預設管理員帳號建立完成 (admin / admin123)")

# 啟動時檢查
if db:
    ensure_admin_exists()


# ============== 公開路由（家長使用） ==============

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    if not db:
        flash('系統錯誤：資料庫未連接', 'danger')
        return redirect(url_for('index'))

    try:
        child_name = request.form.get('child_name', '').strip()
        parent_info = request.form.get('parent_info', '').strip()
        
        if not child_name:
            flash('請填寫孩子姓名', 'danger')
            return redirect(url_for('index'))
        
        if 'file' not in request.files:
            flash('請選擇要上傳的檔案', 'danger')
            return redirect(url_for('index'))
        
        files = request.files.getlist('file')
        
        if not files or files[0].filename == '':
            flash('請選擇要上傳的檔案', 'danger')
            return redirect(url_for('index'))
            
        bucket = storage.bucket()
        if not bucket:
            flash('系統錯誤：無法連接到雲端儲存', 'danger')
            return redirect(url_for('index'))
            
        success_count = 0
        fail_count = 0
        
        for file in files:
            if file.filename == '' or not allowed_file(file.filename):
                fail_count += 1
                continue
                
            try:
                # 檔案處理
                # 保留原始中文檔名，只做基本路徑清理
                original_filename = os.path.basename(file.filename)
                
                file.seek(0, 2)
                file_size = file.tell()
                file.seek(0)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                # 加入隨機字串避免同一秒多檔名衝突
                import random
                import string
                random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
                
                # 為了避免 Storage 路徑問題，blob_name 使用安全編碼後的名稱
                # 這裡使用 secure_filename 確保路徑安全 (它會移除中文，但沒關係，blob_name 只是內部路徑)
                # 如果 secure_filename 後變空 (例如純中文檔名)，給一個預設值
                safe_name = secure_filename(original_filename)
                if not safe_name:
                    safe_name = "file" + os.path.splitext(original_filename)[1]
                
                blob_name = f"uploads/{timestamp}_{random_str}_{safe_name}"
                
                blob = bucket.blob(blob_name)
                
                # 設定 metadata，確保下載時瀏覽器能看到正確的中文檔名
                try:
                    from urllib.parse import quote
                    encoded_filename = quote(original_filename)
                    blob.content_disposition = f"attachment; filename*=utf-8''{encoded_filename}"
                    blob.metadata = {'original_filename': original_filename}
                except Exception as e:
                    print(f"Metadata 設定警告: {e}")
                
                blob.upload_from_file(file, content_type=file.content_type)
                
                # 讓檔案公開可讀取
                blob.make_public()
                file_url = blob.public_url
                
                # 寫入 Firestore
                submission_data = {
                    'child_name': child_name,
                    'parent_info': parent_info,
                    'file_url': file_url,
                    'storage_path': blob_name, # 用於刪除
                    'original_filename': original_filename,
                    'file_size': file_size,
                    'upload_time': datetime.utcnow(),
                    'ip_address': request.remote_addr
                }
                
                db.collection('submissions').add(submission_data)
                success_count += 1
                
            except Exception as e:
                print(f"單一檔案上傳失敗: {e}")
                fail_count += 1
        
        if success_count > 0:
            msg = f'成功上傳 {success_count} 個檔案！感謝您的參與 🎉'
            if fail_count > 0:
                msg += f' (另有 {fail_count} 個檔案上傳失敗)'
            flash(msg, 'success')
        else:
            flash('檔案上傳失敗，請檢查檔案格式或大小', 'danger')
            
        return redirect(url_for('index'))
        
    except Exception as e:
        app.logger.error(f"上傳錯誤: {str(e)}")
        flash(f'上傳失敗: {str(e)}', 'danger')
        return redirect(url_for('index'))


# ============== 管理員路由 ==============

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if db:
            # 查詢 Firestore
            docs = db.collection('admins').where('username', '==', username).limit(1).stream()
            admin_doc = next(docs, None)
            
            if admin_doc:
                data = admin_doc.to_dict()
                if check_password_hash(data['password_hash'], password):
                    user = AdminUser(admin_doc.id, data['username'], data['password_hash'])
                    login_user(user)
                    flash('登入成功！', 'success')
                    return redirect(url_for('admin_dashboard'))
        
        flash('使用者名稱或密碼錯誤', 'danger')
    
    return render_template('login.html')


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('已成功登出', 'success')
    return redirect(url_for('index'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not db:
        flash('資料庫連接失敗', 'danger')
        return redirect(url_for('index'))

    # 簡單分頁邏輯 (Firestore 分頁較複雜，這裡簡化為獲取全部後在內存分頁)
    # 註：如果數據量很大，這不是最佳實踐
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    # 獲取所有 submissions
    submissions_ref = db.collection('submissions').order_by('upload_time', direction=firestore.Query.DESCENDING)
    all_docs = list(submissions_ref.stream())
    
    results = []
    total_size = 0
    
    for doc in all_docs:
        data = doc.to_dict()
        data['id'] = doc.id
        
        # 搜尋過濾
        if search:
            if (search.lower() not in data.get('child_name', '').lower() and
                search.lower() not in data.get('parent_info', '').lower() and
                search.lower() not in data.get('original_filename', '').lower()):
                continue
        
        # 格式化
        data['formatted_size'] = format_file_size(data.get('file_size', 0))
        total_size += data.get('file_size', 0)
        
        # 處理時間 (Firestore Timestamp 轉 Python datetime)
        if hasattr(data.get('upload_time'), 'strftime'):
             pass # 已經是 datetime
        else:
             # 如果是字串或其他
             pass

        results.append(data)

    # 內存分頁
    per_page = app.config['ITEMS_PER_PAGE']
    total_items = len(results)
    total_pages = (total_items + per_page - 1) // per_page
    
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = results[start:end]
    
    # 模擬 Pagination 物件以適配模板
    class MockPagination:
        def __init__(self, items, page, pages, total):
            self.items = items
            self.page = page
            self.pages = pages
            self.total = total
            self.has_prev = page > 1
            self.has_next = page < pages
            self.prev_num = page - 1
            self.next_num = page + 1
            
        def iter_pages(self, left_edge=1, right_edge=1, left_current=2, right_current=2):
            # 簡單實作
            for i in range(1, self.pages + 1):
                yield i

    pagination = MockPagination(paginated_items, page, total_pages, total_items)
    
    return render_template(
        'dashboard.html',
        submissions=paginated_items,
        pagination=pagination,
        search=search,
        total_submissions=total_items,
        total_size=total_size
    )


@app.route('/admin/delete/<submission_id>', methods=['POST'])
@login_required
def admin_delete(submission_id):
    if not db: return jsonify({'error': 'No DB'}), 500

    doc_ref = db.collection('submissions').document(submission_id)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        # 刪除 Storage 中的檔案
        storage_path = data.get('storage_path')
        if storage_path:
            try:
                bucket = storage.bucket()
                blob = bucket.blob(storage_path)
                blob.delete()
            except Exception as e:
                print(f"刪除 Storage 檔案失敗: {e}")
        
        # 刪除 Firestore 記錄
        doc_ref.delete()
        flash('記錄已刪除', 'success')
    else:
        flash('記錄不存在', 'danger')
        
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/export')
@login_required
def admin_export():
    if not db: return "Database error", 500
    
    submissions = db.collection('submissions').order_by('upload_time', direction=firestore.Query.DESCENDING).stream()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['孩子姓名', '家長資訊', '檔案名稱', '檔案連結', '檔案大小(Bytes)', '上傳時間', 'IP位址'])
    
    for doc in submissions:
        data = doc.to_dict()
        upload_time = data.get('upload_time')
        if hasattr(upload_time, 'strftime'):
            upload_time = upload_time.strftime('%Y-%m-%d %H:%M:%S')
            
        writer.writerow([
            data.get('child_name'),
            data.get('parent_info'),
            data.get('original_filename'),
            data.get('file_url'),
            data.get('file_size'),
            upload_time,
            data.get('ip_address')
        ])
    
    output.seek(0)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=submissions_{datetime.now().strftime("%Y%m%d")}.csv'
        }
    )


@app.route('/admin/download-all')
@login_required
def admin_download_all():
    """下載所有檔案並打包成 ZIP"""
    if not db: return "Database error", 500
    
    try:
        bucket = storage.bucket()
        submissions = db.collection('submissions').stream()
        
        # 建立記憶體中的 ZIP
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            
            # 用來處理重名檔案的計數器
            filename_counter = {}
            
            for doc in submissions:
                data = doc.to_dict()
                storage_path = data.get('storage_path')
                original_filename = data.get('original_filename', 'unknown')
                child_name = data.get('child_name', 'unknown')
                
                # 建構 ZIP 內的檔名：孩子姓名_原始檔名
                # 移除非法字元
                safe_child_name = "".join([c for c in child_name if c.isalnum() or c in (' ', '-', '_')]).strip()
                zip_filename = f"{safe_child_name}_{original_filename}"
                
                # 處理重名
                if zip_filename in filename_counter:
                    filename_counter[zip_filename] += 1
                    name, ext = os.path.splitext(zip_filename)
                    zip_filename = f"{name}_{filename_counter[zip_filename]}{ext}"
                else:
                    filename_counter[zip_filename] = 0
                
                if storage_path:
                    try:
                        blob = bucket.blob(storage_path)
                        # 下載檔案內容到記憶體
                        file_content = blob.download_as_bytes()
                        # 寫入 ZIP
                        zf.writestr(zip_filename, file_content)
                    except Exception as e:
                        print(f"下載檔案失敗 {storage_path}: {e}")
                        # 可以選擇寫入一個錯誤文字檔到 ZIP 中
                        zf.writestr(f"ERROR_{zip_filename}.txt", f"Download failed: {str(e)}")

        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'all_files_{datetime.now().strftime("%Y%m%d_%H%M")}.zip'
        )
        
    except Exception as e:
        app.logger.error(f"打包下載失敗: {str(e)}")
        flash(f'打包下載失敗: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

# ============== 錯誤處理 ==============

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    # 注意：本地開發時，你需要下載 serviceAccountKey.json 並放在專案根目錄
    # 或者是設定環境變數 FIREBASE_CREDENTIALS
    print("啟動 Firebase 版應用程式...")
    app.run(debug=True, host='0.0.0.0', port=5002)
