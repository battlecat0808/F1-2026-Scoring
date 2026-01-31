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
    st.session_state.form_id = 0

# --- 側邊欄 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("存檔代碼：", height=100)
    if st.button("載入存檔"):
        try:
            data = json.loads(backup_input)
            st.session_state.update(data)
            st.success("讀取成功！"); st.rerun()
        except: st.error("格式錯誤")
    if st.button("🚨 重置全賽季"):
        st.session_state.clear(); st.rerun()

# --- 主程式 ---
st.title(f"🏎️ 2026 F1 賽季 (第{st.session_state.race_no+1}週)")
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
                inputs[driver] = st.text_input(f"#{no} {driver}", key=k, placeholder="1-22 / R")
    
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
                    if 1 <= n <= 22 and n not in used_ranks:
                        processed[d] = n; used_ranks.add(n)
                    else: err = True; err_msg = f"排名 {n} 重複或超出範圍！"
                except: err = True; err_msg = f"'{v}' 格式不對！"

        if err: st.error(f"❌ {err_msg}")
        else:
            if r_type == "正賽":
                for i, name in enumerate(wdc_order, 1): st.session_state.stats[name]["prev_rank"] = i
                t_now = sorted(TEAM_CONFIG.keys(), key=lambda x: sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), reverse=True)
                for i, t_name in enumerate(t_now, 1): st.session_state.team_prev_rank[t_name] = i
                st.session_state.race_no += 1
            
            curr_mark = st.session_state.race_no if r_type == "正賽" else st.session_state.race_no + 0.5
            sorted_res = sorted(processed.items(), key=lambda x: 99 if x[1]=='R' else x[1])

            if r_type == "正賽":
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                for d, r in sorted_res:
                    s = st.session_state.stats[d]
                    p = 0
                    s["ranks"].append(r) # 直接存數字或 'R'
                    if r == 'R':
                        s["dnf"] += 1
                        if s["dnf"] % 5 == 0: s["penalty_next"] = True
                    else:
                        if r==1: s["p1"]+=1
                        elif r==2: s["p2"]+=1
                        elif r==3: s["p3"]+=1
                        if pts_pool and r <= 10:
                            if s["penalty_next"]: s["penalty_next"] = False
                            else: p = pts_pool.pop(0)
                    s["points"] += p
                    s["point_history"].append({"race": curr_mark, "pts": s["points"]})
            else: # Sprint
                sprint_pts = {d: 0 for d in st.session_state.stats.keys()}
                for d, r in sorted_res:
                    if r != 'R': sprint_pts[d] += {1: 5, 2: 3, 3: 1}.get(r, 0)
                non_top_10 = [(d, r) for d, r in sorted_res if d not in top_10_names and r != 'R']
                non_top_10.sort(key=lambda x: x[1])
                bonus = [8, 7, 6, 5, 4, 3, 2, 1]
                for d, r in non_top_10:
                    if bonus: sprint_pts[d] += bonus.pop(0)
                for d, p in sprint_pts.items():
                    st.session_state.stats[d]["points"] += p
                    st.session_state.stats[d]["point_history"].append({"race": curr_mark, "pts": st.session_state.stats[d]["points"]})

            for t in TEAM_CONFIG.keys():
                t_sum = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                st.session_state.team_history[t].append({"race": curr_mark, "pts": t_sum})
            
            st.session_state.form_id += 1
            st.rerun()

# --- 完賽位置表 (含顏色標註) ---
with tab_pos:
    if st.session_state.race_no > 0:
        st.subheader("🏁 每場完賽名次記錄 (R 記為 25)")
        
        # 準備數據
        pos_data = []
        sorted_drivers = sorted(st.session_state.stats.keys(), key=lambda x: st.session_state.stats[x]['points'], reverse=True)
        for d in sorted_drivers:
            s = st.session_state.stats[d]
            # 將 'R' 轉換為 25 進行顯示
            row = {"車手": d, "車隊": s['team']}
            for i, r in enumerate(s["ranks"], 1):
                row[f"Rd.{i}"] = 25 if r == 'R' else r
            pos_data.append(row)
        
        df_pos = pd.DataFrame(pos_data)

        # 定義樣式函數
        def style_ranks(val):
            if isinstance(val, (int, float)):
                if val == 25: return 'background-color: #FF4B4B; color: white; font-weight: bold' # 紅色 (DNF)
                if val == 1: return 'background-color: #FFD700; color: black; font-weight: bold'  # 金色
                if val == 2: return 'background-color: #C0C0C0; color: black; font-weight: bold'  # 銀色
                if val == 3: return 'background-color: #CD7F32; color: white; font-weight: bold'  # 銅色
                if 4 <= val <= 10: return 'background-color: #28a745; color: white'             # 綠色
                if 11 <= val <= 24: return 'background-color: #ffc107; color: black'            # 黃色
            return ''

        # 套用樣式並顯示
        # 我們排除 "車手" 與 "車隊" 欄位，只對 Rd. 欄位進行染色
        rd_cols = [c for c in df_pos.columns if c.startswith("Rd.")]
        styled_df = df_pos.style.applymap(style_ranks, subset=rd_cols)
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.info("尚無正賽數據。")

