import streamlit as st
import pandas as pd
import json
import plotly.express as px

# --- 1. 核心數據配置 ---
TEAM_CONFIG = {
    "McLaren": {"color": "#FF8700", "tier": 10, "drivers": ["Lando Norris", "Oscar Piastri"]},
    "Ferrari": {"color": "#E80020", "tier": 10, "drivers": ["Lewis Hamilton", "Charles Leclerc"]},
    "Red Bull": {"color": "#3671C6", "tier": 9, "drivers": ["Max Verstappen", "Isack Hadjar"]},
    "Mercedes": {"color": "#27F4D2", "tier": 9, "drivers": ["George Russell", "Kimi Antonelli"]},
    "Aston Martin": {"color": "#229971", "tier": 8, "drivers": ["Fernando Alonso", "Lance Stroll"]},
    "Audi": {"color": "#F50A20", "tier": 8, "drivers": ["Nico Hulkenberg", "Gabriel Bortoleto"]},
    "Williams": {"color": "#64C4FF", "tier": 8, "drivers": ["Carlos Sainz", "Alex Albon"]},
    "Alpine": {"color": "#0093CC", "tier": 8, "drivers": ["Pierre Gasly", "Franco Colapinto"]},
    "Racing Bulls": {"color": "#6692FF", "tier": 8, "drivers": ["Liam Lawson", "Arvid Lindblad"]},
    "Haas": {"color": "#B6BABD", "tier": 8, "drivers": ["Esteban Ocon", "Oliver Bearman"]},
    "APX-CTWR": {"color": "#000000", "tier": 8, "drivers": ["Yuki Tsunoda", "Ethan Tan"]}
}

# 10/9/8 性能矩陣
MATRIX = {
    10: {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.2, 6: 0, 7: -0.1, 8: -0.2, 9: -0.3, 10: -0.4, 11: -0.5, 12: -0.6, 13: -0.7, 14: -0.8, 15: -0.9, 16: -1.0, 17: -1.1, 18: -1.2, 19: -1.3, 20: -1.4, 21: -1.5, 22: -1.6},
    9: {1: 1.5, 2: 1.2, 3: 1.0, 4: 0.8, 5: 0.6, 6: 0.4, 7: 0.2, 8: 0, 9: -0.1, 10: -0.2, 11: -0.3, 12: -0.4, 13: -0.5, 14: -0.6, 15: -0.7, 16: -0.8, 17: -0.9, 18: -1.0, 19: -1.1, 20: -1.2, 21: -1.3, 22: -1.4},
    8: {1: 2.0, 2: 1.7, 3: 1.4, 4: 1.2, 5: 1.0, 6: 0.8, 7: 0.6, 8: 0.4, 9: 0.2, 10: 0, 11: -0.1, 12: -0.2, 13: -0.3, 14: -0.4, 15: -0.5, 16: -0.6, 17: -0.7, 18: -0.8, 19: -0.9, 20: -1.0, 21: -1.1, 22: -1.2}
}

# --- 2. 輔助函數：查找隊友 ---
def get_teammate(driver_name):
    for team, cfg in TEAM_CONFIG.items():
        if driver_name in cfg["drivers"]:
            teammate = [d for d in cfg["drivers"] if d != driver_name][0]
            return teammate, cfg["tier"]
    return None, None

# --- 3. 初始化 Session State ---
if "initialized" not in st.session_state:
    st.session_state.stats = {}
    for team, cfg in TEAM_CONFIG.items():
        for d in cfg["drivers"]:
            st.session_state.stats[d] = {
                "team": team, "points": 0, "ranks": [], 
                "rating": 8.5, "rating_history": [8.5], # 簡化 history 存數值即可
                "p1": 0, "dnf": 0
            }
    st.session_state.race_no = 0
    st.session_state.initialized = True

# --- 4. 介面佈局 ---
st.set_page_config(page_title="2026 F1 精算系統", layout="wide")

with st.sidebar:
    st.title("🏎️ 賽事選單")
    page = st.radio("前往分頁", ["1. 比賽結果輸入", "2. 車手排行榜", "3. 完賽紀錄明細", "4. 能力計算細節", "5. 實力趨勢圖", "6. 數據管理"])
    st.divider()
    if st.button("🚨 重置所有數據"):
        st.session_state.clear()
        st.rerun()

