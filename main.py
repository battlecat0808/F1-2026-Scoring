import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Pro", page_icon="🏎️", layout="wide")

# --- 基礎設定 ---
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

# --- 初始化狀態 ---
if "stats" not in st.session_state:
    st.session_state.stats = {d: {"no": c, "team": t, "points": 0, "ranks": [], "point_history": [0], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False, "prev_rank": 0} 
                             for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
    st.session_state.team_history = {t: [0] for t in TEAM_CONFIG.keys()}
    st.session_state.race_no = 0

# --- 側邊欄存檔管理 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("在此貼上存檔代碼：", height=120)
    if st.button("載入存檔"):
        try:
            data = json.loads(backup_input)
            st.session_state.stats = data["stats"]
            st.session_state.race_no = data["race_no"]
            st.session_state.team_history = data["team_history"]
            st.success("讀取成功！")
            st.rerun()
        except: st.error("代碼格式不正確，請確認後再貼上。")
    if st.button("🚨 重置全賽季"):
        st.session_state.clear()
        st.rerun()

# --- 主程式介面 ---
st.title(f"🏎️ 2026 F1 賽季系統 (第 {st.session_state.race_no} 場正式賽)")
tab_input, tab_wdc, tab_wcc, tab_chart = st.tabs(["🏁 輸入成績", "👤 車手榜", "🏎️ 車隊榜", "📈 數據圖表"])

with tab_input:
    r_type = st.radio("選擇比賽類型：", ["正賽", "衝刺賽"], horizontal=True)
    st.caption("※ 衝刺賽不計入 DNF 與平均排名，不增加場次數字。")
    
    # 計算 Top 10 (基於目前總積分)
    current_wdc = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1']), reverse=True)
    top_10 = set(current_wdc[:10])

    with st.form("race_form"):
        cols = st.columns(3)
        inputs = {d: st.text_input(f"#{s['no']} {d}", key=f"inp_{d}", placeholder="1-22 / R") for d, s in st.session_state.stats.items()}
        submitted = st.form_submit_button("提交成績")
        
        if submitted:
            processed, used, err = {}, set(), False
            for d, r in inputs.items():
                v = r.strip().upper()
                if v == 'R': processed[d] = 'DNF'
                else:
                    try:
                        n = int(v)
                        if 1 <= n <= 22 and n not in used: processed[d] = n; used.add(n)
                        else: err = True
                    except: err = True
            
            if err or len(processed) < 22:
                st.error("輸入錯誤：排名重複、超出範圍或漏填。")
            else:
                if r_type == "正賽":
                    # 紀錄升降前排名
                    wdc_now = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1']), reverse=True)
                    for idx, name in enumerate(wdc_now, 1): st.session_state.stats[name]["prev_rank"] = idx
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
                            p += {1:5, 2:3, 3:1}.get(r, 0)
                            if d not in top_10: p += {1:8, 2:7, 3:6, 4:5, 5:4, 6:3, 7:2, 8:1}.get(r, 0)
                        s["points"] += p
                        s["point_history"][-1] = s["points"] # 更新最近一個歷史點

                # 更新車隊歷史
                for t in TEAM_CONFIG.keys():
                    t_sum = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                    if r_type == "正賽": st.session_state.team_history[t].append(t_sum)
                    else: st.session_state.team_history[t][-1] = t_sum
                st.success(f"{r_type}成績已存檔！")
                st.rerun()

with tab_wdc:
    st.subheader("👤 車手年度積分榜 (WDC)")
    d_sort = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1'], x[1]['p2'], x[1]['p3'], -sum(x[1]['ranks'])/len(x[1]['ranks']) if x[1]['ranks'] else 0), reverse=True)
    d_rows = []
    for i, (n, s) in enumerate(d_sort, 1):
        ch = ""
        if st.session_state.race_no > 1:
            diff = s["prev_rank"] - i
            ch = f"🔼 {diff}" if diff > 0 else f"🔽 {abs(diff)}" if diff < 0 else "➖"
        avg = sum(s['ranks'])/len(s['ranks']) if s['ranks'] else 0
        d_rows.append([ch, i, s['no'], n, s['team'], s['points'], f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf'], f"{avg:.3f}"])
    st.dataframe(pd.DataFrame(d_rows, columns=["趨勢","排名","#","車手","車隊","積分","P1/2/3","DNF","Avg"]), use_container_width=True, hide_index=True)

with tab_wcc:
    st.subheader("🏎️ 車隊年度積分榜 (WCC)")
    t_rows = []
    for t in TEAM_CONFIG.keys():
        ds = [s for d, s in st.session_state.stats.items() if s["team"] == t]
        all_r = [r for d in ds for r in d["ranks"]]
        t_avg = sum(all_r)/len(all_r) if all_r else 0
        t_rows.append([t, sum(d["points"] for d in ds), sum(d["p1"] for d in ds), sum(d["p2"] for d in ds), sum(d["p3"] for d in ds), f"{t_avg:.3f}"])
    t_sort = sorted(t_rows, key=lambda x: (x[1], x[2]), reverse=True)
    st.dataframe(pd.DataFrame([[i+1]+r for i, r in enumerate(t_sort)], columns=["排名","車隊","總分","P1","P2","P3","平均完賽"]), use_container_width=True, hide_index=True)

with tab_chart:
    if st.session_state.race_no > 0:
        st.subheader("👤 車手積分趨勢圖")
        dh_list = [{"Race": i, "Driver": f"#{s['no']} {d}", "Points": p, "Team": s['team']} for d, s in st.session_state.stats.items() for i, p in enumerate(s['point_history'])]
        d_colors = {f"#{s['no']} {d}": TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()}
        st.plotly_chart(px.line(pd.DataFrame(dh_list), x="Race", y="Points", color="Driver", markers=True, color_discrete_map=d_colors, template="plotly_dark", height=500), use_container_width=True)
        
        st.divider()
        
        st.subheader("🏎️ 車隊積分趨勢圖")
        th_list = [{"Race": i, "Team": t, "Points": p} for t, h in st.session_state.team_history.items() for i, p in enumerate(h)]
        t_colors = {t: cfg["color"] for t, cfg in TEAM_CONFIG.items()}
        st.plotly_chart(px.line(pd.DataFrame(th_list), x="Race", y="Points", color="Team", markers=True, color_discrete_map=t_colors, template="plotly_dark", height=500), use_container_width=True)
    else: st.info("尚無數據，請先輸入第一場正賽成績。")

st.divider()
st.write("🔑 **存檔代碼 (請妥善保存)：**")
st.code(json.dumps({"stats": st.session_state.stats, "race_no": st.session_state.race_no, "team_history": st.session_state.team_history}))
