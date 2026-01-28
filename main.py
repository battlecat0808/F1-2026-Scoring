import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Ultimate", page_icon="🏎️", layout="wide")

# --- 核心設定 ---
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

# --- 初始化 ---
if "stats" not in st.session_state:
    st.session_state.stats = {d: {"no": c, "team": t, "points": 0, "ranks": [], "point_history": [{"race": 0, "pts": 0}], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False, "prev_rank": 0} 
                             for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
    st.session_state.team_history = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
    st.session_state.team_prev_rank = {t: 0 for t in TEAM_CONFIG.keys()}
    st.session_state.race_no = 0

# --- 側邊欄 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("在此貼上存檔代碼：", height=120)
    if st.button("載入存檔"):
        try:
            data = json.loads(backup_input)
            st.session_state.stats = data["stats"]
            st.session_state.race_no = data["race_no"]
            st.session_state.team_history = data["team_history"]
            st.session_state.team_prev_rank = data.get("team_prev_rank", {t: 0 for t in TEAM_CONFIG.keys()})
            st.success("讀取成功！"); st.rerun()
        except: st.error("存檔格式錯誤")
    if st.button("🚨 重置全賽季"):
        st.session_state.clear(); st.rerun()

# --- 主程式 ---
st.title(f"🏎️ 2026 F1 賽季 (正式賽：{st.session_state.race_no})")
tab_input, tab_wdc, tab_wcc, tab_chart = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📈 數據圖表"])

with tab_input:
    r_type = st.radio("本場類型：", ["正賽", "衝刺賽"], horizontal=True)
    
    # 決定誰是目前的總排 Top 10
    wdc_order = sorted(st.session_state.stats.keys(), 
                       key=lambda x: (st.session_state.stats[x]['points'], 
                                      st.session_state.stats[x]['p1'], 
                                      st.session_state.stats[x]['p2'], 
                                      st.session_state.stats[x]['p3']), reverse=True)
    top_10_names = set(wdc_order[:10])

    # 這裡移除 clear_on_submit，手動控制清空時機
    with st.form("race_form"):
        st.info("💡 提示：輸入完按 Tab 或 Enter 可跳轉下一格。輸入錯誤時數據會保留。")
        
        # 為了順暢的 Enter/Tab 跳轉，我們按照車隊順序排列輸入框
        inputs = {}
        cols = st.columns(2)
        idx = 0
        for team, cfg in TEAM_CONFIG.items():
            with cols[idx % 2]:
                st.markdown(f"**{team}**")
                for driver in cfg["drivers"]:
                    s = st.session_state.stats[driver]
                    inputs[driver] = st.text_input(f"#{s['no']} {driver}", key=f"f_{driver}", placeholder="1-22 / R")
            idx += 1
            
        submitted = st.form_submit_button("🏁 提交本場成績")
        
        if submitted:
            processed, used_ranks, err = {}, set(), False
            err_msg = ""
            
            for d, r in inputs.items():
                v = r.strip().upper()
                if v == 'R': 
                    processed[d] = 'DNF'
                elif v == '':
                    err = True; err_msg = "有車手漏填成績！"
                else:
                    try:
                        n = int(v)
                        if 1 <= n <= 22:
                            if n not in used_ranks:
                                processed[d] = n
                                used_ranks.add(n)
                            else:
                                err = True; err_msg = f"排名 {n} 重複出現了！"
                        else:
                            err = True; err_msg = f"排名 {n} 超出範圍 (1-22)！"
                    except:
                        err = True; err_msg = f"'{v}' 不是有效的輸入 (請輸入數字或 R)！"
            
            if err:
                st.error(f"🚫 {err_msg}")
            elif len(processed) < 22:
                st.error("🚫 還有車手沒填寫到排名喔！")
            else:
                # 只有在這裡（完全正確）才會執行更新與跳轉，達成「成功才清空」
                if r_type == "正賽":
                    for i, name in enumerate(wdc_order, 1): st.session_state.stats[name]["prev_rank"] = i
                    t_now = sorted(TEAM_CONFIG.keys(), key=lambda x: sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), reverse=True)
                    for i, t_name in enumerate(t_now, 1): st.session_state.team_prev_rank[t_name] = i
                    st.session_state.race_no += 1
                
                curr_mark = st.session_state.race_no if r_type == "正賽" else st.session_state.race_no + 0.5
                sorted_res = sorted(processed.items(), key=lambda x: 99 if x[1]=='DNF' else x[1])

                if r_type == "正賽":
                    pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                    for d, r in sorted_res:
                        s = st.session_state.stats[d]
                        p = 0
                        if r == 'DNF':
                            s["ranks"].append(25); s["dnf"] += 1
                            if s["dnf"] % 5 == 0: s["penalty_next"] = True
                        else:
                            s["ranks"].append(r)
                            if r==1: s["p1"]+=1
                            elif r==2: s["p2"]+=1
                            elif r==3: s["p3"]+=1
                            if pts_pool and r <= 10:
                                if s["penalty_next"]: s["penalty_next"] = False
                                else: p = pts_pool.pop(0)
                        s["points"] += p
                        s["point_history"].append({"race": curr_mark, "pts": s["points"]})
                else: # 衝刺賽
                    sprint_points = {d: 0 for d in st.session_state.stats.keys()}
                    for d, r in sorted_res:
                        if r != 'DNF': sprint_points[d] += {1: 5, 2: 3, 3: 1}.get(r, 0)
                    non_top_10 = [(d, r) for d, r in sorted_res if d not in top_10_names and r != 'DNF']
                    non_top_10.sort(key=lambda x: x[1])
                    bonus_pool = [8, 7, 6, 5, 4, 3, 2, 1]
                    for d, r in non_top_10:
                        if bonus_pool: sprint_points[d] += bonus_pool.pop(0)
                    for d, p in sprint_points.items():
                        st.session_state.stats[d]["points"] += p
                        st.session_state.stats[d]["point_history"].append({"race": curr_mark, "pts": st.session_state.stats[d]["points"]})

                for t in TEAM_CONFIG.keys():
                    t_sum = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                    st.session_state.team_history[t].append({"race": curr_mark, "pts": t_sum})
                
                st.success("✅ 成績錄入成功！")
                st.rerun()

