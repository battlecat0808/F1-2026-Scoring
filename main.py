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

# --- 2. 初始化函數 (載入重建時也會用到) ---
def init_driver_stats(name, no, team):
    return {
        "no": no, "team": team, "points": 0, "ranks": [], 
        "point_history": [{"race": 0, "pts": 0}], 
        "p1": 0, "p2": 0, "p3": 0, "dnf": 0, 
        "penalty_next": False, "prev_rank": 0
    }

if "stats" not in st.session_state:
    st.session_state.stats = {d: init_driver_stats(d, c, t) for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
    st.session_state.team_history = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
    st.session_state.team_prev_rank = {t: 0 for t in TEAM_CONFIG.keys()}
    st.session_state.race_no = 0
    st.session_state.form_id = 0

# --- 3. 側邊欄與壓縮載入邏輯 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("貼入壓縮存檔代碼：", height=100)
    
    if st.button("載入存檔"):
        try:
            raw = json.loads(backup_input)
            # 重建機制
            st.session_state.race_no = raw["race_no"]
            st.session_state.form_id = raw.get("form_id", 0)
            new_stats = {d: init_driver_stats(d, c, t) for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
            
            # 重新計算積分與歷史
            pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
            for d, r_list in raw["data"].items():
                s = new_stats[d]
                s["ranks"] = r_list
                for i, r in enumerate(r_list, 1):
                    p = 0
                    if r == 'R': s["dnf"] += 1
                    else:
                        if r == 1: s["p1"] += 1
                        elif r == 2: s["p2"] += 1
                        elif r == 3: s["p3"] += 1
                        p = pts_map.get(r, 0)
                    s["points"] += p
                    s["point_history"].append({"race": i, "pts": s["points"]})
            
            st.session_state.stats = new_stats
            # 重建車隊歷史
            st.session_state.team_history = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
            for i in range(1, st.session_state.race_no + 1):
                for t in TEAM_CONFIG.keys():
                    t_pts = sum(s["point_history"][i]["pts"] for d, s in st.session_state.stats.items() if s["team"] == t)
                    st.session_state.team_history[t].append({"race": i, "pts": t_pts})
            st.success("成功解壓縮並重建賽季！"); st.rerun()
        except Exception as e:
            st.error(f"解析失敗: {e}")

    if st.button("🚨 重置全賽季"):
        st.session_state.clear(); st.rerun()

# --- 4. 主介面邏輯 ---
st.title(f"🏎️ 2026 F1 賽季 (第 {st.session_state.race_no+1} 週)")
tabs = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置", "📈 數據圖表"])

with tabs[0]: # 成績輸入
    r_type = st.radio("本場類型：", ["正賽", "衝刺賽"], horizontal=True)
    wdc_order = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1']), reverse=True)
    
    inputs = {}
    cols = st.columns(2)
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 2]:
            st.markdown(f"**{team}**")
            for driver, no in cfg["drivers"].items():
                inputs[driver] = st.text_input(f"#{no} {driver}", key=f"in_{driver}_{st.session_state.form_id}", placeholder="1-22 / R")

    if st.button("🚀 提交成績", use_container_width=True, type="primary"):
        processed, used_ranks, err = {}, set(), False
        for d, r in inputs.items():
            v = r.strip().upper()
            if v == 'R': processed[d] = 'R'
            elif v.isdigit() and 1 <= int(v) <= 22 and int(v) not in used_ranks:
                processed[d] = int(v); used_ranks.add(int(v))
            else: err = True
        
        if err or len(processed) < 22:
            st.error("❌ 輸入無效（重複或漏填）")
        else:
            if r_type == "正賽":
                for i, name in enumerate(wdc_order, 1): st.session_state.stats[name]["prev_rank"] = i
                t_now = sorted(TEAM_CONFIG.keys(), key=lambda x: sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), reverse=True)
                for i, t_name in enumerate(t_now, 1): st.session_state.team_prev_rank[t_name] = i
                st.session_state.race_no += 1

            curr_m = st.session_state.race_no if r_type == "正賽" else st.session_state.race_no + 0.5
            
            if r_type == "正賽":
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                res_sorted = sorted(processed.items(), key=lambda x: 99 if x[1]=='R' else x[1])
                for d, r in res_sorted:
                    s = st.session_state.stats[d]
                    s["ranks"].append(r)
                    p = 0
                    if r == 'R': s["dnf"] += 1
                    else:
                        if r==1: s["p1"]+=1
                        elif r==2: s["p2"]+=1
                        elif r==3: s["p3"]+=1
                        if r <= 10 and pts_pool: p = pts_pool.pop(0)
                    s["points"] += p
                    s["point_history"].append({"race": curr_m, "pts": s["points"]})
            
            for t in TEAM_CONFIG.keys():
                t_pts = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                st.session_state.team_history[t].append({"race": curr_m, "pts": t_pts})
            st.session_state.form_id += 1
            st.rerun()

