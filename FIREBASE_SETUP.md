# Firebase 設置與部署指南

本系統已遷移至 Firebase (Firestore + Storage)，支援完全無狀態的雲端部署 (Zeabur)。

## 1. 建立 Firebase 專案

1. 前往 [Firebase Console](https://console.firebase.google.com/)。
2. 點擊 **"Add project"** (新增專案)。
3. 輸入專案名稱 (例如 `file-upload-sys`)，並依步驟完成建立。

## 2. 啟用 Firestore 資料庫

1. 在左側選單中，選擇 **Build** > **Firestore Database**。
2. 點擊 **"Create database"**。
3. 選擇 **Location** (建議選 `asia-east1` 台灣或 `asia-northeast1` 東京)。
4. 安全規則選擇 **"Start in production mode"** (稍後我們會修改規則)。

## 3. 啟用 Storage (檔案儲存)

1. 在左側選單中，選擇 **Build** > **Storage**。
2. 點擊 **"Get started"**。
3. 選擇 **Production mode**。
4. 設定 Location (同上)。
5. 完成後，請記下 **Bucket URL** (通常是 `gs://your-project-id.appspot.com`)。
   * 您可以在 Storage 頁面的 "Files" 標籤上方看到，例如 `gs://xxxx.appspot.com`。

## 4. 獲取服務帳戶金鑰 (Service Account Key)

這是後端程式與 Firebase 溝通的憑證。

1. 點擊左上角 **Project Overview** 旁的齒輪圖示 > **Project settings**。
2. 切換到 **"Service accounts"** 標籤。
3. 點擊下方的 **"Generate new private key"**。
4. 下載 JSON 檔案。
5. **本地開發**：將此檔案重新命名為 `serviceAccountKey.json` 並放在專案根目錄 (與 `app.py` 同層)。

## 5. 部署到 Zeabur (或其他平台)

在 Zeabur 上部署時，我們不能直接上傳 `serviceAccountKey.json` (不安全)。我們使用環境變數。

### 準備環境變數

1. 打開您下載的 JSON 檔案，複製全部內容。
2. 前往 Zeabur 的服務設定頁面，找到 **Environment Variables** (環境變數)。
3. 新增以下變數：

| 變數名稱 | 值 (Value) | 說明 |
| :--- | :--- | :--- |
| `FIREBASE_CREDENTIALS` | `{ "type": "service_account", ... }` | 貼上 JSON 檔案的**完整內容** |
| `FIREBASE_STORAGE_BUCKET` | `your-project-id.appspot.com` | 您的 Storage Bucket 名稱 (不含 gs://) |
| `SECRET_KEY` | (任意隨機字串) | Flask 加密金鑰 |

**注意**：
* `FIREBASE_CREDENTIALS` 的值必須是有效的 JSON 字串。
* `FIREBASE_STORAGE_BUCKET` 不需要加 `gs://` 前綴。

## 6. Firebase 安全規則 (Security Rules)

為了安全起見，我們應該設定規則。不過因為我們是使用 **Admin SDK** (後端程式)，它擁有完全權限，會繞過這些規則。這些規則主要限制前端直接訪問。

### Firestore Rules
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if false; // 禁止前端直接讀寫，只允許後端 Admin SDK
    }
  }
}
```

### Storage Rules
為了讓後端生成的 `public_url` 可以被訪問，我們需要允許讀取。

```
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /{allPaths=**} {
      allow read;  // 允許公開讀取 (因為我們是公開表單)
      allow write: if false; // 禁止前端直接寫入
    }
  }
}
```

## 常見問題

**Q: 部署後出現 "Firebase 初始化錯誤"？**
A: 檢查 `FIREBASE_CREDENTIALS` 環境變數是否完整複製了 JSON 內容，確保沒有多餘的空白或換行導致 JSON 解析失敗。

**Q: 檔案上傳失敗？**
A: 檢查 `FIREBASE_STORAGE_BUCKET` 是否設定正確。

**Q: 本地開發時需要環境變數嗎？**
A: 不需要，只要有 `serviceAccountKey.json` 在根目錄即可。

