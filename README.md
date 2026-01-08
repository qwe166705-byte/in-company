# IPC 資料收集與上傳系統

##  專案說明
此專案用於 IPC 端進行機台資料收集，並將資料上傳至 Server / MES 系統。
主要功能包含：
- 機台心跳回報
- PID / 2DID 資料處理
- CMD65 資料上傳
- PLC 參數讀取與整合

---

##  使用技術
- Python 3.x
- Flask
- MySQL
- PLC 通訊（MC / FINS）
- MQTT

---

##  時間戳記
因程式被清除，故從0107開始修復
更新時間與內容：
- 0107 : 找回上古版本
- 0107 : 更新machine_info、machine_edit、machine_add "棟別"互動與顯示功能
- 
- 