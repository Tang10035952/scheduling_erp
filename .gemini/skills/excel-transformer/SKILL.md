---
name: excel-transformer
description: 專門優化 Django 模板中的 HTML 表格，使其具有 Excel 般的互動感，特別是實作「凍結首列/首欄」功能與處理表格破版問題。
---
# 執行規範
1. **技術實現**：在 Django 模板 (.html) 中，優先使用 CSS `position: sticky` 實作凍結窗格，改用『容器溢出隱藏』方案，並使用 box-shadow 取代 border 來處理黏性儲存格的邊界，一定要「確保被凍結的欄位最外層表格框線完全固定」
   - 頂部標題：`.thead-dark th { position: sticky; top: 0; z-index: 10; }`
   - 左側首欄 (如員工姓名)：`.sticky-col { position: sticky; left: 0; background-color: #f8f9fa; z-index: 5; }`
2. **Django 整合**：優化 `{% for %}` 迴圈生成的表格結構，確保 `<table>` 標籤具有 `table-responsive` 或自定義的滾動容器包裹。
3. **視覺優化**：
   - 增加 `table-hover` (Bootstrap 風格) 確保排班表易於閱讀。
   - 為排班狀態（如：早班、晚班）建議對應的背景顏色標籤。
4. **效能提示**：若排班資料量龐大（超過 500 列），主動建議用戶將 Django 視圖改為分頁 (Paginator) 或使用 AJAX 異步加載。