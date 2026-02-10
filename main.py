import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(page_title="2026 F1 Scoring Ultimate", page_icon="🏎️", layout="wide")

# --- 1. 核心設定 ---
TEAM_CONFIG = {
    "McLaren": {"color": "#FF8700", "drivers": {"Lando Norris": "1", "Oscar Piastri": "81"}},
    "Ferrari": {"color": "#E80020", "drivers": {"Lewis Hamilton": "44", "Charles Leclerc": "16"}},
    "Red Bull": {"color": "#3671C6", "drivers": {"Max Verstappen": "3", "Isack Hadjar": "66"}},
    "Mercedes": {"color": "#27F4D2", "drivers": {"George Russell": "63", "Kimi Antonelli": "12"}},
    "Aston Martin": {"color": "#229971", "drivers": {"Fernando Alonso": "14", "Lance Stroll": "18"}},
    "Audi": {"color": "#F50A20", "drivers": {"Nico Hulkenberg": "27", "Ethan Tan": "9"}},
    "Williams": {"color": "#64C4FF", "drivers": {"Carlos Sainz": "55", "Alex Albon": "23"}},
    "Alpine": {"color": "#0093CC", "drivers": {"Pierre Gasly": "10", "Franco Colapinto": "43"}},
    "Racing Bulls": {"color": "#6692FF", "drivers": {"Liam Lawson": "30", "Arvid Lindblad": "17"}},
    "Haas": {"color": "#B6BABD", "drivers": {"Esteban Ocon": "31", "Oliver Bearman": "87"}},
    "APX-CTWR": {"color": "#000000", "drivers": {"Yuki Tsunoda": "22", "Zhou Guanyu": "24"}}
}

