import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Ultimate", page_icon="🏎️", layout="wide")

# --- 1. 核心設定 (12 隊 24 人) ---
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
    backup_input = st.text_area("貼入精簡存檔代碼：", height=100)
    
    if st.button("載入並重建賽季"):
        try:
            raw = json.loads(backup_input)
            st.session_state.race_no = raw["race_no"]
            st.session_state.sprint_history = raw.get("sprints", [])
            new_stats = {d: {"no": c, "team": t, "points": 0, "ranks": [], "point_history": [{"race": 0, "pts": 0}], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False, "prev_rank": 0} 
                         for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
            new_team_hist = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
            pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
            
            for i in range(1, st.session_state.race_no + 1):
                for sp in st.session_state.sprint_history:
                    if sp["race_after"] == (i - 0.5):
                        for d, p in sp["results"].items():
                            if d in new_stats:
                                new_stats[d]["points"] += p
                                new_stats[d]["point_history"].append({"race": i-0.5, "pts": new_stats[d]["points"]})
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
                for t in TEAM_CONFIG.keys():
                    t_sum = sum(s["points"] for d, s in new_stats.items() if s["team"] == t)
                    new_team_hist[t].append({"race": float(i), "pts": t_sum})
            st.session_state.stats, st.session_state.team_history = new_stats, new_team_hist
            st.success("✅ 重建成功！"); st.rerun()
        except Exception as e:
            st.error(f"解析失敗: {e}")

# --- 4. 輔助功能 ---
def style_ranks(val):
    if val == 25 or val == 'R': return 'background-color: #4B0000; color: #FF4B4B; font-weight: bold'
    if val == 1: return 'background-color: #5C4B00; color: #D4AF37; font-weight: bold'
    if val == 2: return 'background-color: #3D3D3D; color: #C0C0C0; font-weight: bold'
    if val == 3: return 'background-color: #4B2E00; color: #CD7F32; font-weight: bold'
    if isinstance(val, int) and 4 <= val <= 10: return 'color: #28a745; font-weight: bold'
    return ''

# --- 5. 主程式頁面 ---
st.title(f"🏎️ 2026 F1 賽季 (第 {st.session_state.race_no+1} 週)")
tabs = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置", "📈 數據圖表"])

wdc_order = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1'], st.session_state.stats[x]['p2'], st.session_state.stats[x]['p3']), reverse=True)

with tabs[0]: # 成績輸入
    r_type = st.radio("本場類型：", ["正賽", "衝刺賽"], horizontal=True)
    cols = st.columns(3)
    inputs = {}
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

        if not err:
            if r_type == "正賽":
                for i, name in enumerate(wdc_order, 1): st.session_state.stats[name]["prev_rank"] = i
                st.session_state.race_no += 1
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                for d, r in processed.items():
                    s = st.session_state.stats[d]
                    s["ranks"].append(r)
                    if r == 'R':
                        s["dnf"] += 1
                        if s["dnf"] % 5 == 0: s["penalty_next"] = True
                    else:
                        if r==1: s["p1"]+=1
                        elif r==2: s["p2"]+=1
                        elif r==3: s["p3"]+=1
                        p = pts_pool[r-1] if r <= 10 and not s["penalty_next"] else 0
                        s["points"] += p
                        s["penalty_next"] = False
                    s["point_history"].append({"race": float(st.session_state.race_no), "pts": s["points"]})
            else:
                sprint_res = {d: 0 for d in st.session_state.stats.keys()}
                for d, r in processed.items():
                    if r != 'R': sprint_res[d] += {1: 5, 2: 3, 3: 1}.get(r, 0)
                # 存入衝刺賽名次紀錄 (存入 ranks 的特殊標記)
                for d, r in processed.items(): st.session_state.stats[d]["ranks"].append(f"S:{r}")
                
                non_top_10 = sorted([(d, r) for d, r in processed.items() if d not in set(wdc_order[:10]) and r != 'R'], key=lambda x: x[1])
                bonus = [8, 7, 6, 5, 4, 3, 2, 1]
                for d, r in non_top_10:
                    if bonus: sprint_res[d] += bonus.pop(0)
                st.session_state.sprint_history.append({"race_after": st.session_state.race_no + 0.5, "results": sprint_res})
                for d, p in sprint_res.items():
                    st.session_state.stats[d]["points"] += p
                    st.session_state.stats[d]["point_history"].append({"race": st.session_state.race_no + 0.5, "pts": st.session_state.stats[d]["points"]})
            
            for t in TEAM_CONFIG.keys():
                t_sum = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                st.session_state.team_history[t].append({"race": float(st.session_state.race_no), "pts": t_sum})
            st.session_state.form_id += 1; st.rerun()

with tabs[1]: # WDC
    wdc_df = []
    for i, n in enumerate(wdc_order, 1):
        s = st.session_state.stats[n]
        avg = round(sum([r if isinstance(r, int) else 25 for r in s["ranks"] if not str(r).startswith("S:")]) / len([r for r in s["ranks"] if not str(r).startswith("S:") or r=="R"]), 2) if s["ranks"] else 0
        wdc_df.append([i, n, s['team'], s['points'], avg, f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf']])
    st.dataframe(pd.DataFrame(wdc_df, columns=["排名","車手","車隊","積分","平均名次","P1/P2/P3","DNF"]), use_container_width=True, hide_index=True)

with tabs[2]: # WCC
    wcc_data = []
    for t in TEAM_CONFIG.keys():
        ds = [s for d, s in st.session_state.stats.items() if s["team"] == t]
        all_r = []
        for s in ds: all_r.extend([r if isinstance(r, int) else 25 for r in s["ranks"] if not str(r).startswith("S:")])
        avg_t = round(sum(all_r)/len(all_r), 2) if all_r else 0
        wcc_data.append({"T": t, "P": sum(s["points"] for s in ds), "A": avg_t, "P123": f"{sum(s['p1'] for s in ds)}/{sum(s['p2'] for s in ds)}/{sum(s['p3'] for s in ds)}"})
    wcc_df = pd.DataFrame(wcc_data).sort_values(by=["P", "A"], ascending=[False, True])
    st.dataframe(wcc_df, use_container_width=True, hide_index=True)

with tabs[3]: # 完賽位置 (含衝刺賽)
    if st.session_state.stats[wdc_order[0]]["ranks"]:
        pos_list = []
        for d in wdc_order:
            s = st.session_state.stats[d]
            row = {"車手": d, "車隊": s['team']}
            rd_cnt = 1
            for r in s["ranks"]:
                if str(r).startswith("S:"):
                    row[f"Rd.{rd_cnt} (S)"] = r.split(":")[1]
                    if row[f"Rd.{rd_cnt} (S)"] != 'R': row[f"Rd.{rd_cnt} (S)"] = int(row[f"Rd.{rd_cnt} (S)"])
                else:
                    row[f"Rd.{rd_cnt}"] = 25 if r == 'R' else r
                    rd_cnt += 1
            pos_list.append(row)
        df_pos = pd.DataFrame(pos_list)
        st.dataframe(df_pos.style.applymap(style_ranks, subset=[c for c in df_pos.columns if "Rd." in c]), use_container_width=True, hide_index=True)

with tabs[4]: # 圖表
    dh = [{"Race": pt["race"], "Driver": d, "Points": pt["pts"]} for d, s in st.session_state.stats.items() for pt in s['point_history']]
    st.plotly_chart(px.line(pd.DataFrame(dh), x="Race", y="Points", color="Driver", markers=True, template="plotly_dark", color_discrete_map={d: TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()}), use_container_width=True)

st.divider()
st.code(json.dumps({"race_no": st.session_state.race_no, "sprints": st.session_state.sprint_history, "data": {d: [r for r in s["ranks"] if not str(r).startswith("S:")] for d, s in st.session_state.stats.items()}}))
