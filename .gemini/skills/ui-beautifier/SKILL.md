---
name: ui-beautifier
description: 專門用於美化 Django 模板的 UI/UX。當用戶要求「美化畫面」、「調整設計」或「改善介面」時觸發。
---
# 執行規範
1. **參考視覺標準**：
   - 執行前，請先讀取 `references/` 目錄下的圖檔或 `links.md`。
   - 觀察 `references/dashboard-ref.png` 中的配色、間距 (Spacing) 與圓角 (Border-radius) 設定，並以此為美化目標。
2. **設計原則**：
   - 優先使用現代簡約風：大留白、軟陰影 (Soft shadows)、12px 以上的圓角。
   - 確保 Django 模板中的按鈕與輸入框在 Focus 狀態下有明顯的視覺反饋。
3. **工具調用**：
   - 如果用戶提到特定元件，請掃描 `references/` 中是否有對應的組件截圖進行模仿。