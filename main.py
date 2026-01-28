import streamlit as st
import pandas as pd
import json

# --- 頁面設定 ---
st.set_page_config(page_title="2026 F1 Scoring System", page_icon="🏎️")
st.title("🏎️ 2026 F1 賽季計分系統 (GitHub 網頁版)")

# --- 核心積分規則 ---
def get_race_points(rank):
    points_map = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
    return points_map.get(rank, 0)

def get_sprint_points(rank, is_top_10_overall):
    pts = 0
    if not is_top_10_overall:
        bottom_map = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}
        pts += bottom_map.get(rank, 0)
    top_bonus_map = {1: 5, 2: 3, 3: 1}
    pts += top_bonus_map.get(rank, 0)
    return pts

# --- 初始化車隊名單 ---
TEAMS = {
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
}

# --- 側邊欄：存檔管理 ---
with st.sidebar:
    st.header("💾 存檔管理")
    backup_input = st.text_area("在此貼上備份代碼以載入進度：")
    
    if "stats" not in st.session_state:
        if backup_input:
            try:
                data = json.loads(backup_input)
                st.session_state.stats = data["stats"]
                st.session_state.race_no = data["race_no"]
                st.success("存檔讀取成功！")
            except:
                st.error("代碼格式錯誤。")
        else:
            # 初始化全新賽季
            st.session_state.stats = {d: {"team": t, "points": 0, "ranks": [], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False} 
                                     for t, ds in TEAMS.items() for d in ds}
            st.session_state.race_no = 0

# --- 主介面 ---
tab1, tab2 = st.tabs(["🏁 輸入比賽成績", "📊 賽季積分榜"])

with tab1:
    race_type = st.radio("選擇場次類型：", ["正賽", "衝刺賽"], horizontal=True)
    st.write(f"### 第 {st.session_state.race_no + 1} 場比賽輸入")
    
    # 計算目前的 Top 10
    current_ranking = sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1'], st.session_state.stats[x]['p2'], st.session_state.stats[x]['p3']), reverse=True)
    top_10_set = set(current_ranking[:10])

    input_ranks = {}
    cols = st.columns(2)
    drivers_list = list(st.session_state.stats.keys())
    
    for i, driver in enumerate(drivers_list):
        with cols[i % 2]:
            res = st.text_input(f"{driver} ({st.session_state.stats[driver]['team']})", key=f"in_{driver}", placeholder="1-22 或 R")
            input_ranks[driver] = res

    if st.button("確認提交成績"):
        processed_ranks = {}
        error = False
        used_nums = set()
        
        # 驗證輸入
        for d, r in input_ranks.items():
            r_up = r.strip().upper()
            if r_up == 'R':
                processed_ranks[d] = 22
            else:
                try:
                    num = int(r_up)
                    if 1 <= num <= 22 and num not in used_nums:
                        processed_ranks[d] = num
                        used_nums.add(num)
                    else:
                        error = True
                        st.error(f"排名錯誤或重複：{d}")
                except:
                    error = True
                    st.error(f"無效輸入：{d}")
        
        if not error:
            # 計算積分
            st.session_state.race_no += 1
            sorted_this_race = sorted(processed_ranks.items(), key=lambda x: x[1])
            race_pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
            
            for d, r in sorted_this_race:
                s = st.session_state.stats[d]
                s["ranks"].append(r)
                if r == 1: s["p1"] += 1
                elif r == 2: s["p2"] += 1
                elif r == 3: s["p3"] += 1
                if r == 22:
                    s["dnf"] += 1
                    if s["dnf"] % 5 == 0: s["penalty_next"] = True
                
                if race_type == "衝刺賽":
                    s["points"] += get_sprint_points(r, d in top_10_set)
                else:
                    if race_pts_pool and r <= 10:
                        if s["penalty_next"]:
                            s["penalty_next"] = False
                        else:
                            s["points"] += race_pts_pool.pop(0)
            st.success("成績已更新！請切換至積分榜查看。")

with tab2:
    st.subheader("📊 2026 賽季當前排名")
    # 轉換成 DataFrame 顯示
    df_data = []
    final_sort = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1'], x[1]['p2'], x[1]['p3'], -sum(x[1]['ranks'])/len(x[1]['ranks']) if x[1]['ranks'] else 0), reverse=True)
    
    for i, (name, s) in enumerate(final_sort, 1):
        avg = sum(s["ranks"])/len(s["ranks"]) if s["ranks"] else 0
        df_data.append([i, name, s["team"], s["points"], f"{s['p1']}/{s['p2']}/{s['p3']}", s["dnf"], round(avg, 1)])
    
    df = pd.DataFrame(df_data, columns=["排名", "車手", "車隊", "總分", "P1/P2/P3", "退賽次數", "平均排名"])
    st.table(df)

    # 顯示備份代碼
    st.divider()
    st.write("### 🔑 存檔代碼 (請複製保存)")
    save_code = json.dumps({"stats": st.session_state.stats, "race_no": st.session_state.race_no})
    st.code(save_code)
