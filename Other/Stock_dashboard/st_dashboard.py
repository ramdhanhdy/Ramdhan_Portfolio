import streamlit as st
import pandas as pd
import numpy as np
import requests
import tweepy
import config
import psycopg2, psycopg2.extras
import plotly.graph_objects as go

# Connect to twitter API
auth = tweepy.OAuthHandler(config.TWITTER_CONSUMER_KEY, config.TWITTER_CONSUMER_SECRET)
auth.set_access_token(config.TWITTER_ACCESS_TOKEN, config.TWITTER_ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

# Connect to database
# connection = psycopg2.connect(host=config.DB_HOST, database=config.DB_NAME, user=config.DB_USER, password=config.DB_PASS)
# cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

# create sidebar widget
option = st.sidebar.selectbox("Which Dashboard?", ('twitter', 'wallstreetbets', 'stockwits', 'chart', 'pattern'), 3)

st.header(option)

# 1.Twitter Dashboard
if option == 'twitter':
    for username in config.TWITTER_USERNAMES:
        user = api.get_user(username)
        tweets = ap.user_timeline(username)

        st.subheader(username)
        st.image(user.profile_image_url)

        for tweet in tweets:
            if '$' in tweet.text:
                words = tweet.text.split(' ')

                #extract stock symbol from tweets
                for word in words:
                    if word.startswith('$') and word[1:].isalpha():
                        symbol = word[1:]
                        st.write(symbol)
                        st.write(tweet.text)
                        st.image(f"https://charts2.finviz.com/chart.ashx?t={symbol}")
           
# 2.Chart Dashboard
if option == 'chart':
    symbol = st.sidebar.text_input("Symbol", value='MSFT', max_chars=None, key=None, type='default')

    data = pd.read_sql("""
        select date(day) as day, open, high, low, close
        from daily_bars
        where stock_id = (select id from stock where UPPER(symbol) = %s) 
        order by day asc""", connection, params=(symbol.upper(),))

    st.subheader(symbol.upper())

    fig = go.Figure(data=[go.Candlestick(x=data['day'],
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name=symbol)])

    fig.update_xaxes(type='category')
    fig.update_layout(height=700)

    st.plotly_chart(fig, use_container_width=True)

    st.write(data)

# 3.Wallstreetbets Dashboard
if option == 'wallstreetbets':
    st.subheader("wallstreetbets")
    
    #slider to adjust num days
    num_days - st.sidebar.slider('Number of days', 1, 30, 3) #min=1, max=30, default=3
    
    cursor.execute("""
        SELECT COUNT(*) AS num_mentions, symbol
        FROM mention JOIN stock ON stock.id = mention.stock_id
        WHERE date(dt) > current_date - interval '%s day'
        GROUP BY stock_id, symbol
        HAVING COUNT(symbol) > 10
        ORDER BY num_mentions DESC
    """, (num_days,))

    counts = cursor.fetchall()
    for count in counts:
        st.write(count)

    cursor.execute("""
    SELECT symbol, message, url, dt, username
    FROM mention JOIN stock ON stock.id = mention.stock_id WHEREORDER BY dt DESC
    LIMIT 100
    """)

    mentions = cursor.fetchall()
    for mention in mentions:
        st.text(mention['dt'])
        st.text(mention['symbol'])
        st.text(mention['message'])
        st.text(mention['url'])
        st.text(mention['username'])

    rows = cursor.fetchall()
    
    st.write(rows)

# 4.Pattern-detection Dashboard
if option == 'pattern':
    pattern = st.sidebar.selectbox(
        "Which Pattern?",
        ("engulfing", "threebar")
    )

    # detect bullish engulfing pattern
    if pattern == 'engulfing':
        cursor.execute("""
            SELECT * 
            FROM ( 
                SELECT day, open, close, stock_id, symbol, 
                LAG(close, 1) OVER ( PARTITION BY stock_id ORDER BY day ) previous_close, 
                LAG(open, 1) OVER ( PARTITION BY stock_id ORDER BY day ) previous_open 
                FROM daily_bars
                JOIN stock ON stock.id = daily_bars.stock_id
            ) a 
            WHERE previous_close < previous_open AND close > previous_open AND open < previous_close
            AND day = '2021-02-18'
        """)
    # detect three bar pattern
    if pattern == 'threebar':
        cursor.execute("""
            SELECT * 
            FROM ( 
                SELECT day, close, volume, stock_id, symbol, 
                LAG(close, 1) OVER ( PARTITION BY stock_id ORDER BY day ) previous_close, 
                LAG(volume, 1) OVER ( PARTITION BY stock_id ORDER BY day ) previous_volume, 
                LAG(close, 2) OVER ( PARTITION BY stock_id ORDER BY day ) previous_previous_close, 
                LAG(volume, 2) OVER ( PARTITION BY stock_id ORDER BY day ) previous_previous_volume, 
                LAG(close, 3) OVER ( PARTITION BY stock_id ORDER BY day ) previous_previous_previous_close, 
                LAG(volume, 3) OVER ( PARTITION BY stock_id ORDER BY day ) previous_previous_previous_volume 
            FROM daily_bars 
            JOIN stock ON stock.id = daily_bars.stock_id) a 
            WHERE close > previous_previous_previous_close 
                AND previous_close < previous_previous_close 
                AND previous_close < previous_previous_previous_close 
                AND volume > previous_volume 
                AND previous_volume < previous_previous_volume 
                AND previous_previous_volume < previous_previous_previous_volume 
                AND day = '2021-02-19'
        """)

    rows = cursor.fetchall()

    for row in rows:
        st.image(f"https://finviz.com/chart.ashx?t={row['symbol']}")



# 5. Stocktwits Dashboard
if option == 'stockwits':
    symbol = st.sidebar.text_input("Stock Name", value='AAPL', max_chars=5)

    #return all recent mentions of stock from stocktwits API
    r = requests.get(f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json")

    data = r.json()
    for messages in data['messages']:
        st.image(messages['user']['avatar_url'])
        st.write(messages['user']['username'])
        st.write(messages['body'])
        st.write(messages['created_at'])