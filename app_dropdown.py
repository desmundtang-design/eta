# -*- coding: utf-8 -*-
"""
Streamlit App: KMB ETA with dropdowns for Route, Direction (bound) and Service Type
- Pulls full route list for a dropdown (deduplicated by route code)
- After selecting a route, fetches valid (bound, service_type) combos for that route and shows as dropdown
- After selecting a combo, loads stops in order and shows as dropdown
- Finally queries ETA for the chosen stop

Dependencies:
  pip install streamlit requests python-dateutil pytz
Run:
  streamlit run app_dropdown.py
"""

import requests
import streamlit as st
from datetime import datetime
from dateutil import parser
import pytz

BASE = "https://data.etabus.gov.hk"
HK_TZ = pytz.timezone("Asia/Hong_Kong")

# ---------------------- Helpers & Caching ----------------------
@st.cache_data(ttl=24*60*60)
def list_all_routes() -> list:
    """Return a sorted unique list of all KMB route codes (e.g., ["1A","6C","268X"]).
    Data updates daily at 05:00.
    """
    url = f"{BASE}/v1/transport/kmb/route/"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json().get("data", [])
    routes = sorted({rec.get("route", "").strip().upper() for rec in data if rec.get("route")})
    return routes

@st.cache_data(ttl=24*60*60)
def list_route_variants(route: str):
    """Return valid (bound, service_type, orig_tc, dest_tc) combos for a given route.
    Example: [{"bound":"I","service_type":"1","orig_tc":"...","dest_tc":"..."}, ...]
    """
    url = f"{BASE}/v1/transport/kmb/route/{route}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json().get("data", [])
    seen = set()
    variants = []
    for rec in data:
        b = (rec.get("bound") or "").strip()
        s = (rec.get("service_type") or "").strip()
        if not b or not s:
            continue
        key = (b, s)
        if key in seen:
            continue
        seen.add(key)
        variants.append({
            "bound": b,  # "I" or "O"
            "service_type": s,
            "orig_tc": rec.get("orig_tc", ""),
            "dest_tc": rec.get("dest_tc", ""),
        })
    order = {"I": 0, "O": 1}
    variants.sort(key=lambda v: (order.get(v["bound"], 9), v["service_type"]))
    return variants

@st.cache_data(ttl=24*60*60)
def get_route_stops(route: str, bound: str, service_type: str):
    """Return ordered stops for the given route/bound/service_type.
    On HTTP 422, return dict with error info for better diagnosis.
    """
    url = f"{BASE}/v1/transport/kmb/route-stop/{route}/{bound}/{service_type}"
    r = requests.get(url, timeout=15)
    if r.status_code == 422:
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text}
        return {"_error": "HTTP_422", "detail": body}
    r.raise_for_status()
    data = r.json().get("data", [])
    data = sorted(data, key=lambda x: int(str(x.get("seq", 0)) or 0))
    return data

@st.cache_data(ttl=24*60*60)
def get_stop_detail(stop_id: str) -> dict:
    url = f"{BASE}/v1/transport/kmb/stop/{stop_id}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json().get("data", {})

@st.cache_data(ttl=30)
def get_eta(stop_id: str, route: str, service_type: str):
    url = f"{BASE}/v1/transport/kmb/eta/{stop_id}/{route}/{service_type}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json().get("data", [])

# ---------------------- Formatting ----------------------
def humanize_eta(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        eta_dt = parser.isoparse(iso_str).astimezone(HK_TZ)
    except Exception:
        return "—"
    now = datetime.now(HK_TZ)
    delta = (eta_dt - now).total_seconds()
    if delta < 0:
        return eta_dt.strftime("%H:%M（已過）")
    mins, secs = int(delta // 60), int(delta % 60)
    return f"{mins} 分 {secs} 秒後（{eta_dt:%H:%M}）"

# ---------------------- UI ----------------------
st.set_page_config(page_title="九巴 ETA（下拉式選單）", page_icon="🚌", layout="centered")
st.title("🚌 九巴 ETA 查詢（下拉式選單版）")

with st.expander("使用說明 / How to use", expanded=False):
    st.markdown(
        """
        1. 從 **路線下拉** 選擇路線（可輸入以篩選）。
        2. 選擇該路線中有效的 **方向(I/O) + service_type** 組合（已依起訖站顯示）。
        3. 再選擇 **站點** 並查詢 ETA。

        資料來源：data.gov.hk / KMB 開放 API（ETA 每分鐘更新；路線/站點每日 05:00 更新）。
        """
    )

# A) Route dropdown (from full unique list)
try:
    all_routes = list_all_routes()
except requests.HTTPError as ex:
    st.error(f"載入路線清單失敗：{ex}")
    st.stop()

route = st.selectbox("選擇路線（可輸入以快速篩選）", options=all_routes, index=all_routes.index("268X") if "268X" in all_routes else 0)

# B) Variants dropdown (bound + service_type), only valid combos are shown
try:
    variants = list_route_variants(route)
except requests.HTTPError as ex:
    st.error(f"載入路線資訊失敗：{ex}")
    st.stop()

if not variants:
    st.error("此路線目前沒有可用的方向/班次資訊，請改選其他路線。")
    st.stop()

bound_map = {"I": "入(I)", "O": "出(O)"}

def variant_label(v: dict) -> str:
    pair = f"{v.get('orig_tc','')} → {v.get('dest_tc','')}".strip(" →")
    return f"{bound_map.get(v['bound'], v['bound'])}｜service_type={v['service_type']}｜{pair}"

variant_opt_labels = [variant_label(v) for v in variants]
variant_label_to_obj = {variant_label(v): v for v in variants}
chosen_label = st.selectbox("選擇方向 + service_type（僅顯示有效組合）", options=variant_opt_labels)
chosen_variant = variant_label_to_obj[chosen_label]

bound = chosen_variant["bound"]
service_type = chosen_variant["service_type"]

st.caption(f"目前組合：路線 {route}｜方向 {bound}｜service_type {service_type}")

# C) Stops dropdown for the selected variant
stops = get_route_stops(route, bound, service_type)
if isinstance(stops, dict) and stops.get("_error"):
    st.error(f"（診斷）API 返回 422：{stops.get('detail')}")
    st.stop()

stop_labels = []
stop_id_map = {}
for s in stops:
    sid = s.get("stop")
    if not sid:
        continue
    info = get_stop_detail(sid)
    name_tc = info.get("name_tc", "")
    name_en = info.get("name_en", "")
    label = f"{name_tc}（{name_en}）｜{sid}"
    stop_labels.append(label)
    stop_id_map[label] = sid

if not stop_labels:
    st.warning("該組合未取得站點資料，請改選其他方向或 service_type。")
    st.stop()

chosen_stop_label = st.selectbox("選擇站點", options=stop_labels)
chosen_stop_id = stop_id_map[chosen_stop_label]

# D) Query ETA
if st.button("查詢 ETA"):
    try:
        etas = get_eta(chosen_stop_id, route, service_type)
        if not etas:
            st.info("此站目前沒有班次資料。")
        else:
            for i, e in enumerate(etas, 1):
                eta_str = humanize_eta(e.get("eta"))
                dest = e.get("dest_tc") or e.get("dest_en") or ""
                rmk = e.get("rmk_tc") or e.get("rmk_en") or ""
                st.write(f"**第 {i} 班**：{eta_str} → {dest}  {rmk}")
        st.caption("提示：ETA 每 1 分鐘更新；請稍等片刻再重新查詢。")
    except requests.HTTPError as ex:
        st.error(f"HTTP 錯誤：{ex}")

