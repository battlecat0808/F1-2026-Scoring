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
    st.session_state.sprint_history = [] # 格式: {"race_after": 8.5, "results": {name: pts}, "ranks": {name: rank}}

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
            new_team_h = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
            
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
                # 車隊歷史
                for t in TEAM_CONFIG.keys():
                    t_sum = sum(s["points"] for d, s in new_stats.items() if s["team"] == t)
                    new_team_h[t].append({"race": float(i), "pts": t_sum})
            st.session_state.stats, st.session_state.team_history = new_stats, new_team_h
            st.success("✅ 賽季重建成功！"); st.rerun()
        except Exception as e: st.error(f"解析失敗: {e}")

# --- 4. 主程式 ---
st.title(f"🏎️ 2026 F1 賽季 (第 {st.session_state.race_no+1} 週)")
tabs = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置", "📈 數據圖表"])

wdc_order = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1'], st.session_state.stats[x]['p2'], st.session_state.stats[x]['p3']), reverse=True)

with tabs[0]: # 成績輸入
    r_type = st.radio("本場類型：", ["正賽", "衝刺賽"], horizontal=True)
    inputs = {}
    cols = st.columns(2)
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 2]:
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
        
        if err: st.error("❌ 輸入格式錯誤或排名重複！")
        else:
            if r_type == "正賽":
                for i, name in enumerate(wdc_order, 1): st.session_state.stats[name]["prev_rank"] = i
                t_now = sorted(TEAM_CONFIG.keys(), key=lambda x: (sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), sum(s["p1"] for d, s in st.session_state.stats.items() if s["team"] == x)), reverse=True)
                for i, t_name in enumerate(t_now, 1): st.session_state.team_prev_rank[t_name] = i
                
                st.session_state.race_no += 1
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
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
                        if r <= 10:
                            p = pts_pool[r-1] if not s["penalty_next"] else 0
                            s["penalty_next"] = False
                    s["points"] += p
                    s["point_history"].append({"race": float(st.session_state.race_no), "pts": s["points"]})
            else:
                top_10 = set(wdc_order[:10])
                s_pts, s_ranks = {d: 0 for d in st.session_state.stats.keys()}, {d: r for d, r in processed.items()}
                for d, r in processed.items():
                    if r != 'R': s_pts[d] += {1: 5, 2: 3, 3: 1}.get(r, 0)
                non_t10 = sorted([(d, r) for d, r in processed.items() if d not in top_10 and r != 'R'], key=lambda x: x[1])
                bonus = [8, 7, 6, 5, 4, 3, 2, 1]
                for d, r in non_t10:
                    if bonus: s_pts[d] += bonus.pop(0)
                st.session_state.sprint_history.append({"race_after": st.session_state.race_no + 0.5, "results": s_pts, "ranks": s_ranks})
                for d, p in s_pts.items():
                    st.session_state.stats[d]["points"] += p
                    st.session_state.stats[d]["point_history"].append({"race": st.session_state.race_no + 0.5, "pts": st.session_state.stats[d]["points"]})
            
            for t in TEAM_CONFIG.keys():
                t_sum = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                st.session_state.team_history[t].append({"race": float(st.session_state.race_no), "pts": t_sum})
            st.session_state.form_id += 1
            st.rerun()

with tabs[1]: # WDC
    d_rows = []
    for i, n in enumerate(wdc_order, 1):
        s = st.session_state.stats[n]
        trend = (f"🔼 {s['prev_rank']-i}" if s['prev_rank']>i else f"🔽 {i-s['prev_rank']}" if s['prev_rank']<i else "➖") if st.session_state.race_no >= 1 and s['prev_rank']!=0 else ""
        avg = round(sum([r if isinstance(r, int) else 25 for r in s["ranks"]]) / len(s["ranks"]), 2) if s["ranks"] else "N/A"
        d_rows.append([trend, i, s['no'], n, s['team'], s['points'], avg, f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf']])
    st.dataframe(pd.DataFrame(d_rows, columns=["趨勢","排名","#","車手","車隊","積分","平均名次","P1/P2/P3","DNF"]), use_container_width=True, hide_index=True)

with tabs[2]: # WCC
    t_sort = sorted(TEAM_CONFIG.keys(), key=lambda x: (sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), sum(s["p1"] for d, s in st.session_state.stats.items() if s["team"] == x)), reverse=True)
    t_rows = []
    for i, t in enumerate(t_sort, 1):
        prev = st.session_state.team_prev_rank.get(t, 0)
        trend = (f"🔼 {prev-i}" if prev>i else f"🔽 {i-prev}" if prev<i else "➖") if st.session_state.race_no >= 1 and prev!=0 else ""
        pts = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
        t_rows.append([trend, i, t, pts])
    st.dataframe(pd.DataFrame(t_rows, columns=["趨勢","排名","車隊","總積分"]), use_container_width=True, hide_index=True)

with tabs[3]: # 完賽位置 (含衝刺賽)
    if st.session_state.race_no > 0 or st.session_state.sprint_history:
        pos_rows = []
        for d in wdc_order:
            s = st.session_state.stats[d]
            row = {"車手": d}
            # 整合正賽與衝刺賽
            for i in range(1, st.session_state.race_no + 1):
                # 檢查該場正賽前是否有衝刺賽
                for sp in st.session_state.sprint_history:
                    if sp["race_after"] == (i - 0.5):
                        row[f"Rd.{i}(S)"] = 25 if sp["ranks"].get(d) == 'R' else sp["ranks"].get(d)
                # 正賽
                if len(s["ranks"]) >= i:
                    row[f"Rd.{i}(R)"] = 25 if s["ranks"][i-1] == 'R' else s["ranks"][i-1]
            pos_rows.append(row)
        df_p = pd.DataFrame(pos_rows)
        def style_pos(v):
            if v == 1: return 'color: #D4AF37; font-weight: bold;' # 金
            if v == 2: return 'color: #C0C0C0; font-weight: bold;' # 銀
            if v == 3: return 'color: #CD7F32; font-weight: bold;' # 銅
            if 4 <= v <= 10: return 'color: #28A745; font-weight: bold;' # 綠
            if v == 25: return 'color: #FF4B4B; font-weight: bold;' # 紅
            return 'color: #F1C40F;' # 黃
        st.dataframe(df_p.style.applymap(style_pos, subset=[c for c in df_p.columns if "Rd." in c]), use_container_width=True, hide_index=True)

with tabs[4]: # 圖表
    dh = [{"Race": pt["race"], "Driver": f"#{s['no']} {d}", "Points": pt["pts"]} for d, s in st.session_state.stats.items() for pt in s['point_history']]
    st.plotly_chart(px.line(pd.DataFrame(dh), x="Race", y="Points", color="Driver", markers=True, color_discrete_map={f"#{s['no']} {d}": TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()}, template="plotly_dark", title="車手積分趨勢"), use_container_width=True)
    th = [{"Race": pt["race"], "Team": t, "Points": pt["pts"]} for t, h in st.session_state.team_history.items() for pt in h]
    st.plotly_chart(px.line(pd.DataFrame(th), x="Race", y="Points", color="Team", markers=True, color_discrete_map={t: cfg["color"] for t, cfg in TEAM_CONFIG.items()}, template="plotly_dark", title="車隊積分趨勢"), use_container_width=True)

st.divider()
st.code(json.dumps({"race_no": st.session_state.race_no, "sprints": st.session_state.sprint_history, "data": {d: s["ranks"] for d, s in st.session_state.stats.items()}}))
