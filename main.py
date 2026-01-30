import streamlit as st
import pandas as pd
import json
import plotly.express as px

# --- 1. 核心設定：車隊、顏色、與賽車等級 (Tier) ---
TEAM_CONFIG = {
    "McLaren": {"color": "#FF8700", "tier": 10, "drivers": {"Lando Norris": "1", "Oscar Piastri": "81"}},
    "Ferrari": {"color": "#E80020", "tier": 10, "drivers": {"Lewis Hamilton": "44", "Charles Leclerc": "16"}},
    "Red Bull": {"color": "#3671C6", "tier": 9, "drivers": {"Max Verstappen": "3", "Isack Hadjar": "66"}},
    "Mercedes": {"color": "#27F4D2", "tier": 9, "drivers": {"George Russell": "63", "Kimi Antonelli": "12"}},
    "Aston Martin": {"color": "#229971", "tier": 8, "drivers": {"Fernando Alonso": "14", "Lance Stroll": "18"}},
    "Audi": {"color": "#F50A20", "tier": 8, "drivers": {"Nico Hulkenberg": "27", "Gabriel Bortoleto": "5"}},
    "Williams": {"color": "#64C4FF", "tier": 8, "drivers": {"Carlos Sainz": "55", "Alex Albon": "23"}},
    "Alpine": {"color": "#0093CC", "tier": 8, "drivers": {"Pierre Gasly": "10", "Franco Colapinto": "43"}},
    "Racing Bulls": {"color": "#6692FF", "tier": 8, "drivers": {"Liam Lawson": "30", "Arvid Lindblad": "17"}},
    "Haas": {"color": "#B6BABD", "tier": 8, "drivers": {"Esteban Ocon": "31", "Oliver Bearman": "87"}},
    "APX-CTWR": {"color": "#000000", "tier": 8, "drivers": {"Yuki Tsunoda": "22", "Ethan Tan": "9"}}
}

# --- 2. 能力變動矩陣 (10/9/8 矩陣) ---
# 這是你定義的：開爛車拿好名次加更多
MATRIX = {
    10: {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.2, 6: 0, 7: -0.1, 8: -0.2, 9: -0.3, 10: -0.4, 11: -0.5, 12: -0.6, 13: -0.7, 14: -0.8, 15: -0.9, 16: -1.0, 17: -1.1, 18: -1.2, 19: -1.3, 20: -1.4, 21: -1.5, 22: -1.6},
    9: {1: 1.5, 2: 1.2, 3: 1.0, 4: 0.8, 5: 0.6, 6: 0.4, 7: 0.2, 8: 0, 9: -0.1, 10: -0.2, 11: -0.3, 12: -0.4, 13: -0.5, 14: -0.6, 15: -0.7, 16: -0.8, 17: -0.9, 18: -1.0, 19: -1.1, 20: -1.2, 21: -1.3, 22: -1.4},
    8: {1: 2.0, 2: 1.7, 3: 1.4, 4: 1.2, 5: 1.0, 6: 0.8, 7: 0.6, 8: 0.4, 9: 0.2, 10: 0, 11: -0.1, 12: -0.2, 13: -0.3, 14: -0.4, 15: -0.5, 16: -0.6, 17: -0.7, 18: -0.8, 19: -0.9, 20: -1.0, 21: -1.1, 22: -1.2}
}

# --- 3. 初始化系統 ---
st.set_page_config(page_title="2026 F1 精算儀", page_icon="🏎️", layout="wide")

