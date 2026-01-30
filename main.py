import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Ultimate: Pro Edition", page_icon="🏎️", layout="wide")

# --- 1. 核心配置與完賽矩陣 ---
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

def calculate_rating_change(rank, car_lv):
    """計算完賽矩陣加扣分"""
    if rank == 'R': return -1.0
    
    # 根據車輛評級選擇矩陣列
    if car_lv >= 10:
        matrix = {(1,3): 0.5, (4,6): 0, (7,10): 0, (11,12): -0.2, (13,16): -0.4, (17,18): -0.6, (19,20): -0.6, (21,22): -0.8}
    elif car_lv == 9:
        matrix = {(1,3): 0.9, (4,6): 0.2, (7,10): 0, (11,12): 0, (13,16): 0, (17,18): 0, (19,20): -0.2, (21,22): -0.4}
    else: # 8級及以下
        matrix = {(1,3): 1.3, (4,6): 0.6, (7,10): 0.4, (11,12): 0.2, (13,16): 0, (17,18): 0, (19,20): 0, (21,22): -0.2}
    
    for (low, high), val in matrix.items():
        if low <= rank <= high: return val
    return 0

# --- 2. 初始化 Session State ---
if "stats" not in st.session_state:
    st.session_state.stats = {
        d: {
            "no": c, "team": t, "points": 0, "ranks": [], 
            "point_history": [{"race": 0, "pts": 0}], 
            "rating_history": [{"race": 0, "val": 85.0}], # 預設起始評分
            "p1": 0, "p2": 0, "p3": 0, "dnf": 0, 
            "penalty_next": False, "prev_rank": 0, "rating": 85.0
        } for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()
    }
    st.session_state.team_lv = {t: 9 for t in TEAM_CONFIG.keys()}
    st.session_state.team_history = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
    st.session_state.team_prev_rank = {t: 0 for t in TEAM_CONFIG.keys()}
    st.session_state.race_no = 0
    st.session_state.form_id = 0

# --- 3. 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 賽季管理")
    with st.expander("🏎️ 車輛評級 (1-10)"):
        for t in TEAM_CONFIG.keys():
            st.session_state.team_lv[t] = st.number_input(f"{t}", 1, 10, st.session_state.team_lv[t], key=f"lv_{t}")
            
    with st.expander("👤 車手初始能力值"):
        for d in st.session_state.stats.keys():
            st.session_state.stats[d]["rating"] = st.number_input(f"{d}", 0.0, 100.0, st.session_state.stats[d]["rating"], step=0.5, key=f"init_{d}")

    st.divider()
    backup_input = st.text_area("💾 存檔/讀取 JSON：", height=100)
    if st.button("載入數據"):
        try:
            data = json.loads(backup_input)
            st.session_state.update(data)
            st.success("讀取成功！"); st.rerun()
        except: st.error("格式錯誤")
    if st.button("🚨 重置全賽季"):
        st.session_state.clear(); st.rerun()

# --- 4. 主程式分頁 ---
st.title(f"🏎️ 2026 F1 賽季 (第 {st.session_state.race_no+1} 週)")
tab_input, tab_wdc, tab_wcc, tab_pos, tab_rating = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置", "📈 能力值追蹤"])

