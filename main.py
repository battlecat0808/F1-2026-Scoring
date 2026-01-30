import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Ultimate", page_icon="🏎️", layout="wide")

# --- 1. 核心配置 ---
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

# --- 2. 初始化 ---
if "stats" not in st.session_state:
    st.session_state.stats = {
        d: {
            "no": c, "team": t, "points": 0, "ranks": [], 
            "point_history": [{"race": 0, "pts": 0}], 
            "rating_history": [{"race": 0, "val": 85.0}],
            "p1": 0, "p2": 0, "p3": 0, "dnf": 0, 
            "penalty_next": False, "prev_rank": 0, "rating": 85.0
        } for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()
    }
    st.session_state.team_lv = {t: 9 for t in TEAM_CONFIG.keys()}
    st.session_state.team_history = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
    st.session_state.team_prev_rank = {t: 0 for t in TEAM_CONFIG.keys()}
    st.session_state.race_no = 0
    st.session_state.form_id = 0

# --- 3. 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 賽季設定")
    with st.expander("🏎️ 車輛評級"):
        for t in TEAM_CONFIG.keys():
            st.session_state.team_lv[t] = st.number_input(f"{t}", 1, 10, st.session_state.team_lv[t], key=f"lv_{t}")
    with st.expander("👤 初始能力值"):
        for d in st.session_state.stats.keys():
            st.session_state.stats[d]["rating"] = st.number_input(f"{d}", 0.0, 100.0, st.session_state.stats[d]["rating"], step=0.1, key=f"init_{d}")
    
    st.divider()
    backup_input = st.text_area("💾 數據代碼：", height=100)
    if st.button("載入"):
        try:
            data = json.loads(backup_input)
            for k, v in data.items(): st.session_state[k] = v
            st.success("成功！"); st.rerun()
        except: st.error("格式錯誤")
    if st.button("🚨 重置"):
        st.session_state.clear(); st.rerun()

# --- 4. 主介面 ---
st.title(f"🏎️ 2026 F1 Season - Week {st.session_state.race_no + 1}")
tabs = st.tabs(["🏁 輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 名次", "📈 能力值"])

with tabs[0]:
    r_type = st.radio("賽事：", ["正賽", "衝刺賽"], horizontal=True)
    inputs = {}
    cols = st.columns(2)
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 2]:
            st.markdown(f"**{team}** (Lv.{st.session_state.team_lv[team]})")
            for driver, no in cfg["drivers"].items():
                inputs[driver] = st.text_input(f"#{no} {driver}", key=f"in_{driver}_{st.session_state.form_id}", placeholder="1-22 / R")

    if st.button("🚀 提交成績", use_container_width=True, type="primary"):
        processed, used_ranks, err = {}, set(), False
        for d, r in inputs.items():
            v = r.strip().upper()
            if v == 'R': processed[d] = 'R'
            elif v.isdigit() and 1 <= int(v) <= 22 and int(v) not in used_ranks:
                processed[d] = int(v); used_ranks.add(int(v))
            else: err = True
        
        if err or len(processed) < 22:
            st.error("❌ 輸入無效（名次重複、漏填或超出範圍）")
        else:
            # 正賽特殊邏輯：更新趨勢與場次
            if r_type == "正賽":
                # 存下前次排名
                wdc_now = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1']), reverse=True)
                for i, name in enumerate(wdc_now, 1): st.session_state.stats[name]["prev_rank"] = i
                st.session_state.race_no += 1

            curr_m = st.session_state.race_no if r_type == "正賽" else st.session_state.race_no + 0.5

            if r_type == "正賽":
                pts = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                res_sorted = sorted(processed.items(), key=lambda x: 99 if x[1]=='R' else x[1])
                for d, r in res_sorted:
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
                        if r <= 10 and pts:
                            if s["penalty_next"]: s["penalty_next"] = False
                            else: p = pts.pop(0)
                    s["points"] += p
                    s["point_history"].append({"race": curr_m, "pts": s["points"]})

                # 能力值計算
                for t, cfg in TEAM_CONFIG.items():
                    ds = list(cfg["drivers"].keys())
                    r1, r2 = processed[ds[0]], processed[ds[1]]
                    if r1 != 'R' and r2 != 'R':
                        diff = r2 - r1
                        st.session_state.stats[ds[0]]["rating"] += (diff // 3) * 0.1
                        st.session_state.stats[ds[1]]["rating"] -= (diff // 3) * 0.1
                    for d_name in ds:
                        st.session_state.stats[d_name]["rating"] += calculate_rating_change(processed[d_name], st.session_state.team_lv[t])
                        st.session_state.stats[d_name]["rating_history"].append({"race": curr_m, "val": round(st.session_state.stats[d_name]["rating"], 2)})
            
            else: # 衝刺賽
                # 這裡保留原本您的衝刺賽邏輯... (略)
                pass

            for t in TEAM_CONFIG.keys():
                t_pts = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                st.session_state.team_history[t].append({"race": curr_m, "pts": t_pts})
            
            st.session_state.form_id += 1
            st.rerun()

# --- 5. 數據看板 (WDC, WCC, Rating 繪圖) ---
with tabs[1]:
    d_list = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1']), reverse=True)
    df_wdc = pd.DataFrame([{
        "排名": i, "車手": n, "車隊": s['team'], "積分": s['points'], "能力值": round(s['rating'],1), "P1/P2/P3": f"{s['p1']}/{s['p2']}/{s['p3']}"
    } for i, (n, s) in enumerate(d_list, 1)])
    st.dataframe(df_wdc, use_container_width=True, hide_index=True)

with tabs[4]:
    if st.session_state.race_no > 0:
        rh = []
        for d, s in st.session_state.stats.items():
            for pt in s['rating_history']:
                rh.append({"Race": pt["race"], "Driver": d, "Rating": pt["val"], "Team": s["team"]})
        fig = px.line(pd.DataFrame(rh), x="Race", y="Rating", color="Driver", markers=True, 
                      color_discrete_map={d: TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()})
        st.plotly_chart(fig, use_container_width=True)

# 存檔代碼顯示
st.divider()
st.code(json.dumps({k: v for k, v in st.session_state.items() if k in ["stats", "team_lv", "race_no", "team_history", "team_prev_rank", "form_id"]}))
