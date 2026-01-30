import streamlit as st
import pandas as pd
import json
import plotly.express as px

# --- 頁面設定 ---
st.set_page_config(page_title="2026 F1 Scoring Pro", page_icon="🏎️", layout="wide")

# --- 數據初始化 ---
# 確保這些變數在整個會話中持續存在
if "stats" not in st.session_state:
    st.session_state.stats = {d: {"team": t, "points": 0, "ranks": [], "point_history": [0], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False} 
                             for t, ds in {
                                "McLaren": ["Lando Norris", "Oscar Piastri"],
                                "Ferrari": ["Lewis Hamilton", "Charles Leclerc"],
                                "Red Bull": ["Max Verstappen", "Isack Hadjar"],
                                "Mercedes": ["George Russell", "Kimi Antonelli"],
                                "Aston Martin": ["Fernando Alonso", "Lance Stroll"],
                                "Audi": ["Nico Hulkenberg", "Gabriel Bortoleto"],
                                "Williams": ["Carlos Sainz", "Alex Albon"],
                                "Alpine": ["Pierre Gasly", "Franco Colapinto"],
                                "Racing Bulls": ["Liam Lawson", "Arvid Lindblad"],
                                "Haas": ["Esteban Ocon", "Oliver Bearman"],
                                "APX-CTWR": ["Yuki Tsunoda", "Ethan Tan"]
                             }.items() for d in ds}
    st.session_state.race_no = 0

# --- 核心規則函數 ---
def get_race_points(rank):
    return {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}.get(rank, 0)

def get_sprint_points(rank, is_top_10):
    pts = {1:5, 2:3, 3:1}.get(rank, 0)
    if not is_top_10:
        pts += {1:8, 2:7, 3:6, 4:5, 5:4, 6:3, 7:2, 8:1}.get(rank, 0)
    return pts

# --- 側邊欄 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("在此貼上存檔代碼：", height=100)
    if st.button("載入存檔"):
        try:
            data = json.loads(backup_input)
            st.session_state.stats = data["stats"]
            st.session_state.race_no = data["race_no"]
            st.success(f"已載入第 {st.session_state.race_no} 場進度")
            st.rerun()
        except:
            st.error("格式錯誤")
    
    if st.button("🚨 重置全賽季"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()

# --- 主介面 ---
st.title(f"🏎️ 2026 F1 賽季 - 當前第 {st.session_state.race_no} 場結束")

tab_input, tab_driver, tab_team, tab_chart = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📈 趨勢圖"])

with tab_input:
    next_race = st.session_state.race_no + 1
    st.subheader(f"📝 輸入第 {next_race} 場成績")
    race_type = st.radio("類型：", ["正賽", "衝刺賽"], horizontal=True)
    
    # 判定 Top 10 (基於上一場結束後的排名)
    current_ranking = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1'], st.session_state.stats[x]['p2'], st.session_state.stats[x]['p3']), reverse=True)
    top_10_set = set(current_ranking[:10])

    # 使用 Form 確保輸入時不會一直刷新
    with st.form("race_input_form"):
        input_ranks = {}
        cols = st.columns(3)
        for i, driver in enumerate(st.session_state.stats.keys()):
            with cols[i % 3]:
                input_ranks[driver] = st.text_input(driver, key=f"f_{driver}", placeholder="1-22/R")
        
        submitted = st.form_submit_button("確認提交成績")
        
        if submitted:
            # 驗證邏輯
            processed = {}
            used = set()
            err = False
            for d, r in input_ranks.items():
                val = r.strip().upper()
                if val == 'R': processed[d] = 22
                else:
                    try:
                        n = int(val)
                        if 1 <= n <= 22 and n not in used:
                            processed[d] = n
                            used.add(n)
                        else: err = True
                    except: err = True
            
            if err or len(processed) < 22:
                st.error("請檢查排名是否重複或漏填！")
            else:
                # 計算積分並存入 session_state
                st.session_state.race_no += 1
                sorted_results = sorted(processed.items(), key=lambda x: x[1])
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                
                for d, r in sorted_results:
                    s = st.session_state.stats[d]
                    s["ranks"].append(r)
                    if r == 1: s["p1"] += 1
                    elif r == 2: s["p2"] += 1
                    elif r == 3: s["p3"] += 1
                    if r == 22:
                        s["dnf"] += 1
                        if s["dnf"] % 5 == 0: s["penalty_next"] = True
                    
                    p = 0
                    if race_type == "衝刺賽":
                        p = get_sprint_points(r, d in top_10_set)
                    else:
                        if pts_pool and r <= 10:
                            if s["penalty_next"]: s["penalty_next"] = False
                            else: p = pts_pool.pop(0)
                    
                    s["points"] += p
                    s["point_history"].append(s["points"])
                
                st.success(f"✅ 第 {st.session_state.race_no} 場已入庫！")
                st.rerun() # 強制刷新顯示新數據
# --- 這裡接在 st.rerun() 之後 ---

with tab_driver:
@@ -45,3 +172,6 @@
st.write("### 🔑 本次更新後的存檔代碼 (請複製保存)")
save_code = json.dumps({"stats": st.session_state.stats, "race_no": st.session_state.race_no})
st.code(save_code)

# --- 顯示與圖表部分 (保持不變) ---
# ... (與上個版本相同，包含 WDC, WCC 和 Plotly 圖表)
