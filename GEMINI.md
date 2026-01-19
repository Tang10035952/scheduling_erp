# 專案概覽

這個專案是一個基於 Django 的網路應用程式，用於管理員工排班及相關行政事務。它似乎是為擁有多家門市和不同員工角色（員工、經理、主管）的企業所設計。

## 主要功能：

*   **使用者管理：** 處理不同使用者角色（員工、經理、主管），並提供詳細的使用者資料，包括個人資訊、工作經驗和僱用狀態。
*   **排班管理：** 允許建立排班週期，定義員工工作可用性，並將班次分配給不同門市的員工。
*   **薪資管理：** 包含管理薪資單的功能，根據工時計算薪資，並處理各種獎金和扣款。
*   **文件管理：** 允許上傳和儲存與員工相關的文件，例如身分證和存摺副本。

## 使用技術：

*   **後端：** Django 4.2.27
*   **資料庫：** MySQL
*   **前端：** Django 模板 (HTML)
*   **部署：** Docker, Gunicorn, Nginx

# 建置與運行

## 先決條件：

*   Python 3
*   Docker 和 Docker Compose
*   MySQL 客戶端

## 本地開發設置：

1.  **克隆儲存庫：**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **建立並啟動虛擬環境：**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **安裝依賴：**
    ```bash
    pip install -r requirements.txt
    ```

4.  **設定環境變數：**
    *   根據 `.env.example` 檔案建立一個 `.env` 檔案，並提供必要的資料庫憑證和其他配置詳細資訊。

5.  **運行資料庫遷移：**
    ```bash
    python manage.py migrate
    ```

6.  **建立超級使用者（可選）：**
    ```bash
    python manage.py createsuperuser
    ```

7.  **運行開發伺服器：**
    ```bash
    python manage.py runserver
    ```

## Docker 部署：

專案包含 `docker-compose.yml` 和 `Dockerfile` 用於容器化部署。

1.  **建置並運行容器：**
    ```bash
    docker-compose up -d --build
    ```

# 開發規範

*   **程式碼風格：** 程式碼庫遵循標準的 Python 和 Django 規範。
*   **專案結構：** 專案分為兩個主要的 Django 應用程式：`users` 和 `scheduling`。
*   **資料庫：** 專案使用 Django 的 ORM 進行資料庫互動。
*   **模板：** 前端使用 Django 的模板引擎進行渲染。
*   **靜態檔案：** 靜態檔案 (CSS, JavaScript) 從 `static` 目錄提供。
*   **媒體檔案：** 使用者上傳的檔案儲存在 `media` 目錄中。