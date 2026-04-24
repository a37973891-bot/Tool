import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
from FinMind.data import DataLoader
import pandas_ta as ta

# --- 網頁基礎設定 ---
st.set_page_config(page_title="台股籌碼 K 線專業旗艦版", layout="wide")
api = DataLoader()

# ==========================================
# 🚀 效能與資料核心
# ==========================================
@st.cache_data(ttl=3600) 
def get_card_data(stock_id):
    """取得卡片用的摘要數據：現價、漲跌、主力氣象 (四段位)"""
    try:
        df = api.taiwan_stock_daily(stock_id=stock_id, 
                                    start_date=(datetime.date.today()-datetime.timedelta(days=15)).strftime("%Y-%m-%d"), 
                                    end_date=datetime.date.today().strftime("%Y-%m-%d"))
        if df.empty: return None
        now = round(df['close'].iloc[-1], 2)
        prev = round(df['close'].iloc[-2], 2)
        diff = round(now - prev, 2)
        percent = round((diff / prev) * 100, 2)
        vol_now = df['Trading_Volume'].iloc[-1]
        vol_ma5 = df['Trading_Volume'].rolling(5).mean().iloc[-1]
        vol_ratio = vol_now / vol_ma5
        if vol_ratio > 1.2:
            status, icon = ("大買", "☀️") if diff > 0 else ("大賣", "🌧️")
        elif 0.8 <= vol_ratio <= 1.2:
            status, icon = ("小買", "⛅") if diff > 0 else ("小賣", "⛈️")
        else:
            status, icon = "震盪", "☁️"
        return {"price": now, "diff": diff, "percent": percent, "status": status, "icon": icon, "vol_ratio": round(vol_ratio, 2)}
    except: return None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_main_data(stock_id):
    df_raw = api.taiwan_stock_daily(stock_id=stock_id, start_date="2000-01-01", end_date=datetime.date.today().strftime("%Y-%m-%d"))
    df_inst_raw = pd.DataFrame()
    if stock_id != "TAIEX":
        df_inst_raw = api.taiwan_stock_institutional_investors(stock_id=stock_id, 
                                                              start_date=(datetime.date.today()-datetime.timedelta(days=1095)).strftime("%Y-%m-%d"), 
                                                              end_date=datetime.date.today().strftime("%Y-%m-%d"))
    return df_raw, df_inst_raw

# ==========================================
# 📁 強化版清單管理系統
# ==========================================
def init_session():
    if 'group_names' not in st.session_state:
        st.session_state.group_names = {f"group_{i}": f"自選股清單 {i}" for i in range(1, 6)}
    if 'group_data' not in st.session_state:
        st.session_state.group_data = {f"group_{i}": ["2330", "0050", "00878"] if i==1 else [] for i in range(1, 6)}
    if 'current_stock_id' not in st.session_state:
        st.session_state.current_stock_id = "2330"
    if 'view_mode_val' not in st.session_state:
        st.session_state.view_mode_val = "詳細圖表分析"
    if 'is_descending' not in st.session_state:
        st.session_state.is_descending = True

init_session()

def on_group_change():
    new_group = st.session_state.group_selector
    new_list = st.session_state.group_data[new_group]
    if new_list:
        st.session_state.current_stock_id = new_list[0]
        st.session_state.manual_input_val = ""

def sync_fav_to_main():
    if st.session_state.fav_selection:
        st.session_state.current_stock_id = st.session_state.fav_selection
        st.session_state.manual_input_val = ""

def handle_search():
    if st.session_state.manual_input_val:
        st.session_state.current_stock_id = st.session_state.manual_input_val
        st.session_state.view_mode_val = "詳細圖表分析"
        st.session_state.fav_selection = None

def toggle_order():
    st.session_state.is_descending = not st.session_state.is_descending

# --- 側邊欄 ---
st.sidebar.header("📂 帳號自選管理")
with st.sidebar.expander("✏️ 修改清單名稱"):
    for g_id in st.session_state.group_names:
        st.session_state.group_names[g_id] = st.text_input(f"清單 {g_id[-1]}", st.session_state.group_names[g_id], key=f"rename_{g_id}")

current_g_id = st.sidebar.selectbox("📅 當前清單", list(st.session_state.group_names.keys()), format_func=lambda x: st.session_state.group_names[x], key="group_selector", on_change=on_group_change)
st.sidebar.radio("🔭 視角切換", ["詳細圖表分析", "清單卡片總覽"], key="view_mode_val", horizontal=True)

sort_type = st.sidebar.selectbox("⭐ 排序基準", ["加入時間", "代碼排序", "價格排序"])
order_label = "目前：高至低 ↓" if st.session_state.is_descending else "目前：低至高 ↑"
st.sidebar.button(order_label, on_click=toggle_order, use_container_width=True)

