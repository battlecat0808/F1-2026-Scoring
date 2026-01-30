import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Ultimate: Dynamic Edition", page_icon="🏎️", layout="wide")

# --- 1. 核心配置與規則 ---
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

def get_matrix_change(rank, car_lv):
    if rank == 'R': return -1.0
    if car_lv >= 10:
        matrix = {(1,3): 0.5, (4,6): 0, (7,10): 0, (11,12): -0.2, (13,16): -0.4, (17,18): -0.6, (19,20): -0.6, (21,22): -0.8}
    elif car_lv == 9:
        matrix = {(1,3): 0.9, (4,6): 0.2, (7,10): 0, (11,12): 0, (13,16): 0, (17,18): 0, (19,20): -0.2, (21,22): -0.4}
    else:
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
            "rating": 10, # 預設值，之後會被輸入覆蓋
            "rating_history": [{"race": 0, "val": 10}],
            "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "prev_rank": 0, "penalty_next": False
        } for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()
    }
    st.session_state.team_lv = {t: 9 for t in TEAM_CONFIG.keys()}
    st.session_state.team_history = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
    st.session_state.team_prev_rank = {t: 0 for t in TEAM_CONFIG.keys()}
    st.session_state.race_no = 0
    st.session_state.form_id = 0

# --- 3. 側邊欄：手動輸入初始值 ---
with st.sidebar:
    st.header("⚙️ 賽季初始化設定")
    
    # 這裡讓使用者輸入初始評分
    with st.expander("👤 設定車手初始能力值", expanded=(st.session_state.race_no == 0)):
        st.info("賽季開始後仍可微調，但建議在第一場前設定完畢。")
        for d in st.session_state.stats.keys():
            new_val = st.number_input(f"{d} (# {st.session_state.stats[d]['no']})", 
                                      0.0, 100.0, st.session_state.stats[d]["rating"], step=0.01)
            # 更新目前評分，若還沒跑過比賽，同步更新歷史起點
            st.session_state.stats[d]["rating"] = new_val
            if st.session_state.race_no == 0:
                st.session_state.stats[d]["rating_history"][0]["val"] = new_val

    with st.expander("🏎️ 設定車隊車輛等級 (1-10)"):
        for t in TEAM_CONFIG.keys():
            st.session_state.team_lv[t] = st.number_input(f"{t} 等級", 1, 10, st.session_state.team_lv[t])

    st.divider()
    st.header("💾 數據管理")
    backup_input = st.text_area("存檔代碼：", height=100)
    if st.button("載入存檔"):
        try:
            data = json.loads(backup_input)
            st.session_state.update(data)
            st.rerun()
        except: st.error("格式錯誤")
    if st.button("🚨 重置全賽季"):
        st.session_state.clear(); st.rerun()

# --- 4. 主介面 ---
st.title(f"🏎️ 2026 F1 賽季 (Week {st.session_state.race_no + 1})")
tabs = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置", "📈 能力值追蹤"])

with tabs[0]:
    r_type = st.radio("類型：", ["正賽", "衝刺賽"], horizontal=True)
    inputs = {}
    cols = st.columns(2)
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 2]:
            st.markdown(f"**{team}** ({st.session_state.team_lv[team]})")
            for driver, no in cfg["drivers"].items():
                inputs[driver] = st.text_input(f"#{no} {driver} (Rating: {st.session_state.stats[driver]['rating']:.1f})", key=f"in_{driver}_{st.session_state.form_id}")

    if st.button("🚀 提交本場成績", use_container_width=True, type="primary"):
        # 校驗輸入與邏輯 (略，與前版相同)
        processed, used_ranks, err = {}, set(), False
        for d, r in inputs.items():
            v = r.strip().upper()
            if v == 'R': processed[d] = 'R'
            elif v.isdigit() and 1 <= int(v) <= 22 and int(v) not in used_ranks:
                processed[d] = int(v); used_ranks.add(int(v))
            else: err = True
        
        if err or len(processed) < 22:
            st.error("❌ 請確認所有排名是否正確填寫且不重複。")
        else:
            if r_type == "正賽":
                st.session_state.race_no += 1
            curr_m = st.session_state.race_no if r_type == "正賽" else st.session_state.race_no + 0.5

            if r_type == "正賽":
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                res_sorted = sorted(processed.items(), key=lambda x: 99 if x[1]=='R' else x[1])
                
                # 計算積分與能力值變動
                for d, r in res_sorted:
                    s = st.session_state.stats[d]
                    s["ranks"].append(r)
                    p = 0
                    if r != 'R':
                        if r == 1: s["p1"] += 1
                        if r <= 10 and pts_pool: p = pts_pool.pop(0)
                        s["points"] += p
                    else: s["dnf"] += 1
                    s["point_history"].append({"race": curr_m, "pts": s["points"]})

                # 能力值系統
                for team, cfg in TEAM_CONFIG.items():
                    ds = list(cfg["drivers"].keys())
                    r1, r2 = processed[ds[0]], processed[ds[1]]
                    lv = st.session_state.team_lv[team]
                    
                    # 隊友對決
                    if r1 != 'R' and r2 != 'R':
                        shift = ((r2 - r1) // 3) * 0.1
                        st.session_state.stats[ds[0]]["rating"] += shift
                        st.session_state.stats[ds[1]]["rating"] -= shift
                    
                    # 完賽矩陣與紀錄歷史
                    for d_name in ds:
                        st.session_state.stats[d_name]["rating"] += get_matrix_change(processed[d_name], lv)
                        st.session_state.stats[d_name]["rating_history"].append({"race": curr_m, "val": round(st.session_state.stats[d_name]["rating"], 2)})
            
            # 更新車隊歷史 (同前)
            for t in TEAM_CONFIG.keys():
                t_sum = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                st.session_state.team_history[t].append({"race": curr_m, "pts": t_sum})

            st.session_state.form_id += 1
            st.rerun()

# --- 5. 圖表與排行榜 (與前版邏輯相同) ---
with tabs[1]:
    # 車手 WDC 榜單
    d_list = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1']), reverse=True)
    st.dataframe(pd.DataFrame([{
        "排名": i, "車手": n, "車隊": s['team'], "能力值": round(s['rating'],1), "積分": s['points'], "P1": s['p1'], "DNF": s['dnf']
    } for i, (n, s) in enumerate(d_list, 1)]), use_container_width=True, hide_index=True)

with tabs[4]:
    # 能力值歷史曲線
    if st.session_state.race_no > 0:
        plot_data = []
        for d, s in st.session_state.stats.items():
            for h in s['rating_history']:
                plot_data.append({"Race": h["race"], "Driver": d, "Rating": h["val"], "Team": s["team"]})
        fig = px.line(pd.DataFrame(plot_data), x="Race", y="Rating", color="Driver", markers=True, 
                      color_discrete_map={d: TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()},
                      title="車手能力值走勢圖 (起始值 -> 動態變化)")
        st.plotly_chart(fig, use_container_width=True)

# 存檔代碼
st.divider()
st.code(json.dumps({k: v for k, v in st.session_state.items() if k in ["stats", "team_lv", "race_no", "team_history", "form_id"]}))
