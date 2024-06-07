import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objs as go
from ta import add_all_ta_features
from ta.utils import dropna
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Mapping for intervals to CryptoCompare API
INTERVALS = {
    '1m': 'histominute',
    '5m': 'histominute',
    '15m': 'histominute',
    '1h': 'histohour',
    '1d': 'histoday'
}

# Function to fetch crypto data from CryptoCompare
def fetch_crypto_data(symbol, interval, api_key):
    try:
        url = f'https://min-api.cryptocompare.com/data/v2/{INTERVALS[interval]}?fsym={symbol}&tsym=USDT&limit=60&aggregate=1&e=CCCAGG&api_key={api_key}'
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()['Data']['Data']
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.rename(columns={'time': 'timestamp', 'volumefrom': 'volume'}, inplace=True)
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        logging.info(f'Data fetched successfully for {symbol} from CryptoCompare')
        return df
    except requests.exceptions.RequestException as e:
        logging.error(f'Error fetching data from CryptoCompare: {e}')
        st.error(f'Error fetching data from CryptoCompare: {e}')
        return pd.DataFrame()

# Function to check for data errors
def check_data_errors(df):
    if df.empty:
        logging.error('Dataframe is empty')
        return 'Dataframe is empty'
    if df.isnull().values.any():
        logging.error('Data contains null values')
        return 'Data contains null values'
    if df.duplicated().any():
        logging.error('Data contains duplicates')
        return 'Data contains duplicates'
    return 'No errors found'

# Function to calculate technical indicators
def calculate_technical_indicators(df):
    df = dropna(df)
    df = add_all_ta_features(
        df, open="open", high="high", low="low", close="close", volume="volume", fillna=True)
    return df

# Function to plot candlestick chart with indicators
def plot_candlestick_with_indicators(df, symbol):
    fig = go.Figure(data=[go.Candlestick(x=df['timestamp'],
                    open=df['open'], high=df['high'],
                    low=df['low'], close=df['close'], name='Candlesticks')])

    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['trend_sma_fast'], mode='lines', name='SMA Fast'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['trend_sma_slow'], mode='lines', name='SMA Slow'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['momentum_rsi'], mode='lines', name='RSI'))

    fig.update_layout(title=f'Candlestick chart with Indicators for {symbol}', xaxis_title='Time', yaxis_title='Price')
    return fig

# Function to build and train LSTM model
def build_lstm_model(df):
    data = df['close'].values.reshape(-1, 1)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)
    X, y = [], []
    for i in range(60, len(scaled_data)):
        X.append(scaled_data[i-60:i, 0])
        y.append(scaled_data[i, 0])
    X, y = np.array(X), np.array(y)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    
    model = Sequential()
    model.add(LSTM(units=50, return_sequences=True, input_shape=(X.shape[1], 1)))
    model.add(Dropout(0.2))
    model.add(LSTM(units=50, return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(units=1))
    
    model.compile(optimizer='adam', loss='mean_squared_error')
    model.fit(X, y, epochs=25, batch_size=32)
    
    return model, scaler

# Streamlit app
st.title('بيانات العملات الرقمية مع المؤشرات الفنية')
symbol = st.text_input('رمز العملة الرقمية', 'BTC')
interval = st.selectbox('الفاصل الزمني', ['1m', '5m', '15m', '1h', '1d'])
api_key = st.text_input('Enter your CryptoCompare API key')

if st.button('جلب البيانات'):
    df = fetch_crypto_data(symbol, interval, api_key)
    error = check_data_errors(df)
    if error == 'No errors found':
        df = calculate_technical_indicators(df)
        df['current_price'] = df['close']
        st.write(f'Current price: {df["current_price"].iloc[-1]} USDT')
        st.plotly_chart(plot_candlestick_with_indicators(df, symbol))
        st.dataframe(df)
        
        if st.button('Train LSTM Model'):
            model, scaler = build_lstm_model(df)
            st.success('Model trained successfully')

        if st.button('Download Data'):
            df.to_csv(f'{symbol}_data.csv', index=False)
            st.success('Data downloaded successfully')
    else:
        st.error(f'Data error: {error}')

# Add an automatic update feature
def auto_update(symbol, interval, api_key, update_interval=1):
    df_placeholder = st.empty()
    chart_placeholder = st.empty()
    price_placeholder = st.empty()
    
    while True:
        df = fetch_crypto_data(symbol, interval, api_key)
        error = check_data_errors(df)
        if error == 'No errors found':
            df = calculate_technical_indicators(df)
            df['current_price'] = df['close']
            price_placeholder.write(f'Current price: {df["current_price"].iloc[-1]} USDT')
            chart_placeholder.plotly_chart(plot_candlestick_with_indicators(df, symbol))
            df_placeholder.dataframe(df)
        else:
            price_placeholder.error(f'Data error: {error}')
        time.sleep(update_interval)

# Option to start automatic updates
if st.button('Start Auto Updates'):
    auto_update(symbol, interval, api_key)