if "stats" not in st.session_state:
    st.session_state.stats = {d: {
        "no": c, "team": t, "points": 0, "ranks": [], 
        "point_history": [{"race": 0, "pts": 0}], 
        "rating": 8.5, 
        "rating_history": [{"race": 0, "val": 8.5}],
        "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "prev_rank": 0
    } for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
    st.session_state.race_no = 0
    st.session_state.form_id = 0

# --- 4. 側邊欄：數據備份與手動調整 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("讀取存檔 (貼上代碼)：", height=100)
    if st.button("載入存檔"):
        try:
            data = json.loads(backup_input)
            st.session_state.update(data)
            st.success("讀取成功！"); st.rerun()
        except: st.error("代碼格式不對喔")
    
    if st.button("🚨 重置全賽季數據"):
        st.session_state.clear(); st.rerun()
    
    st.divider()
    st.header("⚙️ 初始底盤微調")
    for d in sorted(st.session_state.stats.keys()):
        st.session_state.stats[d]["rating"] = st.sidebar.number_input(f"{d} 能力分", value=st.session_state.stats[d]["rating"], step=0.1)

# --- 5. 主介面：分頁設計 ---
st.title(f"🏎️ 2026 F1 賽季系統 - 第 {st.session_state.race_no + 1} 場")
tab_input, tab_wdc, tab_status, tab_pos, tab_chart = st.tabs(["🏁 成績錄入", "👤 車手積分榜", "🧪 能力精算細節", "📊 完賽歷史", "📈 趨勢圖"])

# 頁面 1：錄入成績
with tab_input:
    st.info("請輸入本場名次 (1-22) 或退賽輸入 'R'")
    inputs = {}
    cols = st.columns(2)
    for idx, (team, cfg) in enumerate(TEAM_CONFIG.items()):
        with cols[idx % 2]:
            st.markdown(f"**{team} (車輛: T{cfg['tier']})**")
            for driver, no in cfg["drivers"].items():
                inputs[driver] = st.text_input(f"#{no} {driver}", key=f"{driver}_{st.session_state.form_id}")

    if st.button("🚀 提交成績並更新所有數據", use_container_width=True, type="primary"):
        processed, used_ranks, err = {}, set(), False
        for d, r in inputs.items():
            v = r.strip().upper()
            if v == 'R': processed[d] = 'R'
            elif not v: err = True
            else:
                n = int(v)
                processed[d] = n; used_ranks.add(n)

        if err:
            st.error("有欄位沒填好或是名次重複了！")
        else:
            st.session_state.race_no += 1
            pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
            
            # 計算邏輯
            for d, r in processed.items():
                s = st.session_state.stats[d]
                car_tier = TEAM_CONFIG[s['team']]['tier']
                
                # A. 積分更新
                p = 0
                if r != 'R':
                    if r <= 10: p = pts_pool[r-1]
                    if r==1: s["p1"]+=1
                    elif r==2: s["p2"]+=1
                    elif r==3: s["p3"]+=1
                else: s["dnf"] += 1
                
                s["points"] += p
                s["ranks"].append(r)
                s["point_history"].append({"race": st.session_state.race_no, "pts": s["points"]})

                # B. 能力變動計算 (SP + H2H)
                if r != 'R':
                    sp = MATRIX[car_tier].get(r, -1.0)
                    # 找隊友名次
                    teammate = [n for n in TEAM_CONFIG[s['team']]['drivers'].keys() if n != d][0]
                    t_rank = processed[teammate]
                    
                    # 贏隊友紅利：每 3 名 +0.1
                    h2h_bonus = 0
                    effective_t_rank = 23 if t_rank == 'R' else t_rank
                    if effective_t_rank > r:
                        h2h_bonus = ((effective_t_rank - r) // 3) * 0.1
                    elif r > effective_t_rank:
                        h2h_bonus = ((effective_t_rank - r) // 3 + 1) * 0.1 # 輸隊友扣分
                        
                    s["rating"] += (sp + h2h_bonus)
                
                # 限制最高 10 分，最低 7 分
                s["rating"] = max(min(s["rating"], 10.4), 6.5)
                s["rating_history"].append({"race": st.session_state.race_no, "val": s["rating"]})

            st.session_state.form_id += 1
            st.rerun()

# 頁面 2：積分榜
with tab_wdc:
    d_sort = sorted(st.session_state.stats.items(), key=lambda x: x[1]['points'], reverse=True)
    d_data = [[i+1, n, s['team'], s['points'], f"{s['rating']:.2f}", round(s['rating']), s['p1'], s['dnf']] for i, (n, s) in enumerate(d_sort)]
    st.dataframe(pd.DataFrame(d_data, columns=["排名", "車手", "車隊", "總積分", "精算分", "下場遊戲等級", "冠軍次數", "DNF"]), use_container_width=True, hide_index=True)

# 頁面 3：能力細節
with tab_status:
    st.subheader("🧪 車手狀態精算表")
    status_df = pd.DataFrame([{"車手": d, "目前精算分": f"{s['rating']:.2f}", "遊戲等級設定": round(s['rating']), "最後變動": f"{s['rating'] - s['rating_history'][-2]['val']:+.2f}" if len(s['rating_history'])>1 else "0.00"} for d, s in st.session_state.stats.items()])
    st.table(status_df.sort_values("目前精算分", ascending=False))

# 頁面 4：完賽表
with tab_pos:
    st.subheader("📅 歷史完賽名次")
    pos_data = [{"車手": d, **{f"Rd.{i+1}": r for i, r in enumerate(s["ranks"])}} for d, s in st.session_state.stats.items()]
    st.dataframe(pd.DataFrame(pos_data), use_container_width=True)

# 頁面 5：趨勢圖
with tab_chart:
    rh = [{"場次": pt["race"], "車手": d, "實力分數": pt["val"]} for d, s in st.session_state.stats.items() for pt in s['rating_history'] if pt["race"] > 0]
    if rh:
        st.plotly_chart(px.line(pd.DataFrame(rh), x="場次", y="實力分數", color="車手", title="車手動態評級走勢"), use_container_width=True)

# --- 頁尾：備份代碼 ---
st.divider()
st.subheader("💾 本地備份代碼 (請複製並保存到記事本)")
st.code(json.dumps({"stats": st.session_state.stats, "race_no": st.session_state.race_no, "form_id": st.session_state.form_id}))