# --- 2. 初始化 ---
if "stats" not in st.session_state:
    st.session_state.stats = {d: {"no": c, "team": t, "points": 0, "ranks": [], "point_history": [{"race": 0, "pts": 0}], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False, "prev_rank": 0} 
                             for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
    st.session_state.team_history = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
    st.session_state.team_prev_rank = {t: 0 for t in TEAM_CONFIG.keys()}
    st.session_state.race_no = 0
    st.session_state.form_id = 0

# --- 3. 側邊欄 ---
with st.sidebar:
    st.header("💾 數據管理")
    backup_input = st.text_area("貼入精簡存檔代碼：", height=100)
    
   if st.button("載入並重建賽季"):
        try:
            raw = json.loads(backup_input)
            # 1. 重置基礎狀態
            st.session_state.race_no = raw["race_no"]
            st.session_state.sprint_history = raw.get("sprints", [])
            
            # 2. 初始化車手與車隊字典
            new_stats = {d: {"no": c, "team": t, "points": 0, "ranks": [], "point_history": [{"race": 0, "pts": 0}], "p1": 0, "p2": 0, "p3": 0, "dnf": 0, "penalty_next": False, "prev_rank": 0} 
                         for t, cfg in TEAM_CONFIG.items() for d, c in cfg["drivers"].items()}
            new_team_history = {t: [{"race": 0, "pts": 0}] for t in TEAM_CONFIG.keys()}
            
            # 3. 按場次重新模擬計算
            pts_map = {1:25, 2:18, 3:15, 4:12, 5:10, 6:8, 7:6, 8:4, 9:2, 10:1}
            
            for i in range(1, st.session_state.race_no + 1):
                # --- A. 處理該場之前的衝刺賽 ---
                for sp in st.session_state.sprint_history:
                    if sp["race_after"] == (i - 0.5):
                        for d, p in sp["results"].items():
                            if d in new_stats: new_stats[d]["points"] += p
                
                # --- B. 處理正賽積分與統計 ---
                for d, r_list in raw["data"].items():
                    if d in new_stats and len(r_list) >= i:
                        r = r_list[i-1]
                        s = new_stats[d]
                        s["ranks"].append(r)
                        if r == 'R': 
                            s["dnf"] += 1
                        else:
                            if r == 1: s["p1"] += 1
                            elif r == 2: s["p2"] += 1
                            elif r == 3: s["p3"] += 1
                            s["points"] += pts_map.get(r, 0)
                        s["point_history"].append({"race": i, "pts": s["points"]})

                # --- C. 每場正賽結束後，紀錄當下的車隊總分 (重建車隊趨勢) ---
                for t in TEAM_CONFIG.keys():
                    t_sum = sum(s["points"] for d, s in new_stats.items() if s["team"] == t)
                    new_team_history[t].append({"race": i, "pts": t_sum})

            st.session_state.stats = new_stats
            st.session_state.team_history = new_team_history
            st.success("賽季、車隊趨勢與衝刺賽記錄已完美重建！"); st.rerun()
        except Exception as e:
            st.error(f"解析失敗: {e}")
# --- 4. 主程式 ---
st.title(f"🏎️ 2026 F1 賽季 (第 {st.session_state.race_no+1} 週)")
tab_input, tab_wdc, tab_wcc, tab_pos, tab_chart = st.tabs(["🏁 成績輸入", "👤 車手榜", "🏎️ 車隊榜", "📊 完賽位置", "📈 數據圖表"])

with tab_input:
    r_type = st.radio("本場類型：", ["正賽", "衝刺賽"], horizontal=True)
    # 獲取當前車手榜排序 (用於衝刺賽 bonus 計算)
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
                # 紀錄賽前排名
                for i, name in enumerate(wdc_order, 1): st.session_state.stats[name]["prev_rank"] = i
                t_now = sorted(TEAM_CONFIG.keys(), key=lambda x: sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == x), reverse=True)
                for i, t_name in enumerate(t_now, 1): st.session_state.team_prev_rank[t_name] = i
                st.session_state.race_no += 1
            
            curr_mark = st.session_state.race_no if r_type == "正賽" else st.session_state.race_no + 0.5
            sorted_res = sorted(processed.items(), key=lambda x: 99 if x[1]=='R' else x[1])

            if r_type == "正賽":
                pts_pool = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
                for d, r in processed.items():
                    s = st.session_state.stats[d]
                    p = 0
                    s["ranks"].append(r)
                    if r == 'R':
                        s["dnf"] += 1
                        if s["dnf"] % 5 == 0: s["penalty_next"] = True
                    else:
                # --- 衝刺賽規則 ---
                sprint_pts = {d: 0 for d in st.session_state.stats.keys()}
                # (中間原有的 sprint_pts 計算邏輯不變...)
                
                # 關鍵修正：將本次結果存入歷史，否則導出會不見
                new_sprint_record = {
                    "race_after": st.session_state.race_no + 0.5,
                    "results": sprint_pts
                }
                if "sprint_history" not in st.session_state:
                    st.session_state.sprint_history = []
                st.session_state.sprint_history.append(new_sprint_record)

                # 更新個人點位歷史
                for d, p in sprint_pts.items():
                    st.session_state.stats[d]["points"] += p
                    st.session_state.stats[d]["point_history"].append({"race": st.session_state.race_no + 0.5, "pts": st.session_state.stats[d]["points"]})
            else:
                # Sprint 規則：前三名 5-3-1，後 12 名扣除 Top 10 後發放 8-1
                sprint_pts = {d: 0 for d in st.session_state.stats.keys()}
                for d, r in processed.items():
                    if r != 'R': sprint_pts[d] += {1: 5, 2: 3, 3: 1}.get(r, 0)
                
                non_top_10 = [(d, r) for d, r in processed.items() if d not in top_10_names and r != 'R']
                non_top_10.sort(key=lambda x: x[1])
                bonus = [8, 7, 6, 5, 4, 3, 2, 1]
                for d, r in non_top_10:
                    if bonus: sprint_pts[d] += bonus.pop(0)
                
                for d, p in sprint_pts.items():
                    st.session_state.stats[d]["points"] += p
                    st.session_state.stats[d]["point_history"].append({"race": curr_mark, "pts": st.session_state.stats[d]["points"]})

            # 更新車隊歷史
            for t in TEAM_CONFIG.keys():
                t_sum = sum(s["points"] for d, s in st.session_state.stats.items() if s["team"] == t)
                st.session_state.team_history[t].append({"race": curr_mark, "pts": t_sum})
            
            st.session_state.form_id += 1
            st.rerun()

# --- 5. 榜單顯示 ---
with tab_wdc:
    def get_avg_pos(ranks):
        if not ranks: return 99.0  # 無數據時給一個極大值
        processed = [r if isinstance(r, int) else 25 for r in ranks]
        return round(sum(processed) / len(processed), 2)

    # 排序邏輯：積分 > P1 > P2 > P3 > 平均名次(負號處理)
    d_sort = sorted(
        st.session_state.stats.items(), 
        key=lambda x: (
            x[1]['points'], 
            x[1]['p1'], 
            x[1]['p2'], 
            x[1]['p3'], 
            -get_avg_pos(x[1]["ranks"]) # 負負得正，讓平均名次小的排前面
        ), 
        reverse=True
    )
    
    d_data = []
    for i, (n, s) in enumerate(d_sort, 1):
        trend = ""
        if st.session_state.race_no >= 1 and s['prev_rank'] != 0:
            diff = s['prev_rank'] - i
            trend = f"🔼 {diff}" if diff > 0 else f"🔽 {abs(diff)}" if diff < 0 else "➖"
        
        avg_p = get_avg_pos(s["ranks"])
        d_data.append([
            trend, i, s['no'], n, s['team'], s['points'], 
            avg_p if avg_p != 99.0 else "N/A", 
            f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf']
        ])
    st.dataframe(pd.DataFrame(d_data, columns=["趨勢","排名","#","車手","車隊","積分","平均名次","P1/P2/P3","DNF"]), use_container_width=True, hide_index=True)