fav_list = st.session_state.group_data[current_g_id].copy()
if sort_type == "代碼排序": fav_list.sort(reverse=st.session_state.is_descending)
elif sort_type == "價格排序":
    @st.cache_data(ttl=600)
    def get_price_for_sort(sid):
        p = get_card_data(sid)
        return p['price'] if p else 0
    fav_list.sort(key=get_price_for_sort, reverse=st.session_state.is_descending)
elif sort_type == "加入時間":
    if st.session_state.is_descending: fav_list = fav_list[::-1]

st.sidebar.selectbox("🎯 選擇清單內標的", fav_list, key="fav_selection", on_change=sync_fav_to_main)
st.sidebar.text_input("🔍 手動輸入代碼", key="manual_input_val")
st.sidebar.button("🚀 查看此股 / 搜尋", use_container_width=True, on_click=handle_search)

stock_id = st.session_state.current_stock_id

st.sidebar.write("---")
target_add_group = st.sidebar.selectbox("加入至哪個清單？", list(st.session_state.group_names.keys()), format_func=lambda x: st.session_state.group_names[x])
col_a, col_r = st.sidebar.columns(2)
if col_a.button("❤️ 加入", use_container_width=True):
    if stock_id not in st.session_state.group_data[target_add_group]:
        st.session_state.group_data[target_add_group].append(stock_id); st.rerun()
if col_r.button("🗑️ 移除", use_container_width=True):
    if stock_id in st.session_state.group_data[current_g_id]:
        st.session_state.group_data[current_g_id].remove(stock_id)
        rem = st.session_state.group_data[current_g_id]
        st.session_state.current_stock_id = rem[0] if rem else "TAIEX"; st.rerun()

st.sidebar.divider()
time_frame = st.sidebar.radio("📅 週期", ["日", "週", "月"], horizontal=True)
indicator = st.sidebar.selectbox("📉 副圖指標", ["成交量", "KD", "RSI", "MACD"])

# ==========================================
# 🎨 介面呈現區
# ==========================================
st.title(f"📈 {st.session_state.group_names[current_g_id]}")

if st.session_state.view_mode_val == "清單卡片總覽":
    if not fav_list: st.info("清單內尚無股票。")
    else:
        cols = st.columns(3)
        for i, sid in enumerate(fav_list):
            data = get_card_data(sid)
            with cols[i % 3]:
                if data:
                    color = "#FF3131" if data['diff'] >= 0 else "#22DD22"
                    st.markdown(f"""<div style="background-color:#1E1E1E; border-radius:10px; padding:20px; border: 1px solid #333; margin-bottom:15px">
                        <div style="display:flex; justify-content:space-between; color:#888"><span>{sid}</span><span>台股</span></div>
                        <div style="font-size:38px; color:{color}; font-weight:bold; margin:10px 0">{data['price']} <span style="font-size:16px">{'▲' if data['diff']>=0 else '▼'} {abs(data['diff'])} ({data['percent']}%)</span></div>
                        <div style="text-align:center; font-size:30px; color:{color}">{data['icon']} <span style="font-size:32px; font-weight:bold">{data['status']}</span></div>
                        <div style="text-align:right; font-size:12px; color:#555">量能比: {data['vol_ratio']}x</div></div>""", unsafe_allow_html=True)
