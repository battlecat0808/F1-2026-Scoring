import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Ultimate", page_icon="🏎️", layout="wide")

# --- 設定與初始化 ---
TEAM_CONFIG = {
    "McLaren": {"color": "#FF8700", "drivers": {"Lando Norris": "4", "Oscar Piastri": "81"}},
    "Ferrari": {"color": "#E80020", "drivers": {"Lewis Hamilton": "44", "Charles Leclerc": "16"}},
    "Red Bull": {"color": "#3671C6", "drivers": {"Max Verstappen": "1", "Isack Hadjar": "66"}},
    "Mercedes": {"color": "#27F4D2", "drivers": {"George Russell": "63", "Kimi Antonelli": "12"}},
    "Aston Martin": {"color": "#229971", "drivers": {"Fernando Alonso": "14", "Lance Stroll": "18"}},
    "Audi": {"color": "#F50A20", "drivers": {"Nico Hulkenberg": "27", "Gabriel Bortoleto": "5"}},
    "Williams": {"color": "#64C4FF", "drivers": {"Carlos Sainz": "55", "Alex Albon": "23"}},
    "Alpine": {"color": "#0093CC", "drivers": {"Pierre Gasly": "10", "Franco Colapinto": "43"}},
    "Racing Bulls": {"color": "#6692FF", "drivers": {"Liam Lawson": "30", "Arvid Lindblad": "17"}},
    "Haas": {"color": "#B6BABD", "drivers": {"Esteban Ocon": "31", "Oliver Bearman": "87"}},
    "APX-CTWR": {"color": "#000000", "drivers": {"Yuki Tsunoda": "22", "Ethan Tan": "09"}}
}

