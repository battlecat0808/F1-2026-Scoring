import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Pro", page_icon="🏎️", layout="wide")

# --- 初始化 ---
if "stats" not in st.session_state:
    st.session_state.stats = {d: {"team": t, "points": 0, "ranks": [], "point_history": [0], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False} 
                             for t, ds in {
                                "McLaren": ["Lando Norris", "Oscar Piastri"], "Ferrari": ["Lewis Hamilton", "Charles Leclerc"],
                                "Red Bull": ["Max Verstappen", "Isack Hadjar"], "Mercedes": ["George Russell", "Kimi Antonelli"],
                                "Aston Martin": ["Fernando Alonso", "Lance Stroll"], "Audi": ["Nico Hulkenberg", "Gabriel Bortoleto"],
                                "Williams": ["Carlos Sainz", "Alex Albon"], "Alpine": ["Pierre Gasly", "Franco Colapinto"],
                                "Racing Bulls": ["Liam Lawson", "Arvid Lindblad"], "Haas": ["Esteban Ocon", "Oliver Bearman"],
                                "APX-CTWR": ["Yuki Tsunoda", "Ethan Tan"]
                             }.items() for d in ds}
    st.session_state.race_no = 0

# --- 側邊欄 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("在此貼上存檔代碼：", height=100)
    if st.button("載入存檔"):
        try:
            data = json.loads(backup_input); st.session_state.stats = data["stats"]; st.session_state.race_no = data["race_no"]
            st.success("讀取成功！"); st.rerun()
        except: st.error("格式錯誤")
    if st.button("🚨 重置全賽季"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- 主程式 ---
st.title(f"🏎️ 2026 F1 賽季 - 當前第 {st.session_state.race_no} 場結束")
tabs = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📈 趨勢圖"])

with tabs[0]:
    st.subheader(f"📝 輸入第 {st.session_state.race_no + 1} 場成績")
    r_type = st.radio("類型：", ["正賽", "衝刺賽"], horizontal=True)
    
    # 判定 Top 10
    top_10 = set(sorted(st.session_state.stats.keys(), key=lambda x: (st.session_state.stats[x]['points'], st.session_state.stats[x]['p1']), reverse=True)[:10])

    with st.form("race_form"):
        cols = st.columns(3)
        inputs = {d: st.text_input(d, key=f"f_{d}_{st.session_state.race_no}", placeholder="1-22 / R") for d in st.session_state.stats.keys()}
        if st.form_submit_button("確認提交"):
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
            
            if err or len(processed) < 22: st.error("排名錯誤或有漏填！")
            else:
                st.session_state.race_no += 1
                sorted_res = sorted(processed.items(), key=lambda x: 99 if x[1]=='DNF' else x[1])
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                
                for d, r in sorted_res:
                    s = st.session_state.stats[d]
                    if r == 'DNF':
                        s["ranks"].append(25) # DNF 記錄為 25 區隔 22 名
                        s["dnf"] += 1
                        if s["dnf"] % 5 == 0: s["penalty_next"] = True
                        p = 0
                    else:
                        s["ranks"].append(r)
                        if r==1: s["p1"]+=1
                        elif r==2: s["p2"]+=1
                        elif r==3: s["p3"]+=1
                        p = 0
                        if r_type == "衝刺賽":
                            p = ({1:5,2:3,3:1}.get(r,0) + ({1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1}.get(r,0) if d not in top_10 else 0))
                        elif pts_pool and r <= 10:
                            if s["penalty_next"]: s["penalty_next"] = False
                            else: p = pts_pool.pop(0)
                    s["points"] += p
                    s["point_history"].append(s["points"])
                st.rerun()

with tabs[1]:
    d_sort = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1'], x[1]['p2'], x[1]['p3'], -sum(x[1]['ranks'])/len(x[1]['ranks']) if x[1]['ranks'] else 0), reverse=True)
    st.dataframe(pd.DataFrame([[i+1, n, s['team'], s['points'], f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf'], round(sum(s['ranks'])/len(s['ranks']),1) if s['ranks'] else "-"] for i, (n, s) in enumerate(d_sort)], columns=["排名","車手","車隊","積分","P1/2/3","DNF","Avg"]), use_container_width=True, hide_index=True)

with tabs[2]:
    t_pts = {}
    for d, s in st.session_state.stats.items(): t_pts[s['team']] = t_pts.get(s['team'], 0) + s['points']
    st.dataframe(pd.DataFrame([[i+1, t, p] for i, (t, p) in enumerate(sorted(t_pts.items(), key=lambda x: x[1], reverse=True))], columns=["排名","車隊","總分"]), use_container_width=True, hide_index=True)

with tabs[3]:
    if st.session_state.race_no > 0:
        h_data = [{"Race": i, "Driver": d, "Points": p} for d, s in st.session_state.stats.items() for i, p in enumerate(s['point_history'])]
        st.plotly_chart(px.line(pd.DataFrame(h_data), x="Race", y="Points", color="Driver", markers=True, template="plotly_dark", height=600), use_container_width=True)
    else: st.info("尚無數據")

st.divider()
st.code(json.dumps({"stats": st.session_state.stats, "race_no": st.session_state.race_no}))