# --- 5. 榜單顯示 (含平均名次，R=25) ---
def get_avg(ranks):
    if not ranks: return "N/A"
    return round(sum([r if isinstance(r, int) else 25 for r in ranks]) / len(ranks), 2)

with tabs[1]: # 車手榜
    d_list = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1']), reverse=True)
    d_data = []
    for i, (n, s) in enumerate(d_list, 1):
        trend = f"🔼 {s['prev_rank']-i}" if s['prev_rank']-i > 0 else f"🔽 {abs(s['prev_rank']-i)}" if s['prev_rank']-i < 0 else "➖"
        d_data.append([trend if st.session_state.race_no > 0 else "", i, s['no'], n, s['team'], s['points'], get_avg(s['ranks']), f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf']])
    st.dataframe(pd.DataFrame(d_data, columns=["趨勢","排名","#","車手","車隊","積分","平均名次","P1/P2/P3","DNF"]), use_container_width=True, hide_index=True)

with tabs[2]: # 車隊榜
    t_list = []
    for t in TEAM_CONFIG.keys():
        ds = [s for d, s in st.session_state.stats.items() if s["team"] == t]
        all_ranks = []
        for d_s in ds: all_ranks.extend([r if isinstance(r, int) else 25 for r in d_s['ranks']])
        t_list.append({"name": t, "pts": sum(d["points"] for d in ds), "p1": sum(d["p1"] for d in ds), "avg": round(sum(all_ranks)/len(all_ranks), 2) if all_ranks else "N/A"})
    t_sort = sorted(t_list, key=lambda x: x["pts"], reverse=True)
    t_rows = [[i, t['name'], t['pts'], t['avg'], t['p1']] for i, t in enumerate(t_sort, 1)]
    st.dataframe(pd.DataFrame(t_rows, columns=["排名","車隊","總積分","平均名次","P1次數"]), use_container_width=True, hide_index=True)

with tabs[3]: # 完賽位置表 (字體染色)
    if st.session_state.race_no > 0:
        pos_df = pd.DataFrame([{"車手": d, "車隊": s['team'], **{f"Rd.{i+1}": (25 if r=='R' else r) for i, r in enumerate(s['ranks'])}} 
                               for d, s in sorted(st.session_state.stats.items(), key=lambda x: x[1]['points'], reverse=True)])
        
        def style_text(val):
            if not isinstance(val, int): return ''
            if val == 25: return 'color: #FF4B4B; font-weight: bold'
            if val == 1: return 'color: #D4AF37; font-weight: bold'
            if val == 2: return 'color: #808080; font-weight: bold'
            if val == 3: return 'color: #CD7F32; font-weight: bold'
            if 4 <= val <= 10: return 'color: #28a745; font-weight: bold'
            return 'color: #E5B800'

        rd_cols = [c for c in pos_df.columns if c.startswith("Rd.")]
        st.dataframe(pos_df.style.applymap(style_text, subset=rd_cols), use_container_width=True, hide_index=True)

with tabs[4]: # 圖表
    if st.session_state.race_no > 0:
        dh = [{"Race": pt["race"], "Driver": d, "Points": pt["pts"]} for d, s in st.session_state.stats.items() for pt in s['point_history']]
        st.plotly_chart(px.line(pd.DataFrame(dh), x="Race", y="Points", color="Driver", markers=True, 
                                color_discrete_map={d: TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()}, 
                                template="plotly_dark", title="積分趨勢"), use_container_width=True)

# --- 6. 壓縮存檔輸出 ---
compact_json = json.dumps({
    "race_no": st.session_state.race_no,
    "form_id": st.session_state.form_id,
    "data": {d: s["ranks"] for d, s in st.session_state.stats.items()}
})
st.divider()
st.subheader("📦 壓縮存檔代碼")
st.code(compact_json)
