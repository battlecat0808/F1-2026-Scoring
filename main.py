import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Ultimate", page_icon="🏎️", layout="wide")

# --- 1. 核心設定 (新增 Cadillac 與調整車手) ---
TEAM_CONFIG = {
    "McLaren": {"color": "#FF8700", "drivers": {"Lando Norris": "1", "Oscar Piastri": "81"}},
    "Ferrari": {"color": "#E80020", "drivers": {"Lewis Hamilton": "44", "Charles Leclerc": "16"}},
    "Red Bull": {"color": "#3671C6", "drivers": {"Max Verstappen": "3", "Isack Hadjar": "66"}},
    "Mercedes": {"color": "#27F4D2", "drivers": {"George Russell": "63", "Kimi Antonelli": "12"}},
    "Aston Martin": {"color": "#229971", "drivers": {"Fernando Alonso": "14", "Lance Stroll": "18"}},
    "Audi": {"color": "#F50A20", "drivers": {"Nico Hulkenberg": "27", "Ethan Tan": "9"}},
    "Williams": {"color": "#64C4FF", "drivers": {"Carlos Sainz": "55", "Alex Albon": "23"}},
    "Alpine": {"color": "#0093CC", "drivers": {"Pierre Gasly": "10", "Franco Colapinto": "43"}},
    "Racing Bulls": {"color": "#6692FF", "drivers": {"Liam Lawson": "30", "Arvid Lindblad": "17"}},
    "Haas": {"color": "#B6BABD", "drivers": {"Esteban Ocon": "31", "Oliver Bearman": "87"}},
    "APX-CTWR": {"color": "#FFD700", "drivers": {"Yuki Tsunoda": "22", "Zhou Guanyu": "24"}},
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

# --- 3. 側邊欄 (修正縮排與重建邏輯) ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("貼入精簡存檔代碼：", height=100)
    
    if st.button("載入並重建賽季"):
        try:
            raw = json.loads(backup_input)
            st.session_state.race_no = raw["race_no"]
            st.session_state.sprint_history = raw.get("sprints", [])
            
            new_stats = {d: {"no": c, "team": t, "points": 0, "ranks": [], "point_history": [{"race": 0, "pts": 0}], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False, "prev_rank": 0} 
                         for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
            new_team_history = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
            
            pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
            
            for i in range(1, st.session_state.race_no + 1):
                # A. 處理該場之前的衝刺賽
                for sp in st.session_state.sprint_history:
                    if sp["race_after"] == (i - 0.5):
                        for d, p in sp["results"].items():
                            if d in new_stats:
                                new_stats[d]["points"] += p
                                new_stats[d]["point_history"].append({"race": i-0.5, "pts": new_stats[d]["points"]})
                
                # B. 處理正賽
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
                        s["point_history"].append({"race": i, "pts": s["points"]})

                # C. 重建車隊趨勢
                for t in TEAM_CONFIG.keys():
                    t_sum = sum(s["points"] for d, s in new_stats.items() if s["team"] == t)
                    new_team_history[t].append({"race": i, "pts": t_sum})

            st.session_state.stats = new_stats
            st.session_state.team_history = new_team_history
            st.success("賽季與 Cadillac 數據重建成功！")
            st.rerun()
        except Exception as e:
            st.error(f"解析失敗: {e}")

# --- 4. 主程式 ---
st.title(f"🏎️ 2026 F1 賽季 (第 {st.session_state.race_no+1} 週)")
tab_input, tab_wdc, tab_wcc, tab_pos, tab_chart = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置", "📈 數據圖表"])

with tab_input:
    r_type = st.radio("本場類型：", ["正賽", "衝刺賽"], horizontal=True)
    wdc_order = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1'], st.session_state.stats[x]['p2'], st.session_state.stats[x]['p3']), reverse=True)
    top_10_names = set(wdc_order[:10])

    st.markdown("---")
    inputs = {}
    cols = st.columns(2)
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 2]:
            st.markdown(f"**{team}**")
            for driver, no in cfg["drivers"].items():
                k = f"in_{driver}_{st.session_state.form_id}"
                inputs[driver] = st.text_input(f"#{no} {driver}", key=k, placeholder="1-24 / R")
    
    if st.button("🚀 提交成績", use_container_width=True, type="primary"):
        processed, used_ranks, err = {}, set(), False
        err_msg = ""
        for d, r in inputs.items():
            v = r.strip().upper()
            if v == 'R': processed[d] = 'R'
            elif not v: err = True; err_msg = "有欄位漏填！"
            else:
                try:
                    n = int(v)
                    if 1 <= n <= 24 and n not in used_ranks:
                        processed[d] = n; used_ranks.add(n)
                    else: err = True; err_msg = f"排名 {n} 重複或超出範圍！"
                except: err = True; err_msg = f"'{v}' 格式不對！"

        if err: st.error(f"❌ {err_msg}")
        else:
            # 紀錄賽前排名
            for i, name in enumerate(wdc_order, 1): st.session_state.stats[name]["prev_rank"] = i
            t_now_rank = sorted(TEAM_CONFIG.keys(), key=lambda x: sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), reverse=True)
            for i, t_name in enumerate(t_now_rank, 1): st.session_state.team_prev_rank[t_name] = i

            if r_type == "正賽":
                st.session_state.race_no += 1
                curr_mark = float(st.session_state.race_no)
                pts_pool = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
                for d, r in processed.items():
                    s = st.session_state.stats[d]
                    s["ranks"].append(r)
                    p = 0
                    if r == 'R':
                        s["dnf"] += 1
                        if s["dnf"] % 5 == 0: s["penalty_next"] = True
                    else:
                        if r==1: s["p1"]+=1
                        elif r==2: s["p2"]+=1
                        elif r==3: s["p3"]+=1
                        if not s["penalty_next"]: p = pts_pool.get(r, 0)
                        else: s["penalty_next"] = False
                    s["points"] += p
                    s["point_history"].append({"race": curr_mark, "pts": s["points"]})
            else:
                curr_mark = st.session_state.race_no + 0.5
                s_pts = {d: 0 for d in st.session_state.stats.keys()}
                for d, r in processed.items():
                    if r != 'R': s_pts[d] += {1: 5, 2: 3, 3: 1}.get(r, 0)
                non_top = [(d, r) for d, r in processed.items() if d not in top_10_names and r != 'R']
                non_top.sort(key=lambda x: x[1])
                bonus = [8, 7, 6, 5, 4, 3, 2, 1]
                for d, r in non_top:
                    if bonus: s_pts[d] += bonus.pop(0)
                st.session_state.sprint_history.append({"race_after": curr_mark, "results": s_pts})
                for d, p in s_pts.items():
                    st.session_state.stats[d]["points"] += p
                    st.session_state.stats[d]["point_history"].append({"race": curr_mark, "pts": st.session_state.stats[d]["points"]})

            for t in TEAM_CONFIG.keys():
                t_sum = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                st.session_state.team_history[t].append({"race": curr_mark, "pts": t_sum})
            st.session_state.form_id += 1
            st.rerun()

