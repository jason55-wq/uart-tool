# UART Serial Monitor

使用 Python 3.11+、PyQt6 與 pyserial 打造的 UART 桌面監控工具雛形，目標不是一次性 demo，而是可持續擴充成商業產品的桌面應用基礎。

## 功能特色

- 自動掃描可用串口，支援手動刷新
- 串口連線參數設定：Port、Baud Rate、Data Bits、Parity、Stop Bits、Flow Control
- 開啟 / 關閉串口，顯示連線狀態與異常提示
- 即時接收資料顯示，支援 `ASCII`、`HEX`、`UTF-8`
- 可切換時間戳、RX/TX 標記、換行格式、接收區自動捲動
- 收發統計：RX bytes、TX bytes、RX packets、TX packets
- 發送區支援 `ASCII` / `HEX`、Enter 快速送出、週期發送
- 命令模板管理：新增 / 編輯 / 刪除 / 一鍵送出
- 發送歷史記錄保存
- 手動開始 / 停止 log 記錄，落地為 JSON line log
- 使用 `QSettings` 與 JSON 記住視窗、串口參數與常用資料
- 預留 parser registry，方便後續擴充協議解析插件

## 安裝方式

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 執行方式

```bash
python main.py
```

## 專案結構

```text
uart_monitor/
├─ app/                  # 應用程式入口、組裝與初始化
├─ controllers/          # UI 與業務邏輯協調
├─ models/               # 狀態、資料結構、enum、dataclass
├─ resources/            # QSS 與靜態資源
├─ services/             # serial、設定、log、parser、template repository
├─ tests/                # 測試骨架與範例
├─ ui/                   # 主視窗、對話框
├─ utils/                # 編碼與路徑工具
├─ main.py               # 執行入口
├─ requirements.txt
├─ README.md
└─ .gitignore
```

## 架構說明

### 1. app

`app/bootstrap.py` 負責組裝 `MainWindow`、`MainController` 與各服務，讓入口保持乾淨。

### 2. services

- `SerialService`：封裝 pyserial，使用 `QThread + QObject worker` 做非阻塞讀取
- `SettingsService`：持久化視窗與串口設定
- `LogService`：將收發事件寫入檔案，與 UI 顯示分離
- `CommandRepository`：命令模板的儲存庫
- `ParserRegistry`：顯示層 parser 的註冊點，方便擴充設備協議解析

### 3. controllers

`MainController` 負責把 UI 事件、serial service、設定與 log 串接起來，避免把業務邏輯散落在 widget 內。

### 4. ui

- `MainWindow`：主操作視窗
- `TemplateEditDialog`：命令模板編輯對話框

## Log 格式

目前 log 採 JSON Lines，每行一筆事件，至少包含：

- `timestamp`
- `direction`
- `hex`
- `raw_len`

後續可無痛擴充為 CSV、TXT、SQLite、遠端上傳。

## 測試

```bash
pytest
```

目前先提供基礎資料模型 round-trip 測試結構，後續建議補上：

- serial service mock 測試
- parser render 測試
- command repository 持久化測試
- controller workflow 測試

## 後續擴充建議

### 商業產品化方向

- 多串口分頁 / 多連線 session 管理
- 協議解析插件市場化，例如 GPS、AT、Modbus-like text
- 命令模板分群、收藏、匯入匯出與團隊共享
- 進階 log 瀏覽器、回放、過濾與匯出
- 裝置自動識別、韌體燒錄整合、測試工站模式
- 授權機制、品牌化主題、企業版設定同步

### 下一步優先功能

1. 串口熱插拔偵測與更友善的 reconnect 體驗
2. 收發資料過濾器與關鍵字搜尋面板
3. 模板匯入 / 匯出與命令分類管理
4. 真正的 parser plugin 載入機制
5. 更完整的自動化測試與 CI

### 適合重構成插件系統的模組

- `services/parser_service.py`：最適合先擴充成 parser plugin
- `services/log_service.py`：可抽象為 file / db / remote backend
- `services/command_repository.py`：可演進為本地 / 雲端模板來源
- `services/serial_service.py`：可抽象為 serial / TCP / BLE transport

## 注意事項

- `HEX` 發送模式目前使用空白分隔十六進位輸入，例如 `41 54 0D 0A`
- Enter 快速送出預設關閉，避免多行輸入時誤送
- 若串口被占用、參數錯誤或裝置拔除，會顯示錯誤訊息
- 專案保留清楚的擴展點，進階功能以 TODO / registry 形式預留
