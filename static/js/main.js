// 檔案上傳處理
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file');
    const fileLabel = document.querySelector('.file-upload-label');
    const fileName = document.querySelector('.file-name');
    
    if (fileInput && fileLabel) {
        fileInput.addEventListener('change', function(e) {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                const size = (file.size / 1024 / 1024).toFixed(2);
                fileName.textContent = `已選擇：${file.name} (${size} MB)`;
                fileName.style.display = 'block';
            } else {
                fileName.style.display = 'none';
            }
        });
    }
    
    // 表單提交載入動畫
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
            }
        });
    });
    
    // 自動隱藏提示訊息
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
});

// 搜尋功能
function searchTable() {
    const input = document.getElementById('searchInput');
    const filter = input.value.toLowerCase();
    const table = document.querySelector('.table tbody');
    const rows = table.getElementsByTagName('tr');
    
    for (let i = 0; i < rows.length; i++) {
        const cells = rows[i].getElementsByTagName('td');
        let found = false;
        
        for (let j = 0; j < cells.length; j++) {
            const cell = cells[j];
            if (cell) {
                const textValue = cell.textContent || cell.innerText;
                if (textValue.toLowerCase().indexOf(filter) > -1) {
                    found = true;
                    break;
                }
            }
        }
        
        rows[i].style.display = found ? '' : 'none';
    }
}

// 確認刪除
function confirmDelete(id) {
    return confirm('確定要刪除這筆記錄嗎？');
}

// 匯出CSV
function exportToCSV() {
    window.location.href = '/admin/export';
}