# --- 榜單與圖表邏輯保持不變 ---
with tab_wdc:
    d_sort = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1'], x[1]['p2'], x[1]['p3'], -sum(x[1]['ranks'])/len(x[1]['ranks']) if x[1]['ranks'] else 0), reverse=True)
    d_data = [[(f"🔼 {s['prev_rank']-i}" if s['prev_rank']-i>0 else f"🔽 {abs(s['prev_rank']-i)}" if s['prev_rank']-i<0 else "➖" if st.session_state.race_no >= 1 and s['prev_rank'] != 0 else ""), i, s['no'], n, s['team'], s['points'], f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf'], f"{sum(s['ranks'])/len(s['ranks']):.3f}" if s['ranks'] else "-"] for i, (n, s) in enumerate(d_sort, 1)]
    st.dataframe(pd.DataFrame(d_data, columns=["趨勢","排名","#","車手","車隊","積分","P1/P2/P3","DNF","Avg"]), use_container_width=True, hide_index=True)

with tab_wcc:
    t_list = []
    for t in TEAM_CONFIG.keys():
        ds = [s for d, s in st.session_state.stats.items() if s["team"] == t]
        all_r = [r for d in ds for r in d["ranks"]]
        t_list.append({"team": t, "pts": sum(d["points"] for d in ds), "p1": sum(d["p1"] for d in ds), "p2": sum(d["p2"] for d in ds), "p3": sum(d["p3"] for d in ds), "avg": sum(all_r)/len(all_r) if all_r else 0})
    t_sort = sorted(t_list, key=lambda x: (x["pts"], x["p1"], x["p2"], x["p3"]), reverse=True)
    t_rows = [[(f"🔼 {st.session_state.team_prev_rank[t['team']]-i}" if st.session_state.team_prev_rank[t['team']]-i>0 else f"🔽 {abs(st.session_state.team_prev_rank[t['team']]-i)}" if st.session_state.team_prev_rank[t['team']]-i<0 else "➖" if st.session_state.race_no >= 1 and st.session_state.team_prev_rank[t['team']] != 0 else ""), i, t["team"], t["pts"], f"{t['p1']}/{t['p2']}/{t['p3']}", f"{t['avg']:.3f}"] for i, t in enumerate(t_sort, 1)]
    st.dataframe(pd.DataFrame(t_rows, columns=["趨勢","排名","車隊","總積分","P1/P2/P3","Avg"]), use_container_width=True, hide_index=True)

with tab_chart:
    if any(len(s['point_history']) > 1 for s in st.session_state.stats.values()):
        dh = [{"Race": pt["race"], "Driver": f"#{s['no']} {d}", "Points": pt["pts"]} for d, s in st.session_state.stats.items() for pt in s['point_history']]
        st.plotly_chart(px.line(pd.DataFrame(dh), x="Race", y="Points", color="Driver", markers=True, color_discrete_map={f"#{s['no']} {d}": TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()}, template="plotly_dark", height=500, title="車手積分趨勢"), use_container_width=True)
        th = [{"Race": pt["race"], "Team": t, "Points": pt["pts"]} for t, h in st.session_state.team_history.items() for pt in h]
        st.plotly_chart(px.line(pd.DataFrame(th), x="Race", y="Points", color="Team", markers=True, color_discrete_map={t: cfg["color"] for t, cfg in TEAM_CONFIG.items()}, template="plotly_dark", height=500, title="車隊積分趨勢"), use_container_width=True)

st.divider()
st.code(json.dumps({"stats": st.session_state.stats, "race_no": st.session_state.race_no, "team_history": st.session_state.team_history, "team_prev_rank": st.session_state.team_prev_rank}))
