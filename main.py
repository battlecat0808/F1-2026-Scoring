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
            new_team_h = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
            
            pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
            for i in range(1, st.session_state.race_no + 1):
                # A. 衝刺賽重建
                for sp in st.session_state.sprint_history:
                    if sp["race_after"] == (i - 0.5):
                        for d, p in sp["results"].items():
                            if d in new_stats:
                                new_stats[d]["points"] += p
                                new_stats[d]["point_history"].append({"race": i-0.5, "pts": new_stats[d]["points"]})
                        for t in TEAM_CONFIG:
                            t_pts = sum(s["points"] for d, s in new_stats.items() if s["team"] == t)
                            new_team_h[t].append({"race": i-0.5, "pts": t_pts})
                # B. 正賽重建
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
                # C. 車隊結算
                for t in TEAM_CONFIG:
                    t_pts = sum(s["points"] for d, s in new_stats.items() if s["team"] == t)
                    new_team_h[t].append({"race": float(i), "pts": t_pts})
            
            st.session_state.stats, st.session_state.team_history = new_stats, new_team_h
            st.success("✅ 重建成功"); st.rerun()
        except Exception as e: st.error(f"解析失敗: {e}")

# --- 4. 主程式 ---
st.title(f"🏎️ 2026 F1 賽季 (第 {st.session_state.race_no+1} 週)")
tabs = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置", "📈 數據圖表"])

# 預先計算目前排名
wdc_order = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1'], st.session_state.stats[x]['p2']), reverse=True)
wcc_order = sorted(TEAM_CONFIG.keys(), key=lambda x: (sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), sum(s["p1"] for d, s in st.session_state.stats.items() if s["team"] == x)), reverse=True)

with tabs[0]: # 輸入
    r_type = st.radio("本場類型：", ["正賽", "衝刺賽"], horizontal=True)
    inputs = {}
    cols = st.columns(3)
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 3]:
            st.markdown(f"**{team}**")
            for dr, no in cfg["drivers"].items():
                inputs[dr] = st.text_input(f"#{no} {dr}", key=f"in_{dr}_{st.session_state.form_id}", placeholder="1-24 / R")
    
    if st.button("🚀 提交成績", use_container_width=True, type="primary"):
        res, used, err = {}, set(), False
        for d, r in inputs.items():
            v = r.strip().upper()
            if v == 'R': res[d] = 'R'
            elif v.isdigit() and 1 <= int(v) <= 24 and int(v) not in used:
                res[d] = int(v); used.add(int(v))
            else: err = True; break
        
        if err or len(res) < 24: st.error("❌ 輸入無效或排名重複")
        else:
            if r_type == "正賽":
                # 紀錄當前排名作為上一場參考
                for i, n in enumerate(wdc_order, 1): st.session_state.stats[n]["prev_rank"] = i
                for i, t in enumerate(wcc_order, 1): st.session_state.team_prev_rank[t] = i
                
                st.session_state.race_no += 1
                p_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
                for d, r in res.items():
                    s = st.session_state.stats[d]
                    s["ranks"].append(r)
                    pts = 0
                    if r == 'R':
                        s["dnf"] += 1
                        if s["dnf"] % 5 == 0: s["penalty_next"] = True
                    else:
                        if r==1: s["p1"]+=1
                        elif r==2: s["p2"]+=1
                        elif r==3: s["p3"]+=1
                        if r <= 10:
                            pts = p_map[r] if not s["penalty_next"] else 0
                            s["penalty_next"] = False
                    s["points"] += pts
                    s["point_history"].append({"race": float(st.session_state.race_no), "pts": s["points"]})
            else:
                # 衝刺賽
                s_pts = {d: 0 for d in st.session_state.stats.keys()}
                for d, r in res.items():
                    if r != 'R': s_pts[d] += {1:5, 2:3, 3:1}.get(r, 0)
                # Bonus
                top10 = set(wdc_order[:10])
                non10 = sorted([(d, r) for d, r in res.items() if d not in top10 and r != 'R'], key=lambda x: x[1])
                bonus_pool = [8,7,6,5,4,3,2,1]
                for d, r in non10:
                    if bonus_pool: s_pts[d] += bonus_pool.pop(0)
                
                st.session_state.sprint_history.append({"race_after": st.session_state.race_no + 0.5, "results": s_pts, "ranks": res})
                for d, p in s_pts.items():
                    st.session_state.stats[d]["points"] += p
                    st.session_state.stats[d]["point_history"].append({"race": st.session_state.race_no + 0.5, "pts": st.session_state.stats[d]["points"]})
            
            for t in TEAM_CONFIG:
                cur_pts = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                st.session_state.team_history[t].append({"race": st.session_state.race_no + (0.5 if r_type == "衝刺賽" else 0), "pts": cur_pts})
            st.session_state.form_id += 1
            st.rerun()

