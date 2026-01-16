# 親子資訊素養工作坊 - 檔案上傳系統

這是一個簡單易用的檔案上傳系統，專為親子資訊素養工作坊設計。家長可以無需登入即可上傳檔案，管理員則可以透過後台查看和下載所有提交的檔案。

## 功能特色

- ✨ 簡潔美觀的響應式設計
- 📤 家長無需登入即可上傳檔案
- 🔐 管理員登入系統
- 📊 管理後台查看所有提交記錄
- 🔍 搜尋和分頁功能
- 📥 檔案下載功能
- 💾 支援多種檔案格式
- 🛡️ 檔案大小和類型驗證

## 安裝步驟

### 1. 安裝 Python 依賴套件

```bash
pip install -r requirements.txt
```

### 2. 啟動應用程式

⚠️ **注意**：從版本 1.1 開始，**不需要手動初始化資料庫**！

應用程式會在啟動時自動：
- ✅ 建立資料庫表格
- ✅ 建立預設管理員帳號（使用者名稱: admin, 密碼: admin123）
- ✅ 建立上傳目錄

#### 方法一：使用啟動腳本（推薦）

```bash
./start.sh
```

#### 方法二：手動啟動

```bash
source venv/bin/activate
python app.py
```

應用程式將在 `http://localhost:5002` 啟動

## 使用方式

### 家長使用

1. 訪問 `http://localhost:5002`
2. 填寫孩子姓名
3. 填寫聯絡資訊（選填）
4. 選擇要上傳的檔案
5. 點擊「送出表單」

### 管理員使用

1. 訪問 `http://localhost:5002/admin/login`
2. 輸入帳號密碼登入
3. 在管理後台查看所有提交記錄
4. 可以搜尋、下載檔案
5. 使用完畢後請登出

## 支援的檔案格式

- 文件：PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT
- 圖片：JPG, JPEG, PNG, GIF
- 壓縮檔：ZIP, RAR

## 安全設定

⚠️ **重要**：在正式使用前，請務必：

1. 更改預設管理員密碼
2. 修改 `config.py` 中的 `SECRET_KEY`
3. 設定適當的檔案大小限制

## 技術規格

- **後端**：Python Flask
- **資料庫**：Google Firebase (Firestore)
- **檔案儲存**：Google Firebase Storage
- **前端**：HTML + Bootstrap 5 + JavaScript
- **身份驗證**：Flask-Login

## 安裝步驟

### 1. 安裝 Python 依賴套件

```bash
pip install -r requirements.txt
```

### 2. Firebase 設定

請參考 [FIREBASE_SETUP.md](FIREBASE_SETUP.md) 進行詳細設定。

簡單來說：
1. 下載 Firebase Service Account JSON。
2. 命名為 `serviceAccountKey.json` 放在專案根目錄。

### 3. 啟動應用程式

```bash
python app.py
```

## Zeabur 部署

請設定以下環境變數：
- `FIREBASE_CREDENTIALS`: Service Account JSON 的完整內容
- `FIREBASE_STORAGE_BUCKET`: 例如 `your-project.appspot.com`
- `SECRET_KEY`: 隨機字串

## 目錄結構

```
file_upload_sys/
├── app.py                 # Flask 主應用程式
├── config.py              # 配置檔案
├── models.py              # 資料庫模型
├── init_db.py             # 資料庫初始化腳本
├── requirements.txt       # Python 依賴套件
├── uploads/               # 上傳檔案儲存目錄
├── templates/             # HTML 模板
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   └── dashboard.html
└── static/                # 靜態資源
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## 授權

本專案僅供教育和非商業用途使用。