with tab_wcc:
    t_list = []
    for t in TEAM_CONFIG.keys():
        ds = [s for d, s in st.session_state.stats.items() if s["team"] == t]
        all_ranks = []
        for d_s in ds: 
            all_ranks.extend([r if isinstance(r, int) else 25 for r in d_s["ranks"]])
        
        avg_val = sum(all_ranks)/len(all_ranks) if all_ranks else 99.0
        t_list.append({
            "team": t, 
            "pts": sum(d["points"] for d in ds), 
            "p1": sum(d["p1"] for d in ds), 
            "p2": sum(d["p2"] for d in ds), 
            "p3": sum(d["p3"] for d in ds), 
            "avg": avg_val
        })
    
    # 排序邏輯：同車手榜
    t_sort = sorted(
        t_list, 
        key=lambda x: (x["pts"], x["p1"], x["p2"], x["p3"], -x["avg"]), 
        reverse=True
    )
    
    t_rows = []
    for i, t in enumerate(t_sort, 1):
        prev = st.session_state.team_prev_rank.get(t['team'], 0)
        trend = (f"🔼 {prev-i}" if prev-i > 0 else f"🔽 {i-prev}" if prev-i < 0 else "➖") if st.session_state.race_no >= 1 and prev != 0 else ""
        t_rows.append([
            trend, i, t["team"], t["pts"], 
            round(t["avg"], 2) if t["avg"] != 99.0 else "N/A", 
            f"{t['p1']}/{t['p2']}/{t['p3']}"
        ])
    st.dataframe(pd.DataFrame(t_rows, columns=["趨勢","排名","車隊","總積分","平均名次","P1/P2/P3"]), use_container_width=True, hide_index=True)
# --- 完賽位置表 ---
with tab_pos:
    if st.session_state.race_no > 0:
        pos_data = []
        sorted_drivers = sorted(st.session_state.stats.keys(), key=lambda x: st.session_state.stats[x]['points'], reverse=True)
        for d in sorted_drivers:
            s = st.session_state.stats[d]
            row = {"車手": d, "車隊": s['team']}
            for i, r in enumerate(s["ranks"], 1):
                row[f"Rd.{i}"] = 25 if r == 'R' else r
            pos_data.append(row)
        df_pos = pd.DataFrame(pos_data)

        def style_ranks_text(val):
            if not isinstance(val, (int, float)): return ''
            if val == 25: return 'color: #FF4B4B; font-weight: bold'
            if val == 1: return 'color: #D4AF37; font-weight: bold'
            if val == 2: return 'color: #808080; font-weight: bold'
            if val == 3: return 'color: #CD7F32; font-weight: bold'
            if 4 <= val <= 10: return 'color: #28a745; font-weight: bold'
            return 'color: #E5B800; font-weight: normal'

        rd_cols = [c for c in df_pos.columns if c.startswith("Rd.")]
        st.dataframe(df_pos.style.applymap(style_ranks_text, subset=rd_cols), use_container_width=True, hide_index=True)
    else:
        st.info("尚無正賽數據。")

# --- 圖表 ---
with tab_chart:
    if st.session_state.race_no > 0:
        dh = [{"Race": pt["race"], "Driver": f"#{s['no']} {d}", "Points": pt["pts"]} for d, s in st.session_state.stats.items() for pt in s['point_history']]
        st.plotly_chart(px.line(pd.DataFrame(dh), x="Race", y="Points", color="Driver", markers=True, color_discrete_map={f"#{s['no']} {d}": TEAM_CONFIG[s['team']]['color'] for d, s in st.session_state.stats.items()}, template="plotly_dark", title="車手積分趨勢"), use_container_width=True)
        
        th = [{"Race": pt["race"], "Team": t, "Points": pt["pts"]} for t, h in st.session_state.team_history.items() for pt in h]
        st.plotly_chart(px.line(pd.DataFrame(th), x="Race", y="Points", color="Team", markers=True, color_discrete_map={t: cfg["color"] for t, cfg in TEAM_CONFIG.items()}, template="plotly_dark", title="車隊積分趨勢"), use_container_width=True)

# --- 6. 導出存檔 ---
# 只抓取車手名次，不抓取顏色、名字等重複資訊
compact_data = {
    "race_no": st.session_state.race_no,
    "sprints": st.session_state.get("sprint_history", []),
    "data": {d: s["ranks"] for d, s in st.session_state.stats.items()}
}
st.divider()
st.subheader("📦 壓縮存檔代碼 (精簡版)")
st.code(json.dumps(compact_data))
