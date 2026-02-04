import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Pro (Sprint Support)", page_icon="🏎️", layout="wide")

# --- 1. 核心設定 ---
TEAM_CONFIG = {
    "McLaren": {"color": "#FF8700", "drivers": {"Lando Norris": "1", "Oscar Piastri": "81"}},
    "Ferrari": {"color": "#E80020", "drivers": {"Lewis Hamilton": "44", "Charles Leclerc": "16"}},
    "Red Bull": {"color": "#3671C6", "drivers": {"Max Verstappen": "3", "Isack Hadjar": "66"}},
    "Mercedes": {"color": "#27F4D2", "drivers": {"George Russell": "63", "Kimi Antonelli": "12"}},
    "Aston Martin": {"color": "#229971", "drivers": {"Fernando Alonso": "14", "Lance Stroll": "18"}},
    "Audi": {"color": "#F50A20", "drivers": {"Nico Hulkenberg": "27", "Gabriel Bortoleto": "5"}},
    "Williams": {"color": "#64C4FF", "drivers": {"Carlos Sainz": "55", "Alex Albon": "23"}},
    "Alpine": {"color": "#0093CC", "drivers": {"Pierre Gasly": "10", "Franco Colapinto": "43"}},
    "Racing Bulls": {"color": "#6692FF", "drivers": {"Liam Lawson": "30", "Arvid Lindblad": "17"}},
    "Haas": {"color": "#B6BABD", "drivers": {"Esteban Ocon": "31", "Oliver Bearman": "87"}},
    "APX-CTWR": {"color": "#000000", "drivers": {"Yuki Tsunoda": "22", "Ethan Tan": "9"}}
}

# --- 2. 初始化函數 ---
def init_driver_stats(name, no, team):
    return {
        "no": no, "team": team, "points": 0, "ranks": [], 
        "point_history": [{"race": 0, "pts": 0}], 
        "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "prev_rank": 0
    }

if "stats" not in st.session_state:
    st.session_state.stats = {d: init_driver_stats(d, c, t) for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
    st.session_state.race_no = 0
    st.session_state.sprint_history = [] # 儲存格式: {"race_after": 5, "results": {driver: points}}

# --- 3. 側邊欄與載入重建 (支援衝刺賽) ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("貼入壓縮存檔代碼：", height=100)
    
    if st.button("載入存檔"):
        try:
            raw = json.loads(backup_input)
            st.session_state.race_no = raw["race_no"]
            st.session_state.sprint_history = raw.get("sprints", [])
            new_stats = {d: init_driver_stats(d, c, t) for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
            
            # A. 重建正賽積分
            pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
            for d, r_list in raw["data"].items():
                s = new_stats[d]
                s["ranks"] = r_list
                temp_pts = 0
                for i, r in enumerate(r_list, 1):
                    p = 0
                    if r == 'R': s["dnf"] += 1
                    else:
                        if r == 1: s["p1"] += 1
                        elif r == 2: s["p2"] += 1
                        elif r == 3: s["p3"] += 1
                        p = pts_map.get(r, 0)
                    
                    # 檢查這場正賽後是否有衝刺賽要插入
                    for sp in st.session_state.sprint_history:
                        if sp["race_after"] == i - 0.5: # 這裡邏輯依你輸入習慣而定
                            temp_pts += sp["results"].get(d, 0)
                    
                    temp_pts += p
                    s["points"] = temp_pts
                    s["point_history"].append({"race": i, "pts": temp_pts})
            
            st.session_state.stats = new_stats
            st.success("賽季重建成功 (含衝刺賽)！"); st.rerun()
        except Exception as e:
            st.error(f"解析失敗: {e}")

# --- 4. 成績輸入 (衝刺賽邏輯) ---
tabs = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置"])

with tabs[0]:
    r_type = st.radio("類型：", ["正賽", "衝刺賽"], horizontal=True)
    inputs = {}
    cols = st.columns(2)
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 2]:
            st.markdown(f"**{team}**")
            for driver, no in cfg["drivers"].items():
                inputs[driver] = st.text_input(f"#{no} {driver}", key=f"in_{driver}_{st.session_state.race_no}_{r_type}")

    if st.button("🚀 提交成績", use_container_width=True):
        if r_type == "衝刺賽":
            # 衝刺賽計分 (8-7-6-5-4-3-2-1)
            s_res = {}
            sorted_in = sorted(inputs.items(), key=lambda x: 99 if x[1].upper()=='R' else int(x[1]))
            s_pts = [8, 7, 6, 5, 4, 3, 2, 1]
            for d, r in sorted_in:
                p = s_pts.pop(0) if r.isdigit() and int(r) <= 8 else 0
                st.session_state.stats[d]["points"] += p
                s_res[d] = p
            st.session_state.sprint_history.append({"race_after": st.session_state.race_no + 0.5, "results": s_res})
            st.success("衝刺賽積分已加入！")
        else:
            # 正賽邏輯 (略，同前版本，但需同步更新 point_history)
            st.session_state.race_no += 1
            # ... 執行正賽積分邏輯 ...
        st.rerun()

# --- 5. 完賽位置與平均名次 ---
with tabs[3]:
    # 這裡套用你最喜歡的「字體染色」與「R=25」邏輯
    pass # 程式碼細節同前

# --- 6. 壓縮存檔輸出 (包含 sprints) ---
compact_json = json.dumps({
    "race_no": st.session_state.race_no,
    "sprints": st.session_state.sprint_history, # 關鍵：把衝刺賽存進去
    "data": {d: s["ranks"] for d, s in st.session_state.stats.items()}
})
st.code(compact_json)
