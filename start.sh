#!/bin/bash

# 親子資訊素養工作坊 - 檔案上傳系統啟動腳本

echo "=========================================="
echo "親子資訊素養工作坊 - 檔案上傳系統"
echo "=========================================="
echo ""

# 檢查虛擬環境是否存在
if [ ! -d "venv" ]; then
    echo "🔧 建立虛擬環境..."
    python3 -m venv venv
    echo "✓ 虛擬環境建立完成"
fi

# 啟動虛擬環境
echo "🔧 啟動虛擬環境..."
source venv/bin/activate

# 檢查是否需要安裝依賴
if ! python -c "import flask" 2>/dev/null; then
    echo "📦 安裝依賴套件..."
    pip install -r requirements.txt
    echo "✓ 依賴套件安裝完成"
fi

# 檢查資料庫是否存在
if [ ! -f "workshop.db" ]; then
    echo "🗄️  初始化資料庫..."
    python init_db.py
fi

# 啟動應用
echo ""
echo "🚀 啟動應用程式..."
echo "📍 應用程式將在以下位址啟動："
echo "   http://localhost:5002"
echo ""
echo "📝 預設管理員帳號："
echo "   使用者名稱: admin"
echo "   密碼: admin123"
echo ""
echo "⚠️  按 Ctrl+C 停止伺服器"
echo "=========================================="
echo ""

python app.py

