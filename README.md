# 🚌 KMB ETA – Streamlit App

這是一個可部署到 **Streamlit Cloud** 的九巴 ETA 查詢小工具。

## 功能
- 依路線 + 方向列出站點，並查詢該站 **ETA**（最多 3 班）
- 自動格式化成「幾分鐘後」並顯示到站時刻（香港時區）
- 對靜態資料（路線/站點）做 1 天快取、對 ETA 做 30 秒快取

## 資料來源
- KMB / data.gov.hk 開放 API：`https://data.etabus.gov.hk`
  - `route-stop`：取得路線在某方向的站點序
  - `stop`：取得站點名稱、座標
  - `eta`：取得即時到站

> ETA 每分鐘更新；路線與站點每日 05:00 更新。

## 本地執行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 部署到 Streamlit Cloud
1. 新建 GitHub Repo，加入 `app.py` 與 `requirements.txt`
2. 到 https://streamlit.io/cloud  → New app → 指向你的 Repo → Deploy

---
如需進一步客製（顯示地圖、收藏常用站點、整合票價/轉乘），歡迎提出需求！
