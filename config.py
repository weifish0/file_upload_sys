import os

class Config:
    """應用程式配置"""
    
    # 基礎設定
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 資料庫設定 (移除 SQL設定)
    # Firebase 設定將在 app.py 中處理
    
    # 檔案上傳設定
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB 限制
    ALLOWED_EXTENSIONS = {
        'pdf', 'doc', 'docx',
        'ppt', 'pptx', 'txt', 'jpg', 'jpeg', 
        'png', 'zip', 'rar'
    }
    
    # 分頁設定
    ITEMS_PER_PAGE = 20

