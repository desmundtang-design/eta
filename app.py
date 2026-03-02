import os
import time
import json
import requests
import streamlit as st
from datetime import datetime
from dateutil import parser
import pytz

BASE = "https://data.etabus.gov.hk"
HK_TZ = pytz.timezone("Asia/Hong_Kong")

@st.cache_data(ttl=24*60*60)
def get_route_stops(route: str, direction: str, service_type: str = "1"):
    url = f"{BASE}/v1/transport/kmb/route-stop/{route}/{direction}/{service_type}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", [])
    stops = sorted(data, key=lambda x: int(x.get("seq", 0)))
    return [s["stop"] for s in stops]

@st.cache_data(ttl=24*60*60)
def get_stop_detail(stop_id: str):
    url = f"{BASE}/v1/transport/kmb/stop/{stop_id}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()["data"]

@st.cache_data(ttl=30)
def get_eta(stop_id: str, route: str, service_type: str = "1"):
    url = f"{BASE}/v1/transport/kmb/eta/{stop_id}/{route}/{service_type}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json().get("data", [])

def humanize_eta(iso_str: str):
    if not iso_str:
        return "—"
    eta_dt = parser.isoparse(iso_str).astimezone(HK_TZ)
    now = datetime.now(HK_TZ)
    delta = (eta_dt - now).total_seconds()
    if delta < 0:
        return eta_dt.strftime("%H:%M（已過）")
    mins = int(delta // 60)
    secs = int(delta % 60)
    return f"{mins} 分 {secs} 秒後（{eta_dt:%H:%M}）"

st.set_page_config(page_title="九巴 ETA 查詢", page_icon="🚌", layout="centered")
st.title("🚌 九巴 ETA 查詢（KMB ETA）")

with st.expander("使用說明 / How to use"):
    st.markdown(
        """
        1. 輸入路線（例如 `6C`、`268X`）
        2. 選擇方向：`I`=入站、`O`=出站
        3. 選擇站點，按「查詢 ETA」
        \n\n資料來源：data.gov.hk / KMB 開放 API（ETA 每分鐘更新；路線/站點每日 05:00 更新）。
        """
    )

col1, col2, col3 = st.columns(3)
route = col1.text_input("路線（例如：6C、268X）", value="6C").strip().upper()
direction = col2.selectbox("方向（I=入站／O=出站）", options=["I", "O"], index=0)
service_type = col3.text_input("服務類型（多數為 1）", value="1").strip()

if route:
    try:
        stop_ids = get_route_stops(route, direction, service_type)
        if not stop_ids:
            st.warning("未找到此路線／方向的站點，請確認輸入是否正確。")
        else:
            options = []
            for sid in stop_ids:
                info = get_stop_detail(sid)
                options.append(f"{info['name_tc']}（{info['name_en']}）｜{sid}")
            choice = st.selectbox("選擇站點", options=options)
            chosen_stop = choice.split("｜")[-1]

            if st.button("查詢 ETA"):
                with st.spinner("查詢中…"):
                    etas = get_eta(chosen_stop, route, service_type)
                    if not etas:
                        st.info("此站目前沒有班次資料。")
                    for i, e in enumerate(etas, 1):
                        eta_str = humanize_eta(e.get("eta"))
                        dest = e.get("dest_tc") or e.get("dest_en") or ""
                        rmk = e.get("rmk_tc") or e.get("rmk_en") or ""
                        st.write(f"**第 {i} 班**：{eta_str} → {dest}  {rmk}")
                st.caption("提示：ETA 每 1 分鐘更新；請稍等片刻再重新查詢。")
    except requests.HTTPError as ex:
        st.error(f"HTTP 錯誤：{ex}")
    except Exception as ex:
        st.error(f"發生例外：{ex}")