# --- 5. 分頁功能 ---

# [頁面 1: 輸入結果]
if page == "1. 比賽結果輸入":
    st.header(f"🏁 第 {st.session_state.race_no + 1} 場錄入")
    
    with st.form("race_input"):
        inputs = {}
        cols = st.columns(2)
        all_drivers = list(st.session_state.stats.keys())
        for idx, driver in enumerate(all_drivers):
            with cols[idx % 2]:
                inputs[driver] = st.text_input(f"{driver} ({st.session_state.stats[driver]['team']})", placeholder="1-22 / R")
        
        submit = st.form_submit_button("🚀 提交本場成績")
        
        if submit:
            pts_table = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1] + [0]*12
            this_race_data = {}
            
            # 數據解析
            try:
                for d, v in inputs.items():
                    val = v.strip().upper()
                    this_race_data[d] = 'R' if val == 'R' else int(val)
                
                # 計算更新
                st.session_state.race_no += 1
                for d, rank in this_race_data.items():
                    s = st.session_state.stats[d]
                    tm, tier = get_teammate(d)
                    
                    # 積分
                    if rank != 'R':
                        s["points"] += pts_table[rank-1] if rank <= 10 else 0
                        if rank == 1: s["p1"] += 1
                        
                        # 能力評估
                        sp = MATRIX[tier].get(rank, -1.0)
                        tm_rank = this_race_data[tm]
                        e_tm_rank = 23 if tm_rank == 'R' else tm_rank
                        
                        h2h = 0
                        if e_tm_rank > rank: h2h = ((e_tm_rank - rank) // 3) * 0.1
                        elif rank > e_tm_rank: h2h = ((e_tm_rank - rank) // 3 + 1) * 0.1
                        
                        s["rating"] += (sp + h2h)
                    else:
                        s["dnf"] += 1
                    
                    s["rating"] = max(min(s["rating"], 10.4), 6.5)
                    s["rating_history"].append(round(s["rating"], 2))
                    s["ranks"].append(rank)
                
                st.success("錄入成功！")
                st.rerun()
            except ValueError:
                st.error("❌ 輸入格式錯誤！名次請輸入數字，退賽請輸入 R")

# [頁面 2: 排行榜]
elif page == "2. 車手排行榜":
    st.header("🏆 積分與下場設定榜")
    data = []
    for d, s in st.session_state.stats.items():
        data.append([d, s["team"], s["points"], round(s["rating"], 2), round(s["rating"]), s["dnf"]])
    
    df = pd.DataFrame(data, columns=["車手", "車隊", "積分", "精算分", "下場設定", "DNF"])
    st.dataframe(df.sort_values("積分", ascending=False), use_container_width=True, hide_index=True)

# [頁面 3: 紀錄表]
elif page == "3. 完賽紀錄明細":
    st.header("📅 歷史名次追蹤")
    if st.session_state.race_no > 0:
        pos_df = pd.DataFrame([{"車手": d, **{f"Rd.{i+1}": r for i, r in enumerate(s["ranks"])}} for d, s in st.session_state.stats.items()])
        st.dataframe(pos_df, use_container_width=True)
    else:
        st.info("尚無比賽數據")

# [頁面 4: 計算細節]
elif page == "4. 能力計算細節":
    st.header("🧪 狀態變動分析")
    form_data = []
    for d, s in st.session_state.stats.items():
        change = s["rating_history"][-1] - s["rating_history"][-2] if len(s["rating_history"]) > 1 else 0
        form_data.append({"車手": d, "目前分": s["rating_history"][-1], "本場變動": round(change, 2)})
    st.table(pd.DataFrame(form_data).sort_values("目前分", ascending=False))

# [頁面 5: 趨勢圖]
elif page == "5. 實力趨勢圖":
    st.header("📈 能力走勢線圖")
    chart_rows = []
    for d, s in st.session_state.stats.items():
        for i, val in enumerate(s["rating_history"]):
            chart_rows.append({"Round": i, "Driver": d, "Rating": val})
    if chart_rows:
        fig = px.line(pd.DataFrame(chart_rows), x="Round", y="Rating", color="Driver", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

# [頁面 6: 數據管理]
elif page == "6. 數據管理":
    st.header("💾 進度備份")
    st.code(json.dumps({"stats": st.session_state.stats, "race_no": st.session_state.race_no}))
