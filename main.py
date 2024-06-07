import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from ta import add_all_ta_features
from ta.utils import dropna
from io import BytesIO
from streamlit_option_menu import option_menu

# الترجمة اليدوية
translations = {
    "en": {
        "crypto_data_with_technical_indicators": "Crypto Data with Technical Indicators",
        "select_language": "Select Language",
        "crypto_symbol": "Crypto Symbol",
        "time_intervals": "Time Intervals",
        "fetch_data": "Fetch Data",
        "insufficient_data": "Not enough data after adding technical indicators. Please try again with a different symbol or interval.",
        "current_price": "Current Price",
        "interactive_candlestick_chart": "Interactive Candlestick Chart",
        "price_usd": "Price (USD)",
        "time": "Time",
        "technical_indicators_data": "Technical Indicators Data",
        "download_data_as_excel": "Download Data as Excel",
        "all_rights_reserved": "All rights reserved"
    },
    "ar": {
        "crypto_data_with_technical_indicators": "بيانات العملات الرقمية مع المؤشرات الفنية",
        "select_language": "اختر اللغة",
        "crypto_symbol": "رمز العملة الرقمية",
        "time_intervals": "الفواصل الزمنية",
        "fetch_data": "جلب البيانات",
        "insufficient_data": "لا توجد بيانات كافية بعد إضافة المؤشرات الفنية. يرجى المحاولة برمز أو فاصل زمني مختلف.",
        "current_price": "السعر الحالي",
        "interactive_candlestick_chart": "الشارت التفاعلي للشموع اليابانية",
        "price_usd": "السعر (USD)",
        "time": "الوقت",
        "technical_indicators_data": "بيانات المؤشرات الفنية",
        "download_data_as_excel": "تحميل البيانات كملف Excel",
        "all_rights_reserved": "جميع الحقوق محفوظة"
    }
}

def t(key, lang):
    return translations[lang].get(key, key)

def fetch_data(symbol, interval, api_key):
    base_url = 'https://min-api.cryptocompare.com/data'
    interval_map = {
        '1m': 'histominute',
        '5m': 'histominute',
        '15m': 'histominute',
        '30m': 'histominute',
        '1h': 'histohour',
        '4h': 'histohour',
        '1d': 'histoday'
    }
    limit_map = {
        '1m': 60,
        '5m': 60,
        '15m': 60,
        '30m': 60,
        '1h': 24,
        '4h': 24,
        '1d': 30
    }
    interval_value = interval_map.get(interval, 'histohour')
    limit_value = limit_map.get(interval, 60)
    url = f'{base_url}/{interval_value}?fsym={symbol}&tsym=USD&limit={limit_value}&api_key={api_key}'

    try:
        response = requests.get(url)
        if response.status_code != 200:
            st.error(f"Error fetching data: {response.status_code}")
            return pd.DataFrame()

        data = response.json()
        if "Data" not in data:
            st.error("Error fetching data from CryptoCompare API. Please check your symbol and interval.")
            return pd.DataFrame()

        candles = data['Data']
        df = pd.DataFrame(candles)
        df['timestamp'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('timestamp', inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volumefrom']]
        df.columns = ['open', 'high', 'low', 'close', 'volume']
        df = df.astype(float)

        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def add_technical_indicators(df):
    if df.empty or len(df) < 50:  # Ensure at least 50 rows are present
        return df, False
    try:
        df = dropna(df)
        df = add_all_ta_features(
            df, open="open", high="high", low="low", close="close", volume="volume")
        return df, True
    except Exception as e:
        st.error(f"Error adding technical indicators: {e}")
        return df, False

def plot_interactive_chart(df, lang):
    fig = go.Figure(data=[go.Candlestick(x=df.index,
                                         open=df['open'],
                                         high=df['high'],
                                         low=df['low'],
                                         close=df['close'])])
    fig.update_layout(
        title=t('interactive_candlestick_chart', lang),
        yaxis_title=t('price_usd', lang),
        xaxis_title=t('time', lang),
        xaxis_rangeslider_visible=False
    )
    return fig

# Set page configuration
st.set_page_config(page_title="Crypto Data with Technical Indicators")

def main():
    # Language selector
    lang = st.selectbox("Select Language / اختر اللغة", ['en', 'ar'])

    st.title(t('crypto_data_with_technical_indicators', lang))

    # List of common crypto symbols for autocomplete
    crypto_symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'XRP', 'DOT', 'LTC', 'LINK', 'DOGE']

    # Input for crypto symbol with autocomplete
    symbol = st.text_input(t('crypto_symbol', lang), placeholder='e.g., BTC')

    if symbol:
        suggestions = [s for s in crypto_symbols if s.startswith(symbol.upper())]
        if suggestions:
            selected_symbol = option_menu(
                menu_title=None,
                options=suggestions,
                icons=None,
                menu_icon="",
                default_index=0,
                orientation="horizontal"
            )
            symbol = selected_symbol

    intervals = st.multiselect(t('time_intervals', lang), ['1m', '5m', '15m', '30m', '1h', '4h', '1d'], default=['15m'])
    api_key = st.text_input("Enter your CryptoCompare API key", type="password")  # Replace with your actual API key

    if st.button(t('fetch_data', lang)):
        if not symbol:
            st.error("Please enter a valid crypto symbol.")
            return
        
        if not api_key:
            st.error("Please enter your CryptoCompare API key.")
            return
        
        all_data = []
        for interval in intervals:
            df = fetch_data(symbol, interval, api_key)
            if df.empty or len(df) < 50:  # Check if data is sufficient before adding indicators
                st.error(f"Not enough data for {symbol} with interval {interval}. Please try again with a different symbol or interval.")
                continue

            df, valid = add_technical_indicators(df)
            if not valid:
                st.error(t('insufficient_data', lang))
                continue
            df = df.sort_index(ascending=False)
            current_price = df['close'].iloc[0] if not df.empty else 0
            df['current_price'] = current_price  # Adding current price as a column
            all_data.append((interval, df))

        if all_data:
            for interval, df in all_data:
                if not df.empty:
                    st.subheader(f"{t('current_price', lang)} ({interval}): {current_price:.2f} USD")

                    fig = plot_interactive_chart(df, lang)
                    st.plotly_chart(fig)

                    st.subheader(f"{t('technical_indicators_data', lang)} ({interval})")
                    st.dataframe(df)

            with BytesIO() as buffer:
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    for interval, df in all_data:
                        if not df.empty:
                            df_reset = df.reset_index()
                            # Remove timezone information
                            df_reset['timestamp'] = df_reset['timestamp'].dt.tz_localize(None)
                            df_reset.to_excel(writer, index=False, sheet_name=interval)
                st.download_button(label=t("download_data_as_excel", lang), data=buffer, file_name=f'{symbol}.xlsx', mime='application/vnd.ms-excel')

    st.markdown(f"<div style='text-align: center;'>{t('all_rights_reserved', lang)} أحمد الحارثي</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
