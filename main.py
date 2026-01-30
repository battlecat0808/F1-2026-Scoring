import streamlit as st
import pandas as pd
import json
import plotly.express as px

# --- 1. 基礎網頁設定 ---
st.set_page_config(page_title="S6 賽季精算儀", layout="wide")

# --- 2. 核心參數數據 (10/9/8 矩陣) ---
MATRIX = {
    10: {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.2, 6: 0, 7: -0.1, 8: -0.2, 9: -0.3, 10: -0.4, 11: -0.5, 12: -0.6, 13: -0.7, 14: -0.8, 15: -0.9, 16: -1.0, 17: -1.1, 18: -1.2, 19: -1.3, 20: -1.4, 21: -1.5, 22: -1.6},
    9: {1: 1.5, 2: 1.2, 3: 1.0, 4: 0.8, 5: 0.6, 6: 0.4, 7: 0.2, 8: 0, 9: -0.1, 10: -0.2, 11: -0.3, 12: -0.4, 13: -0.5, 14: -0.6, 15: -0.7, 16: -0.8, 17: -0.9, 18: -1.0, 19: -1.1, 20: -1.2, 21: -1.3, 22: -1.4},
    8: {1: 2.0, 2: 1.7, 3: 1.4, 4: 1.2, 5: 1.0, 6: 0.8, 7: 0.6, 8: 0.4, 9: 0.2, 10: 0, 11: -0.1, 12: -0.2, 13: -0.3, 14: -0.4, 15: -0.5, 16: -0.6, 17: -0.7, 18: -0.8, 19: -0.9, 20: -1.0, 21: -1.1, 22: -1.2}
}

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

# --- 3. 數據初始化 ---
if "stats" not in st.session_state:
    st.session_state.stats = {}
    for team, cfg in TEAM_CONFIG.items():
        for d in cfg["drivers"]:
            st.session_state.stats[d] = {
                "team": team, "points": 0, "ranks": [], 
                "rating": 8.5, "rating_history": [{"race": 0, "val": 8.5}],
                "p1": 0, "dnf": 0
            }
    st.session_state.race_no = 0
    st.session_state.form_id = 100

# --- 4. 側邊欄導航 (舊版 Radio 樣式) ---
with st.sidebar:
    st.title("🏁 S6 精算後台")
    menu = st.radio("功能導航", ["1. 比賽結果錄入", "2. 車手排行榜", "3. 完賽紀錄表", "4. 狀態計算細節", "5. 趨勢分析圖", "6. 數據管理"])
    st.divider()
    if st.button("🚨 重置全賽季"):
        st.session_state.clear()
        st.rerun()

# --- 5. 頁面邏輯分流 ---

# [1. 比賽結果錄入]
if menu == "1. 比賽結果錄入":
    st.header(f"🏁 第 {st.session_state.race_no + 1} 場成績錄入")
    st.info("輸入名次 (1-22) 或退賽輸入 'R'")
    inputs = {}
    cols = st.columns(2)
    for i, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[i % 2]:
            st.markdown(f"**{team} (T{cfg['tier']})**")
            for d in cfg["drivers"]:
                inputs[d] = st.text_input(f"{d}", key=f"in_{d}_{st.session_state.form_id}")
    
    if st.button("🚀 提交成績", use_container_width=True, type="primary"):
        pts_map = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1] + [0]*12
        st.session_state.race_no += 1
        
        # 暫存本場名次用於 H2H 計算
        this_race_ranks = {}
        for d, val in inputs.items():
            v = val.strip().upper()
            this_race_ranks[d] = 'R' if v == 'R' else int(v) if v.isdigit() else 22
            
        # 更新每位車手
        for d, rank in this_race_ranks.items():
            s = st.session_state.stats[d]
            tier = TEAM_CONFIG[s["team"]]["tier"]
            
            # 積分更新
            if rank != 'R':
                s["points"] += pts_map[rank-1] if rank <= 10 else 0
                if rank == 1: s["p1"] += 1
                
                # 能力計算 (SP + H2H)
                sp = MATRIX[tier].get(rank, -1.0)
                teammate = [n for n in TEAM_CONFIG[s["team"]]["drivers"] if n != d][0]
                t_rank = this_race_ranks[teammate]
                e_t_rank = 23 if t_rank == 'R' else t_rank
                
                h2h = 0
                if e_t_rank > rank: h2h = ((e_t_rank - rank) // 3) * 0.1
                elif rank > e_t_rank: h2h = ((e_t_rank - rank) // 3 + 1) * 0.1
                
                s["rating"] += (sp + h2h)
            else:
                s["dnf"] += 1
                
            s["rating"] = max(min(s["rating"], 10.4), 6.5) # 限制範圍
            s["rating_history"].append({"race": st.session_state.race_no, "val": s["rating"]})
            s["ranks"].append(rank)
            
        st.session_state.form_id += 1
        st.success("成績錄入成功！")
        st.rerun()

# [2. 車手排行榜]
elif menu == "2. 車手排行榜":
    st.header("🏆 車手積分榜與下場設定")
    table_data = []
    for d, s in st.session_state.stats.items():
        table_data.append({
            "車手": d, "車隊": s["team"], "積分": s["points"],
            "精算評分": round(s["rating"], 2),
            "下場遊戲設定": round(s["rating"]),
            "DNF": s["dnf"]
        })
    df = pd.DataFrame(table_data).sort_values("積分", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

# [3. 完賽紀錄表]
elif menu == "3. 完賽紀錄表":
    st.header("📅 全賽季完賽紀錄明細")
    pos_data = []
    for d, s in st.session_state.stats.items():
        row = {"車手": d}
        for i, r in enumerate(s["ranks"]):
            row[f"Rd.{i+1}"] = r
        pos_data.append(row)
    st.dataframe(pd.DataFrame(pos_data), use_container_width=True)

# [4. 狀態計算細節]
elif menu == "4. 狀態計算細節":
    st.header("🧪 車手實力變動細節")
    calc_data = []
    for d, s in st.session_state.stats.items():
        change = s["rating"] - s["rating_history"][-2]["val"] if len(s["rating_history"]) > 1 else 0
        calc_data.append({
            "車手": d, "目前評分": round(s["rating"], 2), "本場變動": round(change, 2)
        })
    st.table(pd.DataFrame(calc_data).sort_values("目前評分", ascending=False))

# [5. 趨勢分析圖]
elif menu == "5. 趨勢分析圖":
    st.header("📈 車手能力走勢分析")
    plot_list = []
    for d, s in st.session_state.stats.items():
        for h in s["rating_history"]:
            plot_list.append({"場次": h["race"], "車手": d, "評分": h["val"]})
    if plot_list:
        fig = px.line(pd.DataFrame(plot_list), x="場次", y="評分", color="車手", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

# [6. 數據管理]
elif menu == "6. 數據管理":
    st.header("💾 進度備份代碼")
    st.write("複製下方的代碼並保存到記事本，以便下次讀取：")
    # 將 Session State 轉為 JSON
    save_data = {
        "stats": st.session_state.stats,
        "race_no": st.session_state.race_no,
        "form_id": st.session_state.form_id
    }
    st.code(json.dumps(save_data))
