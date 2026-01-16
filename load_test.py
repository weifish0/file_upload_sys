import random
import string
import io
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    # 模擬使用者在任務之間的等待時間 (5~15秒)，更像真實人類操作
    wait_time = between(5, 15)
    
    # 設置目標主機
    host = "https://file-upload-sys.zeabur.app"

    @task(1)
    def index_page(self):
        """模擬訪問首頁"""
        self.client.get("/")

    @task(3)
    def submit_form(self):
        """模擬提交表單與上傳檔案"""
        
        # 1. 生成隨機測試數據
        child_name = f"測試學生_{''.join(random.choices(string.digits, k=4))}"
        parent_info = f"09{''.join(random.choices(string.digits, k=8))}"
        
        # 2. 生成隨機檔案內容 (模擬 PDF 或 TXT)
        # 為了節省頻寬，我們生成較小的檔案 (約 100KB)
        file_content = ''.join(random.choices(string.ascii_letters, k=1024 * 100))
        file_obj = io.BytesIO(file_content.encode('utf-8'))
        
        # 3. 準備 multipart/form-data
        files = {
            'file': (f'test_file_{random.randint(1000,9999)}.txt', file_obj, 'text/plain')
        }
        
        data = {
            'child_name': child_name,
            'parent_info': parent_info
        }

        # 4. 發送 POST 請求
        # 使用 catch_response=True 來自行處理成功/失敗判定
        with self.client.post("/submit", data=data, files=files, catch_response=True) as response:
            if response.status_code == 200:
                # 檢查是否重定向回首頁或顯示成功訊息
                # 注意：Locust 默認會自動跟隨重定向，所以最終 URL 應該是 "/"
                # 我們可以檢查回應內容中是否有 "上傳成功" 的關鍵字 (如果有的話)
                # 這裡假設返回 200 就是成功
                response.success()
            elif response.status_code == 302:
                # 處理重定向 (通常 Flask redirect 是 302)
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

# 使用說明：
# 1. 安裝 Locust: pip install locust
# 2. 執行測試: locust -f load_test.py
# 3. 打開瀏覽器訪問 http://localhost:8089
# 4. 在網頁介面設定：
#    - Number of users: 30 (模擬 30 人)
#    - Spawn rate: 5 (每秒增加 5 人，直到 30 人)
#    - Host: https://file-upload-sys.zeabur.app

