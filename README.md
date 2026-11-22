# moneycount

記帳日常網頁版，可直接透過 GitHub Pages 使用。

## 網頁功能

- 記錄收入與支出、分類、日期、備註
- 按月份查看收入、支出與結餘
- Google 登入後將記錄同步到 Cloud Firestore
- 第一次登入時，會把此瀏覽器原有的記錄匯入帳號（若此瀏覽器尚未綁定其他帳號）

## Firebase 設定

Firebase 專案需啟用 Google Authentication、建立 Cloud Firestore，並在 Firestore Rules 發布 `firestore.rules` 的內容。資料存放於 `users/{uid}/entries/{entryId}`，規則限制使用者只能存取自己的資料。

## Python 本機版

執行 `python money.py`，再開啟 http://127.0.0.1:8000。Python 版本使用程式旁的 SQLite 資料庫。
