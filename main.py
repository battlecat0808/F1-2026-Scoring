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
    return {"no": no, "team": team, "points": 0, "ranks": [], "point_history": [{"race": 0, "pts": 0}], 
            "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "prev_rank": 0}

# --- 2. 初始化與載入邏輯 ---
if "stats" not in st.session_state:
    st.session_state.stats = {d: init_driver_stats(d, c, t) for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
    st.session_state.race_no = 0
    st.session_state.sprint_history = []

with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("貼入壓縮存檔代碼：", height=150)
    if st.button("載入並重建賽季"):
        try:
            raw = json.loads(backup_input)
            st.session_state.race_no = raw["race_no"]
            st.session_state.sprint_history = raw.get("sprints", [])
            new_stats = {d: init_driver_stats(d, c, t) for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
            
            pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
            for d, r_list in raw["data"].items():
                s = new_stats[d]
                s["ranks"] = r_list
                curr_pts = 0
                for i, r in enumerate(r_list, 1):
                    # 加入該場次前的衝刺賽積分
                    for sp in st.session_state.sprint_history:
                        if sp["race_after"] == (i - 0.5):
                            curr_pts += sp["results"].get(d, 0)
                    
                    # 計算正賽積分
                    if r == 'R' or r == 25: s["dnf"] += 1
                    else:
                        if r == 1: s["p1"] += 1
                        elif r == 2: s["p2"] += 1
                        elif r == 3: s["p3"] += 1
                        curr_pts += pts_map.get(r, 0)
                    s["point_history"].append({"race": i, "pts": curr_pts})
                
                # 最後檢查是否有發生在最後一場正賽後的衝刺賽
                for sp in st.session_state.sprint_history:
                    if sp["race_after"] > len(r_list):
                        curr_pts += sp["results"].get(d, 0)
                
                s["points"] = curr_pts
            st.session_state.stats = new_stats
            st.success("數據已完美還原！")
            st.rerun()
        except Exception as e:
            st.error(f"解析失敗: {e}")

# --- 3. UI 標籤頁 ---
tabs = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 趨勢與完賽"])

with tabs[0]:
    st.subheader(f"第 {st.session_state.race_no + 1} 場比賽紀錄")
    mode = st.radio("比賽類型：", ["正賽", "衝刺賽"], horizontal=True)
    
    inputs = {}
    cols = st.columns(2)
    drivers_list = list(st.session_state.stats.keys())
    for idx, d in enumerate(drivers_list):
        with cols[idx % 2]:
            inputs[d] = st.text_input(f"{st.session_state.stats[d]['no']} {d} ({st.session_state.stats[d]['team']})", key=f"in_{d}")

    if st.button("提交成績", use_container_width=True):
        if mode == "正賽":
            st.session_state.race_no += 1
            pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
            for d, val in inputs.items():
                rank = 'R' if val.upper() == 'R' else int(val)
                st.session_state.stats[d]["ranks"].append(rank)
                p = pts_map.get(rank, 0) if isinstance(rank, int) else 0
                st.session_state.stats[d]["points"] += p
                st.session_state.stats[d]["point_history"].append({"race": st.session_state.race_no, "pts": st.session_state.stats[d]["points"]})
        else:
            # 衝刺賽 8-7-6-5-4-3-2-1
            s_res = {}
            sorted_s = sorted([(d, v) for d, v in inputs.items() if v.isdigit()], key=lambda x: int(x[1]))
            s_pts = [8, 7, 6, 5, 4, 3, 2, 1]
            for i, (d, r) in enumerate(sorted_s):
                p = s_pts[i] if i < 8 else 0
                st.session_state.stats[d]["points"] += p
                s_res[d] = p
            st.session_state.sprint_history.append({"race_after": st.session_state.race_no + 0.5, "results": s_res})
        st.rerun()

# --- 4. 車手與車隊榜 ---
with tabs[1]:
    df_d = pd.DataFrame([{"車手": d, "積分": s["points"], "P1": s["p1"], "DNF": s["dnf"], "車隊": s["team"]} for d, s in st.session_state.stats.items()])
    st.table(df_d.sort_values("積分", ascending=False).reset_index(drop=True))

with tabs[2]:
    team_pts = {}
    for d, s in st.session_state.stats.items():
        team_pts[s["team"]] = team_pts.get(s["team"], 0) + s["points"]
    df_t = pd.DataFrame([{"車隊": t, "積分": p} for t, p in team_pts.items()])
    st.table(df_t.sort_values("積分", ascending=False).reset_index(drop=True))

# --- 5. 趨勢與完賽矩陣 ---
with tabs[3]:
    # 積分趨勢圖
    hist_data = []
    for d, s in st.session_state.stats.items():
        for h in s["point_history"]:
            hist_data.append({"Race": h["race"], "Points": h["pts"], "Driver": d, "Team": s["team"]})
    if hist_data:
        fig = px.line(pd.DataFrame(hist_data), x="Race", y="Points", color="Driver", title="賽季積分走勢")
        st.plotly_chart(fig, use_container_width=True)

    # 完賽矩陣 (染色邏輯)
    st.subheader("每場完賽名次")
    matrix = []
    for d, s in st.session_state.stats.items():
        matrix.append([d] + s["ranks"])
    max_races = max([len(s["ranks"]) for s in st.session_state.stats.values()]) if st.session_state.stats else 0
    df_m = pd.DataFrame(matrix, columns=["Driver"] + [f"R{i+1}" for i in range(max_races)])
    
    def color_rank(val):
        if val == 1: return 'background-color: #FFD700; color: black'
        if val == 2: return 'background-color: #C0C0C0; color: black'
        if val == 3: return 'background-color: #CD7F32; color: black'
        if val == 'R' or val == 25: return 'background-color: #333; color: white'
        if isinstance(val, int) and val <= 10: return 'background-color: #E1FFD7; color: black'
        return ''
    st.dataframe(df_m.style.applymap(color_rank))

# --- 6. 底部導出 ---
st.divider()
st.subheader("📦 當前賽季壓縮代碼")
compact_json = json.dumps({
    "race_no": st.session_state.race_no,
    "sprints": st.session_state.sprint_history,
    "data": {d: s["ranks"] for d, s in st.session_state.stats.items()}
})
st.code(compact_json)
