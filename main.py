import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Ultimate", page_icon="🏎️", layout="wide")

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
    "APX-CTWR": {"color": "#000000", "drivers": {"Yuki Tsunoda": "22", "Ethan Tan": "9"}},
    "Cadillac": {"color": "#FFCC00", "drivers": {"Sergio Perez": "11", "Valtteri Bottas": "77"}}
}

# --- 2. 初始化 ---
if "stats" not in st.session_state:
    st.session_state.stats = {d: {"no": c, "team": t, "points": 0, "ranks": [], "point_history": [{"race": 0, "pts": 0}], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False, "prev_rank": 0} 
                             for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
    st.session_state.team_history = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
    st.session_state.team_prev_rank = {t: 0 for t in TEAM_CONFIG.keys()}
    st.session_state.race_no = 0
    st.session_state.form_id = 0
    st.session_state.sprint_history = []

# --- 3. 側邊欄：重建邏輯 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("貼入存檔代碼：", height=100)
    if st.button("載入並重建賽季"):
        try:
            raw = json.loads(backup_input)
            st.session_state.race_no = raw["race_no"]
            st.session_state.sprint_history = raw.get("sprints", [])
            new_stats = {d: {"no": c, "team": t, "points": 0, "ranks": [], "point_history": [{"race": 0, "pts": 0}], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False, "prev_rank": 0} 
                         for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
            
            pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
            for i in range(1, st.session_state.race_no + 1):
                # 衝刺賽
                for sp in st.session_state.sprint_history:
                    if sp["race_after"] == (i - 0.5):
                        for d, p in sp["results"].items():
                            if d in new_stats:
                                new_stats[d]["points"] += p
                                new_stats[d]["point_history"].append({"race": i-0.5, "pts": new_stats[d]["points"]})
                # 正賽
                for d, r_list in raw["data"].items():
                    if d in new_stats and len(r_list) >= i:
                        r = r_list[i-1]
                        s = new_stats[d]
                        s["ranks"].append(r)
                        if r == 'R': s["dnf"] += 1
                        else:
                            if r == 1: s["p1"] += 1
                            elif r == 2: s["p2"] += 1
                            elif r == 3: s["p3"] += 1
                            s["points"] += pts_map.get(r, 0)
                        s["point_history"].append({"race": float(i), "pts": s["points"]})
            
            st.session_state.stats = new_stats
            st.session_state.team_history = {t: [{"race": 0, "pts": sum(s["points"] for d, s in new_stats.items() if s["team"] == t)}] for t in TEAM_CONFIG.keys()}
            st.success("數據重建完成！"); st.rerun()
        except Exception as e:
            st.error(f"解析失敗: {e}")

# --- 4. 主程式 ---
st.title(f"🏎️ 2026 F1 賽季 (Rd.{st.session_state.race_no+1})")
tab_input, tab_wdc, tab_wcc, tab_pos, tab_chart = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置", "📈 數據圖表"])

wdc_order = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1'], st.session_state.stats[x]['p2'], st.session_state.stats[x]['p3']), reverse=True)

with tab_input:
    r_type = st.radio("本場類型：", ["正賽", "衝刺賽"], horizontal=True)
    inputs = {}
    cols = st.columns(3)
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 3]:
            st.markdown(f"**{team}**")
            for driver, no in cfg["drivers"].items():
                inputs[driver] = st.text_input(f"#{no} {driver}", key=f"in_{driver}_{st.session_state.form_id}", placeholder="1-24 / R")
    
    if st.button("🚀 提交成績", use_container_width=True, type="primary"):
        processed, used_ranks, err = {}, set(), False
        for d, r in inputs.items():
            v = r.strip().upper()
            if v == 'R': processed[d] = 'R'
            elif not v: err = True; break
            else:
                try:
                    n = int(v)
                    if 1 <= n <= 24 and n not in used_ranks: processed[d] = n; used_ranks.add(n)
                    else: err = True; break
                except: err = True; break

        if err: st.error("❌ 格式錯誤或排名重複")
        else:
            curr_mark = st.session_state.race_no + (1.0 if r_type == "正賽" else 0.5)
            if r_type == "正賽":
                for i, name in enumerate(wdc_order, 1): st.session_state.stats[name]["prev_rank"] = i
                st.session_state.race_no += 1
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                for d, r in processed.items():
                    s = st.session_state.stats[d]
                    s["ranks"].append(r)
                    p = pts_pool[r-1] if isinstance(r, int) and r <= 10 else 0
                    if r == 'R': s["dnf"] += 1; p = 0
                    elif r == 1: s["p1"] += 1
                    elif r == 2: s["p2"] += 1
                    elif r == 3: s["p3"] += 1
                    s["points"] += p
                    s["point_history"].append({"race": float(st.session_state.race_no), "pts": s["points"]})
            else:
                # 衝刺賽
                s_res = {d: 0 for d in st.session_state.stats.keys()}
                for d, r in processed.items():
                    if r != 'R': s_res[d] += {1: 5, 2: 3, 3: 1}.get(r, 0)
                top_10 = set(wdc_order[:10])
                non_top = sorted([(d, r) for d, r in processed.items() if d not in top_10 and r != 'R'], key=lambda x: x[1])
                bonus = [8, 7, 6, 5, 4, 3, 2, 1]
                for d, r in non_top:
                    if bonus: s_res[d] += bonus.pop(0)
                st.session_state.sprint_history.append({"race_after": curr_mark, "results": s_res, "raw_ranks": processed})
                for d, p in s_res.items():
                    st.session_state.stats[d]["points"] += p
                    st.session_state.stats[d]["point_history"].append({"race": curr_mark, "pts": st.session_state.stats[d]["points"]})
            
            st.session_state.form_id += 1
            st.rerun()

# --- 5. 榜單顯示 ---
with tab_wdc:
    d_rows = []
    for i, name in enumerate(wdc_order, 1):
        s = st.session_state.stats[name]
        avg = round(sum([r if isinstance(r, int) else 25 for r in s["ranks"]]) / len(s["ranks"]), 2) if s["ranks"] else 0
        d_rows.append([i, s['no'], name, s['team'], s['points'], avg, f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf']])
    st.dataframe(pd.DataFrame(d_rows, columns=["排名","#","車手","車隊","積分","平均名次","P1/P2/P3","DNF"]), use_container_width=True, hide_index=True)

with tab_wcc:
    t_sort = sorted(TEAM_CONFIG.keys(), key=lambda x: sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), reverse=True)
    t_rows = []
    for i, t in enumerate(t_sort, 1):
        ds = [s for d, s in st.session_state.stats.items() if s["team"] == t]
        all_r = [r if isinstance(r, int) else 25 for s in ds for r in s["ranks"]]
        t_rows.append([i, t, sum(s["points"] for s in ds), round(sum(all_r)/len(all_r), 2) if all_r else 0, f"{sum(s['p1'] for s in ds)}/{sum(s['p2'] for s in ds)}/{sum(s['p3'] for s in ds)}"])
    st.dataframe(pd.DataFrame(t_rows, columns=["排名","車隊","總積分","平均完賽","P1/P2/P3"]), use_container_width=True, hide_index=True)

with tab_pos:
    if st.session_state.race_no > 0:
        pos_df_data = []
        for d in wdc_order:
            s = st.session_state.stats[d]
            row = {"車手": d, "車隊": s["team"]}
            # 遍歷正賽
            for i in range(1, st.session_state.race_no + 1):
                # 檢查該場正賽前是否有衝刺賽
                for sp in st.session_state.sprint_history:
                    if sp["race_after"] == (i - 0.5):
                        row[f"Rd.{i}(S)"] = sp["raw_ranks"].get(d, 25)
                row[f"Rd.{i}"] = s["ranks"][i-1] if i <= len(s["ranks"]) else 25
            pos_df_data.append(row)
        
        df_final = pd.DataFrame(pos_df_data).fillna("-")
        def style_pos(v):
            if v == 'R' or v == 25: return 'color: #FF4B4B; font-weight: bold'
            if v == 1: return 'background-color: #D4AF37; color: black; font-weight: bold'
            if v == 2: return 'background-color: #C0C0C0; color: black; font-weight: bold'
            if v == 3: return 'background-color: #CD7F32; color: black; font-weight: bold'
            if isinstance(v, int) and v <= 10: return 'color: #28a745; font-weight: bold'
            return ''
        st.dataframe(df_final.style.applymap(style_pos, subset=[c for c in df_final.columns if "Rd." in c]), use_container_width=True, hide_index=True)

with tab_chart:
    dh = [{"Race": pt["race"], "Driver": d, "Points": pt["pts"]} for d, s in st.session_state.stats.items() for pt in s['point_history']]
    st.plotly_chart(px.line(pd.DataFrame(dh), x="Race", y="Points", color="Driver", markers=True, template="plotly_dark", color_discrete_map={d: TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()}), use_container_width=True)

# 導出
st.code(json.dumps({"race_no": st.session_state.race_no, "sprints": st.session_state.sprint_history, "data": {d: s["ranks"] for d, s in st.session_state.stats.items()}}))
