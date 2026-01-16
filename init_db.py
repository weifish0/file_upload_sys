"""資料庫初始化腳本"""
import os
from app import app, db
from models import Admin

def init_database():
    """初始化資料庫和建立預設管理員帳號"""
    with app.app_context():
        # 建立資料庫表格
        db.create_all()
        print("✓ 資料庫表格建立完成")
        
        # 檢查是否已有管理員帳號
        if Admin.query.first() is None:
            # 建立預設管理員帳號
            admin = Admin(username='admin')
            admin.set_password('admin123')  # 請在生產環境中更改此密碼
            db.session.add(admin)
            db.session.commit()
            print("✓ 預設管理員帳號建立完成")
            print("  使用者名稱: admin")
            print("  密碼: admin123")
            print("  ⚠️  請在正式使用前更改預設密碼！")
        else:
            print("✓ 管理員帳號已存在")
        
        # 確保上傳目錄存在
        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            print("✓ 上傳目錄建立完成")
        else:
            print("✓ 上傳目錄已存在")
        
        print("\n🎉 初始化完成！您可以執行以下指令啟動應用程式：")
        print("   python app.py")

if __name__ == '__main__':
    init_database()