# --- 榜單與圖表 (同前) ---
# --- 榜單與圖表 ---
with tab_wdc:
    def get_avg_pos_with_dnf(ranks):
        if not ranks: return "N/A"
        # 將 'R' 轉換為 25，其餘保持原數字
        processed_ranks = [r if isinstance(r, int) else 25 for r in ranks]
        return round(sum(processed_ranks) / len(processed_ranks), 2)

    d_sort = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1'], x[1]['p2'], x[1]['p3']), reverse=True)
    
    d_data = []
    for i, (n, s) in enumerate(d_sort, 1):
        # 趨勢計算
        trend = ""
        if st.session_state.race_no >= 1 and s['prev_rank'] != 0:
            diff = s['prev_rank'] - i
            if diff > 0: trend = f"🔼 {diff}"
            elif diff < 0: trend = f"🔽 {abs(diff)}"
            else: trend = "➖"
        
        avg_p = get_avg_pos_with_dnf(s["ranks"])
        
        d_data.append([
            trend, i, s['no'], n, s['team'], s['points'], 
            avg_p, f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf']
        ])
    
    st.dataframe(
        pd.DataFrame(d_data, columns=["趨勢","排名","#","車手","車隊","積分","平均名次","P1/P2/P3","DNF"]), 
        use_container_width=True, hide_index=True
    )

with tab_wcc:
    t_list = []
    for t in TEAM_CONFIG.keys():
        ds = [s for d, s in st.session_state.stats.items() if s["team"] == t]
        
        # 收集該車隊所有車手的名次紀錄，'R' 視為 25
        all_team_ranks = []
        for d_stat in ds:
            all_team_ranks.extend([r if isinstance(r, int) else 25 for r in d_stat["ranks"]])
        
        avg_t_pos = round(sum(all_team_ranks) / len(all_team_ranks), 2) if all_team_ranks else "N/A"
        
        t_list.append({
            "team": t, 
            "pts": sum(d["points"] for d in ds), 
            "p1": sum(d["p1"] for d in ds), 
            "p2": sum(d["p2"] for d in ds), 
            "p3": sum(d["p3"] for d in ds),
            "avg_pos": avg_t_pos
        })
    
    t_sort = sorted(t_list, key=lambda x: (x["pts"], x["p1"], x["p2"], x["p3"]), reverse=True)
    
    t_rows = []
    for i, t in enumerate(t_sort, 1):
        trend = ""
        prev = st.session_state.team_prev_rank.get(t['team'], 0)
        if st.session_state.race_no >= 1 and prev != 0:
            diff = prev - i
            if diff > 0: trend = f"🔼 {diff}"
            elif diff < 0: trend = f"🔽 {abs(diff)}"
            else: trend = "➖"
            
        t_rows.append([trend, i, t["team"], t["pts"], t["avg_pos"], f"{t['p1']}/{t['p2']}/{t['p3']}"])
    
    st.dataframe(
        pd.DataFrame(t_rows, columns=["趨勢","排名","車隊","總積分","平均名次","P1/P2/P3"]), 
        use_container_width=True, hide_index=True
    )

with tab_chart:
    if st.session_state.race_no > 0:
        dh = [{"Race": pt["race"], "Driver": f"#{s['no']} {d}", "Points": pt["pts"]} for d, s in st.session_state.stats.items() for pt in s['point_history']]
        st.plotly_chart(px.line(pd.DataFrame(dh), x="Race", y="Points", color="Driver", markers=True, color_discrete_map={f"#{s['no']} {d}": TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()}, template="plotly_dark", title="車手積分趨勢"), use_container_width=True)
        th = [{"Race": pt["race"], "Team": t, "Points": pt["pts"]} for t, h in st.session_state.team_history.items() for pt in h]
        st.plotly_chart(px.line(pd.DataFrame(th), x="Race", y="Points", color="Team", markers=True, color_discrete_map={t: cfg["color"] for t, cfg in TEAM_CONFIG.items()}, template="plotly_dark", title="車隊積分趨勢"), use_container_width=True)

st.divider()
st.code(json.dumps({"stats": st.session_state.stats, "race_no": st.session_state.race_no, "team_history": st.session_state.team_history, "team_prev_rank": st.session_state.team_prev_rank}))
