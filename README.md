# 🚌 KMB ETA – 下拉式選單版（Streamlit）

這個專案提供「路線、方向(I/O)、service_type、站點」**全下拉式選單**的九巴 ETA 查詢。

## 本地執行
```bash
pip install -r requirements.txt
streamlit run app_dropdown.py
```

## Streamlit Cloud 部署
1. 建立 GitHub Repo，加入 `app_dropdown.py`、`requirements.txt`、`README.md`
2. 到 Streamlit Cloud → New app → 指向該 Repo → App file 選 `app_dropdown.py` → Deploy

## 說明
- 路線清單、方向/班次（bound + service_type）、站點清單皆為 **每日 05:00** 更新的靜態資料
- ETA 為 **每分鐘**更新
- 程式已對靜態資料快取 24h、ETA 快取 30s，並顯示友善錯誤