if "stats" not in st.session_state:
    st.session_state.stats = {d: {"no": c, "team": t, "points": 0, "ranks": [], "point_history": [0], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False, "prev_rank": 0} 
                             for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
    st.session_state.team_history = {t: [0] for t in TEAM_CONFIG.keys()}
    st.session_state.race_no = 0

# --- 側邊欄 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("在此貼上存檔代碼：", height=100)
    if st.button("載入存檔"):
        try:
            data = json.loads(backup_input)
            st.session_state.stats = data["stats"]
            st.session_state.race_no = data["race_no"]
            st.session_state.team_history = data.get("team_history", {t: [0] for t in TEAM_CONFIG.keys()})
            st.success("讀取成功！"); st.rerun()
        except: st.error("格式錯誤")
    if st.button("🚨 重置全賽季"):
        st.session_state.clear(); st.rerun()

# --- 主程式 ---
st.title(f"🏎️ 2026 F1 賽季 - 第 {st.session_state.race_no} 場正式比賽結束")
tabs = st.tabs(["🏁 成績輸入", "👤 車手榜 (WDC)", "🏎️ 車隊榜 (WCC)", "📈 積分曲線"])

with tabs[0]:
    r_type = st.radio("本場類型：", ["正賽", "衝刺賽"], horizontal=True)
    st.info("💡 提示：衝刺賽不計入平均排名與 DNF 次數，且不會增加正式比賽場次數字。")
    
    # 計算 Top 10 (用於衝刺賽 11名後加分判定)
    top_10 = set(sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1']), reverse=True)[:10])

    with st.form("race_form"):
        cols = st.columns(3)
        inputs = {d: st.text_input(f"#{s['no']} {d}", key=f"f_{d}_{st.session_state.race_no}_{r_type}", placeholder="1-22 / R") for d, s in st.session_state.stats.items()}
        if st.form_submit_button("確認提交成績"):
            processed, used, err = {}, set(), False
            for d, r in inputs.items():
                v = r.strip().upper()
                if v == 'R': processed[d] = 'DNF'
                else:
                    try:
                        n = int(v); (processed.__setitem__(d, n), used.add(n)) if 1 <= n <= 22 and n not in used else setattr(st, 'err', True)
                    except: err = True
            
            if err or len(processed) < 22: st.error("排名錯誤或有漏填！")
            else:
                if r_type == "正賽":
                    # 紀錄升降前排名
                    current_order = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1']), reverse=True)
                    for idx, d_name in enumerate(current_order, 1): st.session_state.stats[d_name]["prev_rank"] = idx
                    st.session_state.race_no += 1

                sorted_res = sorted(processed.items(), key=lambda x: 99 if x[1]=='DNF' else x[1])
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                
                for d, r in sorted_res:
                    s = st.session_state.stats[d]
                    p = 0
                    if r_type == "正賽":
                        if r == 'DNF':
                            s["ranks"].append(25); s["dnf"] += 1; p = 0
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
                        s["point_history"].append(s["points"])
                    else: # 衝刺賽
                        if r != 'DNF':
                            # 1. Top 10 的 5-3-1 分
                            p += {1:5, 2:3, 3:1}.get(r, 0)
                            # 2. 非 Top 10 的 8-7-6...1 分
                            if d not in top_10:
                                p += {1:8, 2:7, 3:6, 4:5, 5:4, 6:3, 7:2, 8:1}.get(r, 0)
                        s["points"] += p
                        s["point_history"][-1] = s["points"] # 衝刺賽直接更新當前比賽最後一個點
                
                # 更新車隊歷史
                for t in TEAM_CONFIG.keys():
                    t_sum = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                    if r_type == "正賽": st.session_state.team_history[t].append(t_sum)
                    else: st.session_state.team_history[t][-1] = t_sum
                
                st.rerun()

with tabs[1]:
    d_sort = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1'], x[1]['p2'], x[1]['p3'], -sum(x[1]['ranks'])/len(x[1]['ranks']) if x[1]['ranks'] else 0), reverse=True)
    driver_data = [[("" if st.session_state.race_no <= 1 else ("🔼 "+str(s["prev_rank"]-i) if s["prev_rank"]-i>0 else "🔽 "+str(abs(s["prev_rank"]-i)) if s["prev_rank"]-i<0 else "➖")), i, s['no'], n, s['team'], s['points'], f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf'], f"{sum(s['ranks'])/len(s['ranks']):.3f}" if s['ranks'] else "-"] for i, (n, s) in enumerate(d_sort, 1)]
    st.dataframe(pd.DataFrame(driver_data, columns=["趨勢", "排名", "車號", "車手", "車隊", "積分", "P1/2/3", "DNF", "Avg"]), use_container_width=True, hide_index=True)

with tabs[2]:
    t_data = []
    for t in TEAM_CONFIG.keys():
        t_drivers = [s for d, s in st.session_state.stats.items() if s["team"] == t]
        t_pts = sum(d["points"] for d in t_drivers)
        t_p1 = sum(d["p1"] for d in t_drivers)
        t_p2 = sum(d["p2"] for d in t_drivers)
        t_p3 = sum(d["p3"] for d in t_drivers)
        all_ranks = [r for d in t_drivers for r in d["ranks"]]
        t_avg = sum(all_ranks)/len(all_ranks) if all_ranks else 0
        t_data.append([t, t_pts, f"{t_p1}/{t_p2}/{t_p3}", f"{t_avg:.3f}"])
    t_sort = sorted(t_data, key=lambda x: (x[1], x[2]), reverse=True)
    st.dataframe(pd.DataFrame([[i+1]+row for i, row in enumerate(t_sort)], columns=["排名", "車隊", "總分", "P1/2/3", "車隊平均排名"]), use_container_width=True, hide_index=True)

with tabs[3]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("車手積分走勢")
        h_data = [{"Race": i, "Driver": f"#{s['no']} {d}", "Points": p} for d, s in st.session_state.stats.items() for i, p in enumerate(s['point_history'])]
        color_map = {f"#{s['no']} {d}": TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()}
        st.plotly_chart(px.line(pd.DataFrame(h_data), x="Race", y="Points", color="Driver", markers=True, color_discrete_map=color_map, template="plotly_dark"), use_container_width=True)
    with c2:
        st.subheader("車隊積分走勢")
        th_data = [{"Race": i, "Team": t, "Points": p} for t, history in st.session_state.session_state.team_history.items() for i, p in enumerate(history)] if "team_history" in st.session_state else []
        # 修正: 這裡直接從 session_state 抓
        th_list = []
        for t, h in st.session_state.team_history.items():
            for i, p in enumerate(h): th_list.append({"Race": i, "Team": t, "Points": p})
        t_colors = {t: cfg["color"] for t, cfg in TEAM_CONFIG.items()}
        st.plotly_chart(px.line(pd.DataFrame(th_list), x="Race", y="Points", color="Team", markers=True, color_discrete_map=t_colors, template="plotly_dark"), use_container_width=True)

st.divider()
st.code(json.dumps({"stats": st.session_state.stats, "race_no": st.session_state.race_no, "team_history": st.session_state.team_history}))
