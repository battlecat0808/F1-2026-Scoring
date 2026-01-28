# --- 這裡接在 st.rerun() 之後 ---

with tab_driver:
    st.subheader("👤 車手年度積分榜 (WDC)")
    # 排序邏輯：總分 > P1 > P2 > P3 > 平均完賽排名
    d_sort = sorted(st.session_state.stats.items(), key=lambda x: (x[1]['points'], x[1]['p1'], x[1]['p2'], x[1]['p3'], -sum(x[1]['ranks'])/len(x[1]['ranks']) if x[1]['ranks'] else 0), reverse=True)
    
    d_df = pd.DataFrame([
        [i+1, n, s['team'], s['points'], f"{s['p1']}/{s['p2']}/{s['p3']}", s['dnf'], round(sum(s['ranks'])/len(s['ranks']),1) if s['ranks'] else "-"]
        for i, (n, s) in enumerate(d_sort)
    ], columns=["排名", "車手", "車隊", "積分", "P1/2/3", "DNF", "平均完賽"])
    st.dataframe(d_df, use_container_width=True, hide_index=True) # 改用 dataframe 比較美觀

with tab_team:
    st.subheader("🏎️ 車隊年度積分榜 (WCC)")
    t_points = {}
    for d, s in st.session_state.stats.items():
        t_points[s['team']] = t_points.get(s['team'], 0) + s['points']
    t_sort = sorted(t_points.items(), key=lambda x: x[1], reverse=True)
    t_df = pd.DataFrame([[i+1, t, p] for i, (t, p) in enumerate(t_sort)], columns=["排名", "車隊", "總積分"])
    st.dataframe(t_df, use_container_width=True, hide_index=True)

with tab_chart:
    st.subheader("📈 賽季積分增長趨勢")
    if st.session_state.race_no == 0:
        st.info("目前尚無比賽數據，請先輸入第一場成績。")
    else:
        chart_data = []
        for d, s in st.session_state.stats.items():
            for i, p in enumerate(s['point_history']):
                chart_data.append({"場次": i, "車手": d, "積分": p, "車隊": s['team']})
        
        if chart_data:
            df_plot = pd.DataFrame(chart_data)
            # 建立圖表
            fig = px.line(df_plot, x="場次", y="積分", color="車手", markers=True, 
                         hover_data=["車隊"], template="plotly_dark", height=600)
            
            # 優化圖表外觀
            fig.update_layout(xaxis_title="比賽場次 (0為賽季前)", yaxis_title="累積總積分")
            st.plotly_chart(fig, use_container_width=True)

# --- 存檔代碼區 ---
st.divider()
st.write("### 🔑 本次更新後的存檔代碼 (請複製保存)")
save_code = json.dumps({"stats": st.session_state.stats, "race_no": st.session_state.race_no})
st.code(save_code)