with tabs[1]: # 車手榜
    d_rows = []
    new_wdc = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1']), reverse=True)
    for i, n in enumerate(new_wdc, 1):
        s = st.session_state.stats[n]
        pr = s["prev_rank"]
        trend = (f"🔼 {pr-i}" if pr>i else f"🔽 {i-pr}" if pr<i else "➖") if pr!=0 else ""
        avg = round(sum([r if isinstance(r, int) else 25 for r in s["ranks"]]) / len(s["ranks"]), 2) if s["ranks"] else 0
        d_rows.append([trend, i, s['no'], n, s['team'], s['points'], avg, f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf']])
    st.dataframe(pd.DataFrame(d_rows, columns=["趨勢","排名","#","車手","車隊","積分","平均名次","P1/P2/P3","DNF"]), use_container_width=True, hide_index=True)

with tabs[2]: # 車隊榜
    t_rows = []
    new_wcc = sorted(TEAM_CONFIG.keys(), key=lambda x: (sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), sum(s["p1"] for d, s in st.session_state.stats.items() if s["team"] == x)), reverse=True)
    for i, t in enumerate(new_wcc, 1):
        pr = st.session_state.team_prev_rank.get(t, 0)
        trend = (f"🔼 {pr-i}" if pr>i else f"🔽 {i-prev}" if pr<i else "➖") if pr!=0 else ""
        pts = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
        t_rows.append([trend, i, t, pts])
    st.dataframe(pd.DataFrame(t_rows, columns=["趨勢","排名","車隊","總積分"]), use_container_width=True, hide_index=True)

with tabs[3]: # 完賽位置
    pos_data = []
    for d in wdc_order:
        s = st.session_state.stats[d]
        row = {"車手": d}
        for i in range(1, st.session_state.race_no + 1):
            for sp in st.session_state.sprint_history:
                if sp["race_after"] == (i-0.5):
                    rk = sp["ranks"].get(d, "")
                    row[f"Rd.{i}(S)"] = 25 if rk == 'R' else rk
            if len(s["ranks"]) >= i:
                rk = s["ranks"][i-1]
                row[f"Rd.{i}(R)"] = 25 if rk == 'R' else rk
        pos_data.append(row)
    df_p = pd.DataFrame(pos_data)
    def style_p(v):
        if v == 1: return 'color: #D4AF37; font-weight: bold;'
        if v == 2: return 'color: #C0C0C0; font-weight: bold;'
        if v == 3: return 'color: #CD7F32; font-weight: bold;'
        if 4 <= v <= 10: return 'color: #28A745; font-weight: bold;'
        if v == 25: return 'color: #FF4B4B; font-weight: bold;'
        return 'color: #F1C40F;'
    st.dataframe(df_p.style.applymap(style_p, subset=[c for c in df_p.columns if "Rd." in c]), use_container_width=True, hide_index=True)

with tabs[4]: # 圖表
    dh = pd.DataFrame([{"Race": pt["race"], "Driver": f"#{s['no']} {d}", "Points": pt["pts"]} for d, s in st.session_state.stats.items() for pt in s['point_history']])
    if not dh.empty: st.plotly_chart(px.line(dh, x="Race", y="Points", color="Driver", color_discrete_map={f"#{s['no']} {d}": TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()}, template="plotly_dark", title="車手趨勢"), use_container_width=True)
    th = pd.DataFrame([{"Race": pt["race"], "Team": t, "Points": pt["pts"]} for t, h in st.session_state.team_history.items() for pt in h])
    if not th.empty: st.plotly_chart(px.line(th, x="Race", y="Points", color="Team", color_discrete_map={t: cfg["color"] for t, cfg in TEAM_CONFIG.items()}, template="plotly_dark", title="車隊趨勢"), use_container_width=True)

st.divider()
st.code(json.dumps({"race_no": st.session_state.race_no, "sprints": st.session_state.sprint_history, "data": {d: s["ranks"] for d, s in st.session_state.stats.items()}}))
