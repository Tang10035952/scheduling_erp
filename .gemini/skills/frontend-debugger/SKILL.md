---
name: frontend-debugger
description: 診斷 Django 前端畫面錯誤、靜態檔案加載失敗或樣式跑版。當用戶貼出 Django 報錯頁面或 Console Error 時觸發。
---
# 診斷流程
1. **模板語法檢查**：檢查 `{% ... %}` 標籤是否閉合，以及 `static` 標籤是否正確引用 `{% load static %}`。
2. **靜態檔案追蹤**：
   - 檢查 `settings.py` 中的 `STATIC_URL` 設定。
   - 驗證 Docker 環境下 `collectstatic` 是否已執行。
3. **路徑與權限**：針對文件管理功能（身分證、存摺），檢查 `media` 目錄權限與 `MEDIA_URL` 設定是否正確。
4. **請求安全檢查**：檢查 AJAX 請求是否遺漏了 `X-CSRFToken` 導致的 403 錯誤。

# 聯動分析
- 當發現報錯與資料庫有關時，主動調用 Django ORM 知識檢查 `models.py` 與資料庫欄位是否一致。
- 分析 Docker Log (Nginx/Gunicorn) 以判斷是伺服器配置問題還是代碼問題。