else:
    st.subheader(f"🔍 目前觀測分析：{stock_id}")
    tabs = st.tabs(["📊 K線與指標", "🏦 法人進出", "⚡ 即時資訊", "🕵️ 主力/籌碼", "📰 相關新聞"])
    
    with tabs[0]:
        try:
            with st.spinner('數據載入中...'):
                df_raw, df_inst_raw = fetch_main_data(stock_id)
                df, df_inst = df_raw.copy(), df_inst_raw.copy()

            if not df.empty:
                df = df.rename(columns={'date': 'Date', 'open': 'Open', 'max': 'High', 'min': 'Low', 'close': 'Close', 'Trading_Volume': 'Volume'})
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)

                if not df_inst.empty and stock_id != "TAIEX":
                    df_foreign = df_inst[df_inst['name'].str.contains('外資', na=False)]
                    df_f_grouped = df_foreign.groupby('date')['buy'].sum().reset_index()
                    df_f_grouped['date'] = pd.to_datetime(df_f_grouped['date'])
                    df_f_grouped.set_index('date', inplace=True)
                    df = df.join(df_f_grouped.rename(columns={'buy': 'Foreign_Buy'}), how='left')
                df['Foreign_Buy'] = df.get('Foreign_Buy', pd.Series(0, index=df.index)).fillna(0)

                if time_frame == "週": df = df.resample('W-FRI').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum', 'Foreign_Buy': 'sum'}).dropna()
                elif time_frame == "月": df = df.resample('ME').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum', 'Foreign_Buy': 'sum'}).dropna()

                for l in [5, 10, 20, 60]: df[f'MA{l}'] = ta.sma(df['Close'], length=l)
                df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
                df['主力成本'] = ((df['Typical_Price'] * df['Volume']).rolling(20).sum() / df['Volume'].rolling(20).sum().replace(0, pd.NA)).ffill()
                df['外資成本'] = ((df['Typical_Price'] * df['Foreign_Buy']).rolling(20).sum() / df['Foreign_Buy'].rolling(20).sum().replace(0, pd.NA)).ffill()

                if indicator == "KD":
                    kd = ta.stoch(df['High'], df['Low'], df['Close'], k=9, d=3)
                    df = pd.concat([df, kd], axis=1)
                elif indicator == "RSI": df['RSI'] = ta.rsi(df['Close'], length=14)
                elif indicator == "MACD":
                    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
                    df = pd.concat([df, macd], axis=1)

                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.75, 0.25])
                hover_text = [f"日期: {d.strftime('%Y/%m/%d')}<br>收盤價: {round(c, 2)}<br>開盤價: {round(o, 2)}<br>最高點: {round(h, 2)}<br>最低點: {round(l, 2)}" for d, o, h, l, c in zip(df.index, df['Open'], df['High'], df['Low'], df['Close'])]
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線', text=hover_text, hoverinfo='text', increasing_line_color='red', decreasing_line_color='green', increasing_fillcolor='red', decreasing_fillcolor='green'), row=1, col=1)
                for m, c in zip(['MA5', 'MA10', 'MA20', 'MA60'], ['#007FFF', '#FFBF00', '#E30022', '#008000']):
                    fig.add_trace(go.Scatter(x=df.index, y=df[m], line=dict(color=c, width=1.2), name=m), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['主力成本'], line=dict(color='#00FFFF', width=2, dash='dot'), name='主力成本'), row=1, col=1)
                if '外資成本' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['外資成本'], line=dict(color='#FF00FF', width=2, dash='dot'), name='外資成本'), row=1, col=1)
                
                l_date, l_close = df.index[-1], round(df['Close'].iloc[-1], 2)
                fig.add_annotation(x=l_date, y=l_close, text=f" {l_close} ", showarrow=False, xanchor="left", bgcolor="red" if l_close >= round(df['Close'].iloc[-2], 2) else "green", font=dict(color="white", size=16, family="Arial Black"), bordercolor="white", borderwidth=1, row=1, col=1)

                if indicator == "成交量":
                    colors = ['red' if c>=o else 'green' for c,o in zip(df['Close'],df['Open'])]
                    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='成交量'), row=2, col=1)
                elif indicator == "KD":
                    fig.add_trace(go.Scatter(x=df.index, y=df['STOCHk_9_3_3'], line=dict(color='#007FFF'), name='K值'), row=2, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['STOCHd_9_3_3'], line=dict(color='#FFBF00'), name='D值'), row=2, col=1)
                elif indicator == "RSI": fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#FF00FF'), name='RSI(14)'), row=2, col=1)
                elif indicator == "MACD":
                    fig.add_trace(go.Bar(x=df.index, y=df['MACDh_12_26_9'], name='MACD柱狀'), row=2, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_12_26_9'], line=dict(color='#007FFF'), name='DIF'), row=2, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['MACDs_12_26_9'], line=dict(color='#FFBF00'), name='MACD'), row=2, col=1)

                view_days = min(60, len(df))
                recent_df = df.iloc[-view_days:]
                # 【核心修復】：確保 yaxis2 範圍永遠根據最近資料動態縮放
                y2_max = recent_df['Volume'].max() if indicator == "成交量" else df.iloc[-view_days:].filter(like='STOCH').max().max() if indicator == "KD" else 100
                if indicator == "MACD": y2_max = recent_df.filter(like='MACD').abs().max().max() * 1.5

                fig.update_layout(height=800, dragmode='pan', hovermode='x unified', hoverlabel=dict(bgcolor="white", font_size=16), margin=dict(l=70, r=80, t=80, b=20), xaxis_rangeslider_visible=False,
                                yaxis=dict(fixedrange=False, side='left', range=[recent_df['Low'].min()*0.97, recent_df['High'].max()*1.03]),
                                yaxis2=dict(fixedrange=False, side='left', range=[0, y2_max * 1.1] if indicator != "MACD" else [-y2_max, y2_max]),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.05),
                                annotations=[dict(xref='paper', yref='paper', x=0, y=0.98, text='股價', showarrow=False, font=dict(color='gray', size=14)),
                                             dict(xref='paper', yref='paper', x=0, y=0.25, text=indicator, showarrow=False, font=dict(color='gray', size=14))])
                fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], range=[df.index[-view_days], df.index[-1] + pd.Timedelta(days=5)], hoverformat="%Y/%m/%d", tickformat="%Y/%m/%d")
                st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})
                with st.expander("查看詳細歷史數據", expanded=False):
                    df_display = df[['Open','High','Low','Close','Volume']].copy()
                    df_display = df_display.rename(columns={'Open':'開盤價','High':'最高價','Low':'最低價','Close':'收盤價','Volume':'成交量'})
                    st.dataframe(df_display.round(2).sort_index(ascending=False).head(50), use_container_width=True)
        except Exception as e: st.error(f"圖表載入異常: {e}")