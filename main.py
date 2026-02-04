import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Pro", page_icon="🏎️", layout="wide")

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

def init_driver_stats(name, no, team):
    return {
        "no": no, "team": team, "points": 0, "ranks": [], 
        "point_history": [{"race": 0, "pts": 0}], 
        "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "prev_rank": 0
    }

# --- 2. 初始化 ---
if "stats" not in st.session_state:
    st.session_state.stats = {d: init_driver_stats(d, c, t) for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
    st.session_state.race_no = 0
    st.session_state.form_id = 0
    st.session_state.sprints_data = []

# --- 3. 側邊欄：修正後的載入邏輯 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("貼入壓縮存檔代碼：", height=100)
    
    if st.button("載入存檔"):
        try:
            raw = json.loads(backup_input)
            st.session_state.race_no = raw["race_no"]
            st.session_state.sprints_data = raw.get("sprints", [])
            
            # 重建車手狀態
            temp_stats = {d: init_driver_stats(d, c, t) for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
            pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
            
            # 按比賽順序重新模擬積分演進 (為了正確生成 point_history)
            max_r = st.session_state.race_no
            for i in range(1, max_r + 1):
                # 1. 檢查是否有賽前的衝刺賽 (例如 Rd 0.5, 1.5...)
                for sp in st.session_state.sprints_data:
                    if sp["race_after"] == (i - 0.5):
                        for d, p in sp["results"].items():
                            temp_stats[d]["points"] += p
                
                # 2. 處理正賽
                for d, r_list in raw["data"].items():
                    if len(r_list) >= i:
                        r = r_list[i-1]
                        temp_stats[d]["ranks"].append(r)
                        if r == 'R': temp_stats[d]["dnf"] += 1
                        else:
                            if r == 1: temp_stats[d]["p1"] += 1
                            elif r == 2: temp_stats[d]["p2"] += 1
                            elif r == 3: temp_stats[d]["p3"] += 1
                            temp_stats[d]["points"] += pts_map.get(r, 0)
                        temp_stats[d]["point_history"].append({"race": i, "pts": temp_stats[d]["points"]})

            st.session_state.stats = temp_stats
            st.success("數據完美重建！"); st.rerun()
        except Exception as e:
            st.error(f"解析失敗: {e}")

# --- 4. 主介面：優化提交邏輯 ---
st.title(f"🏎️ 2026 F1 賽季 (第 {st.session_state.race_no+1} 週)")
tabs = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置", "📈 數據圖表"])

with tabs[0]: 
    r_type = st.radio("本場類型：", ["正賽", "衝刺賽"], horizontal=True)
    cols = st.columns(2)
    inputs = {}
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 2]:
            st.markdown(f"**{team}**")
            for driver, no in cfg["drivers"].items():
                inputs[driver] = st.text_input(f"#{no} {driver}", key=f"in_{driver}_{st.session_state.form_id}")

    if st.button("🚀 提交成績", use_container_width=True, type="primary"):
        # 簡單驗證邏輯
        processed = {d: (int(v) if v.isdigit() else v.upper()) for d, v in inputs.items() if v}
        if len(processed) < 22:
            st.error("請填寫所有車手成績")
        else:
            if r_type == "正賽":
                st.session_state.race_no += 1
                pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
                for d, r in processed.items():
                    s = st.session_state.stats[d]
                    s["ranks"].append(r)
                    if r == 1: s["p1"] += 1
                    elif r == 'R': s["dnf"] += 1
                    s["points"] += pts_map.get(r, 0)
                    s["point_history"].append({"race": st.session_state.race_no, "pts": s["points"]})
            else:
                s_res = {}
                sorted_s = sorted(processed.items(), key=lambda x: 99 if x[1]=='R' else x[1])
                s_pts = [8, 7, 6, 5, 4, 3, 2, 1]
                for i, (d, r) in enumerate(sorted_s):
                    p = s_pts[i] if i < 8 and isinstance(r, int) else 0
                    st.session_state.stats[d]["points"] += p
                    s_res[d] = p
                st.session_state.sprints_data.append({"race_after": st.session_state.race_no + 0.5, "results": s_res})
            
            st.session_state.form_id += 1
            st.rerun()

# --- 5. 榜單與圖表 (維持你要求的渲染架構) ---
with tabs[1]: # 車手榜
    d_data = []
    for n, s in st.session_state.stats.items():
        avg = round(sum([r if isinstance(r, int) else 25 for r in s['ranks']]) / len(s['ranks']), 2) if s['ranks'] else "-"
        d_data.append([s['no'], n, s['team'], s['points'], avg, s['p1'], s['dnf']])
    df_wdc = pd.DataFrame(d_data, columns=["#", "車手", "車隊", "積分", "平均名次", "P1", "DNF"]).sort_values("積分", ascending=False)
    st.dataframe(df_wdc, use_container_width=True, hide_index=True)

with tabs[3]: # 完賽位置染色 (確保 Rd. 標題正確)
    if st.session_state.race_no > 0:
        matrix = []
        for d, s in st.session_state.stats.items():
            matrix.append({"車手": d, **{f"Rd.{i+1}": r for i, r in enumerate(s['ranks'])}})
        df_m = pd.DataFrame(matrix)
        def color_map(val):
            if val == 1: return 'background-color: #FFD700; color: black'
            if val == 'R': return 'background-color: #444; color: white'
            return ''
        st.dataframe(df_m.style.applymap(color_map), use_container_width=True)

with tabs[4]: # 圖表
    hist = []
    for d, s in st.session_state.stats.items():
        for h in s["point_history"]:
            hist.append({"Race": h["race"], "Points": h["pts"], "Driver": d})
    if hist:
        st.plotly_chart(px.line(pd.DataFrame(hist), x="Race", y="Points", color="Driver", template="plotly_dark"))

# --- 6. 輸出 ---
st.code(json.dumps({
    "race_no": st.session_state.race_no,
    "sprints": st.session_state.sprints_data,
    "data": {d: s["ranks"] for d, s in st.session_state.stats.items()}
}))