# --- 5. 榜單顯示 (略，邏輯保持不變) ---
with tab_wdc:
    d_sort = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1'], x[1]['p2'], x[1]['p3']), reverse=True)
    d_data = []
    for i, (n, s) in enumerate(d_sort, 1):
        trend = (f"🔼 {s['prev_rank']-i}" if s['prev_rank']-i > 0 else f"🔽 {i-s['prev_rank']}" if s['prev_rank']-i < 0 else "➖") if st.session_state.race_no >= 1 and s['prev_rank'] != 0 else ""
        d_data.append([trend, i, s['no'], n, s['team'], s['points'], f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf']])
    st.dataframe(pd.DataFrame(d_data, columns=["趨勢","排名","#","車手","車隊","積分","P1/P2/P3","DNF"]), use_container_width=True, hide_index=True)

with tab_wcc:
    t_list = []
    for t in TEAM_CONFIG.keys():
        ds = [s for d, s in st.session_state.stats.items() if s["team"] == t]
        t_list.append({"team": t, "pts": sum(d["points"] for d in ds), "p1": sum(d["p1"] for d in ds), "p2": sum(d["p2"] for d in ds), "p3": sum(d["p3"] for d in ds)})
    t_sort = sorted(t_list, key=lambda x: (x["pts"], x["p1"], x["p2"], x["p3"]), reverse=True)
    t_rows = []
    for i, t in enumerate(t_sort, 1):
        prev = st.session_state.team_prev_rank.get(t['team'], 0)
        trend = (f"🔼 {prev-i}" if prev-i > 0 else f"🔽 {i-prev}" if prev-i < 0 else "➖") if st.session_state.race_no >= 1 and prev != 0 else ""
        t_rows.append([trend, i, t["team"], t["pts"], f"{t['p1']}/{t['p2']}/{t['p3']}"])
    st.dataframe(pd.DataFrame(t_rows, columns=["趨勢","排名","車隊","總積分","P1/P2/P3"]), use_container_width=True, hide_index=True)

with tab_pos:
    if st.session_state.race_no > 0:
        pos_data = []
        for d in wdc_order:
            s = st.session_state.stats[d]
            row = {"車手": d, "車隊": s['team']}
            for i, r in enumerate(s["ranks"], 1): row[f"Rd.{i}"] = r
            pos_data.append(row)
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True, hide_index=True)

with tab_chart:
    if st.session_state.race_no > 0:
        dh = [{"Race": pt["race"], "Driver": d, "Points": pt["pts"]} for d, s in st.session_state.stats.items() for pt in s['point_history']]
        st.plotly_chart(px.line(pd.DataFrame(dh), x="Race", y="Points", color="Driver", markers=True, template="plotly_dark", title="車手積分趨勢"), use_container_width=True)
        th = [{"Race": pt["race"], "Team": t, "Points": pt["pts"]} for t, h in st.session_state.team_history.items() for pt in h]
        st.plotly_chart(px.line(pd.DataFrame(th), x="Race", y="Points", color="Team", markers=True, color_discrete_map={t: cfg["color"] for t, cfg in TEAM_CONFIG.items()}, template="plotly_dark", title="車隊積分趨勢"), use_container_width=True)

# --- 6. 導出存檔 ---
compact_data = {
    "race_no": st.session_state.race_no,
    "sprints": st.session_state.sprint_history,
    "data": {d: s["ranks"] for d, s in st.session_state.stats.items()}
}
st.divider()
st.subheader("📦 2026 存檔代碼")
st.code(json.dumps(compact_data))