with tab_input:
    r_type = st.radio("賽事類型：", ["正賽", "衝刺賽"], horizontal=True)
    wdc_order = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1'], st.session_state.stats[x]['p2'], st.session_state.stats[x]['p3']), reverse=True)
    top_10_names = set(wdc_order[:10])

    inputs = {}
    cols = st.columns(2)
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 2]:
            st.markdown(f"**{team}** (Lv.{st.session_state.team_lv[team]})")
            for driver, no in cfg["drivers"].items():
                inputs[driver] = st.text_input(f"#{no} {driver} (Rating: {st.session_state.stats[driver]['rating']:.1f})", key=f"in_{driver}_{st.session_state.form_id}")

    if st.button("🚀 提交成績並更新數據", use_container_width=True, type="primary"):
        processed, used_ranks, err = {}, set(), False
        for d, r in inputs.items():
            v = r.strip().upper()
            if v == 'R': processed[d] = 'R'
            elif not v: err = True
            else:
                try:
                    n = int(v)
                    if 1 <= n <= 22 and n not in used_ranks:
                        processed[d] = n; used_ranks.add(n)
                    else: err = True
                except: err = True

        if err:
            st.error("❌ 輸入錯誤：請確認名次是否重複或有漏填。")
        else:
            # 更新排名趨勢
            if r_type == "正賽":
                for i, name in enumerate(wdc_order, 1): st.session_state.stats[name]["prev_rank"] = i
                t_now = sorted(TEAM_CONFIG.keys(), key=lambda x: sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), reverse=True)
                for i, t_name in enumerate(t_now, 1): st.session_state.team_prev_rank[t_name] = i
                st.session_state.race_no += 1

            curr_mark = st.session_state.race_no if r_type == "正賽" else st.session_state.race_no + 0.5
            
            # 處理積分邏輯
            if r_type == "正賽":
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                sorted_results = sorted(processed.items(), key=lambda x: 99 if x[1]=='R' else x[1])
                for d, r in sorted_results:
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
                        if pts_pool and r <= 10:
                            if s["penalty_next"]: s["penalty_next"] = False
                            else: p = pts_pool.pop(0)
                    s["points"] += p
                    s["point_history"].append({"race": curr_mark, "pts": s["points"]})

                # --- 動態評分計算系統 ---
                for team, cfg in TEAM_CONFIG.items():
                    drivers = list(cfg["drivers"].keys())
                    d1, d2 = drivers[0], drivers[1]
                    r1, r2 = processed[d1], processed[d2]
                    lv = st.session_state.team_lv[team]

                    # 1. 隊友對決：領先3名+0.1，落後3名-0.1 (皆非DNF才計算)
                    if r1 != 'R' and r2 != 'R':
                        diff = r2 - r1
                        shift = (diff // 3) * 0.1
                        st.session_state.stats[d1]["rating"] += shift
                        st.session_state.stats[d2]["rating"] -= shift
                    
                    # 2. 完賽矩陣
                    st.session_state.stats[d1]["rating"] += calculate_rating_change(r1, lv)
                    st.session_state.stats[d2]["rating"] += calculate_rating_change(r2, lv)
                    
                    # 記錄歷史
                    for d_name in drivers:
                        st.session_state.stats[d_name]["rating_history"].append({"race": curr_mark, "val": round(st.session_state.stats[d_name]["rating"], 2)})

            else: # Sprint 邏輯
                sprint_res = sorted(processed.items(), key=lambda x: 99 if x[1]=='R' else x[1])
                sprint_pts = {d: 0 for d in st.session_state.stats.keys()}
                for d, r in sprint_res:
                    if r != 'R': sprint_pts[d] += {1: 5, 2: 3, 3: 1}.get(r, 0)
                non_top_10 = [(d, r) for d, r in sprint_res if d not in top_10_names and r != 'R']
                non_top_10.sort(key=lambda x: x[1])
                bonus = [8, 7, 6, 5, 4, 3, 2, 1]
                for d, r in non_top_10:
                    if bonus: sprint_pts[d] += bonus.pop(0)
                for d, p in sprint_pts.items():
                    st.session_state.stats[d]["points"] += p
                    st.session_state.stats[d]["point_history"].append({"race": curr_mark, "pts": st.session_state.stats[d]["points"]})

            # 更新車隊總積分
            for t in TEAM_CONFIG.keys():
                t_sum = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                st.session_state.team_history[t].append({"race": curr_mark, "pts": t_sum})
            
            st.session_state.form_id += 1
            st.rerun()

# --- 5. 數據顯示區 ---
with tab_wdc:
    d_sort = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1'], x[1]['p2'], x[1]['p3']), reverse=True)
    d_data = []
    for i, (n, s) in enumerate(d_sort, 1):
        trend = f"🔼 {s['prev_rank']-i}" if s['prev_rank']-i > 0 else f"🔽 {abs(s['prev_rank']-i)}" if s['prev_rank']-i < 0 else "➖"
        d_data.append([trend if st.session_state.race_no > 0 else "", i, s['no'], n, s['team'], s['points'], f"{round(s['rating'],1)}", f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf']])
    st.dataframe(pd.DataFrame(d_data, columns=["趨勢","排名","#","車手","車隊","積分","能力值","P1/P2/P3","DNF"]), use_container_width=True, hide_index=True)

with tab_wcc:
    t_list = []
    for t in TEAM_CONFIG.keys():
        ds = [s for d, s in st.session_state.stats.items() if s["team"] == t]
        t_list.append({"team": t, "pts": sum(d["points"] for d in ds), "p1": sum(d["p1"] for d in ds), "p2": sum(d["p2"] for d in ds), "p3": sum(d["p3"] for d in ds)})
    t_sort = sorted(t_list, key=lambda x: (x["pts"], x["p1"], x["p2"], x["p3"]), reverse=True)
    t_rows = []
    for i, t in enumerate(t_sort, 1):
        prev = st.session_state.team_prev_rank[t['team']]
        trend = f"🔼 {prev-i}" if prev-i > 0 else f"🔽 {abs(prev-i)}" if prev-i < 0 else "➖"
        t_rows.append([trend if st.session_state.race_no > 0 else "", i, t["team"], t["pts"], f"Lv.{st.session_state.team_lv[t['team']]}", f"{t['p1']}/{t['p2']}/{t['p3']}"])
    st.dataframe(pd.DataFrame(t_rows, columns=["趨勢","排名","車隊","總積分","車輛等級","P1/P2/P3"]), use_container_width=True, hide_index=True)

with tab_pos:
    if st.session_state.race_no > 0:
        pos_data = []
        for d in sorted(st.session_state.stats.keys(), key=lambda x: st.session_state.stats[x]['points'], reverse=True):
            s = st.session_state.stats[d]
            row = {"車手": d, "車隊": s['team']}
            for i, r in enumerate(s["ranks"], 1): row[f"Rd.{i}"] = r
            pos_data.append(row)
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True, hide_index=True)

with tab_rating:
    if st.session_state.race_no > 0:
        rh = [{"Race": pt["race"], "Driver": d, "Rating": pt["val"]} for d, s in st.session_state.stats.items() for pt in s['rating_history']]
        st.plotly_chart(px.line(pd.DataFrame(rh), x="Race", y="Rating", color="Driver", markers=True, 
                                color_discrete_map={d: TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()},
                                template="plotly_dark", title="車手能力值演化圖"), use_container_width=True)

# 底部導出
st.divider()
st.code(json.dumps({"stats": st.session_state.stats, "team_lv": st.session_state.team_lv, "race_no": st.session_state.race_no, "team_history": st.session_state.team_history, "team_prev_rank": st.session_state.team_prev_rank}))
