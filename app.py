"""親子資訊素養工作坊 - 檔案上傳系統"""
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
import csv
from io import StringIO

from config import Config
from models import db, Submission, Admin

# 初始化 Flask 應用
app = Flask(__name__)
app.config.from_object(Config)

# 初始化擴展
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = '請先登入以訪問此頁面'

@login_manager.user_loader
def load_user(user_id):
    """載入使用者"""
    return Admin.query.get(int(user_id))


def allowed_file(filename):
    """檢查檔案是否允許上傳"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_file_size(file):
    """獲取檔案大小"""
    file.seek(0, 2)  # 移動到檔案末尾
    size = file.tell()
    file.seek(0)  # 重置到檔案開頭
    return size


# ============== 公開路由（家長使用） ==============

@app.route('/')
def index():
    """家長表單頁面"""
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    """處理表單提交"""
    try:
        # 獲取表單數據
        child_name = request.form.get('child_name', '').strip()
        parent_info = request.form.get('parent_info', '').strip()
        
        # 驗證必填欄位
        if not child_name:
            flash('請填寫孩子姓名', 'danger')
            return redirect(url_for('index'))
        
        # 檢查檔案
        if 'file' not in request.files:
            flash('請選擇要上傳的檔案', 'danger')
            return redirect(url_for('index'))
        
        file = request.files['file']
        
        if file.filename == '':
            flash('請選擇要上傳的檔案', 'danger')
            return redirect(url_for('index'))
        
        if not allowed_file(file.filename):
            flash('不支援的檔案類型，請上傳 PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, JPG, JPEG, PNG, GIF, ZIP, RAR 格式', 'danger')
            return redirect(url_for('index'))
        
        # 獲取檔案大小
        file_size = get_file_size(file)
        
        # 生成安全的檔案名稱
        original_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{original_filename}"
        
        # 儲存檔案
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # 建立資料庫記錄
        submission = Submission(
            child_name=child_name,
            parent_info=parent_info,
            file_path=file_path,
            original_filename=original_filename,
            file_size=file_size,
            ip_address=request.remote_addr
        )
        
        db.session.add(submission)
        db.session.commit()
        
        flash('檔案上傳成功！感謝您的參與 🎉', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        app.logger.error(f"上傳錯誤: {str(e)}")
        flash('上傳過程發生錯誤，請稍後再試', 'danger')
        return redirect(url_for('index'))


# ============== 管理員路由 ==============

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """管理員登入"""
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            login_user(admin)
            flash('登入成功！', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('使用者名稱或密碼錯誤', 'danger')
    
    return render_template('login.html')


@app.route('/admin/logout')
@login_required
def admin_logout():
    """管理員登出"""
    logout_user()
    flash('已成功登出', 'success')
    return redirect(url_for('index'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """管理後台"""
    # 獲取分頁參數
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    # 查詢提交記錄
    query = Submission.query
    
    if search:
        query = query.filter(
            (Submission.child_name.contains(search)) |
            (Submission.parent_info.contains(search)) |
            (Submission.original_filename.contains(search))
        )
    
    # 按上傳時間降序排列
    query = query.order_by(Submission.upload_time.desc())
    
    # 分頁
    pagination = query.paginate(
        page=page,
        per_page=app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    
    submissions = pagination.items
    
    # 統計數據
    total_submissions = Submission.query.count()
    total_size = db.session.query(db.func.sum(Submission.file_size)).scalar() or 0
    
    return render_template(
        'dashboard.html',
        submissions=submissions,
        pagination=pagination,
        search=search,
        total_submissions=total_submissions,
        total_size=total_size
    )


@app.route('/admin/download/<int:submission_id>')
@login_required
def admin_download(submission_id):
    """下載檔案"""
    submission = Submission.query.get_or_404(submission_id)
    
    if not os.path.exists(submission.file_path):
        flash('檔案不存在', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    return send_file(
        submission.file_path,
        as_attachment=True,
        download_name=submission.original_filename
    )


@app.route('/admin/delete/<int:submission_id>', methods=['POST'])
@login_required
def admin_delete(submission_id):
    """刪除提交記錄"""
    submission = Submission.query.get_or_404(submission_id)
    
    # 刪除檔案
    if os.path.exists(submission.file_path):
        os.remove(submission.file_path)
    
    # 刪除資料庫記錄
    db.session.delete(submission)
    db.session.commit()
    
    flash('記錄已刪除', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/export')
@login_required
def admin_export():
    """匯出所有記錄為 CSV"""
    submissions = Submission.query.order_by(Submission.upload_time.desc()).all()
    
    # 建立 CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # 寫入標題
    writer.writerow(['編號', '孩子姓名', '家長資訊', '檔案名稱', '檔案大小', '上傳時間', 'IP位址'])
    
    # 寫入數據
    for sub in submissions:
        writer.writerow([
            sub.id,
            sub.child_name,
            sub.parent_info or '',
            sub.original_filename,
            sub.format_file_size(),
            sub.upload_time.strftime('%Y-%m-%d %H:%M:%S'),
            sub.ip_address or ''
        ])
    
    # 準備回應
    output.seek(0)
    
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=submissions_{datetime.now().strftime("%Y%m%d")}.csv'
        }
    )


# ============== 錯誤處理 ==============

@app.errorhandler(404)
def not_found(error):
    """404 錯誤頁面"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """500 錯誤頁面"""
    db.session.rollback()
    return render_template('500.html'), 500


# ============== 資料庫初始化 ==============

def init_database():
    """自動初始化資料庫"""
    with app.app_context():
        # 建立資料庫表格
        db.create_all()
        
        # 檢查是否已有管理員帳號
        if Admin.query.first() is None:
            # 建立預設管理員帳號
            admin = Admin(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✓ 預設管理員帳號建立完成（使用者名稱: admin, 密碼: admin123）")


# ============== 啟動應用 ==============

if __name__ == '__main__':
    # 確保上傳目錄存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 自動初始化資料庫
    init_database()
    
    # 啟動應用
    app.run(debug=True, host='0.0.0.0', port=5002)

