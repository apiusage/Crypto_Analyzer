import streamlit as st
from db import *
import pandas as pd
import requests
import json
import pytz
from datetime import date, timedelta
import plotly.express as px
import altair as alt

def run_potentialCoin():
    st.header("Potential Coin")
    intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    columns = ["Open time", "Open", "High", "Low", "Close", "Volume", "Close time", "Quote asset volume",
               "Number of trades", "Taker buy base asset volume", "Taker buy quote asset volume", "Ignore"]

    marketpairsList = []
    dataMarketPairs = GetMarketPairs()
    for i in range(0, len(dataMarketPairs['symbols'])):
        marketpairsList.append(dataMarketPairs['symbols'][i]['symbol'])

    coinOption = st.multiselect("Select a coin", marketpairsList, default="MATICUSDT")
    intervalOption = st.select_slider('Select a interval', options=intervals, value ='1h')

    today = date.today()
    min_date = today
    max_date = today
    startEndDate = st.date_input("Pick a date", (min_date, max_date))
    sDate = startEndDate[0].strftime("%Y/%m/%d, %H:%M:%S")
    eDate = (startEndDate[1] + timedelta(days=1)).strftime("%Y/%m/%d, %H:%M:%S")

    col1, col2 = st.beta_columns(2)
    if coinOption:
        HighDF = pd.DataFrame()
        LowDF = pd.DataFrame()
        closeDF = pd.DataFrame()
        volumeDF = pd.DataFrame()
        dataJson = GetResultsJson(coinOption, intervalOption)
        for i in range(0, len(dataJson)):
            # UTC time to local time
            current_utc_time = pd.to_datetime(dataJson[i][0], unit='ms')
            date_time = current_utc_time.replace(tzinfo=pytz.utc).astimezone('Asia/Singapore')

            dayofweek = dow(date_time)
            date_time = date_time.strftime("%Y/%m/%d, %H:%M:%S")
            high = "{:.4f}".format(float(dataJson[i][2]))
            low = "{:.4f}".format(float(dataJson[i][3]))
            close = "{:.4f}".format(float(dataJson[i][4]))
            volume = "{:.0f}".format(float(dataJson[i][5]))

            HighData = {'Day': dayofweek, 'Open time': date_time, 'High': high}
            HighDF = HighDF.append(HighData, ignore_index=True)

            LowData = {'Day': dayofweek, 'Open time': date_time, 'Low': low}
            LowDF = LowDF.append(LowData, ignore_index=True)

            closeData = {'Open time': date_time, 'Close': close}
            closeDF = closeDF.append(closeData, ignore_index=True)

            volumeData = {'Open time': date_time, 'Volume': volume}
            volumeDF = volumeDF.append(volumeData, ignore_index=True)

        HighDF.set_index('Open time', inplace=True)
        LowDF.set_index('Open time', inplace=True)
        HighDF = filterDFDate(HighDF, sDate, eDate)
        LowDF = filterDFDate(LowDF, sDate, eDate)
        weekNumber = date.today().isocalendar()[1]

        closeDF = closeDF[(closeDF['Open time'] >= sDate) & (closeDF['Open time'] <= eDate)]
        closeDF['Open time'] = "(" + pd.to_datetime(closeDF['Open time']).dt.strftime("%a") + ") " + closeDF['Open time']
        fig = px.line(closeDF, x="Open time", y="Close")
        fig.update_yaxes(autorange="reversed")
        fig.update_yaxes(categoryorder="category descending")
        st.plotly_chart(fig, use_container_width=True)

        volumeDF = volumeDF[(volumeDF['Open time'] >= sDate) & (volumeDF['Open time'] <= eDate)]
        volumeDF['Open time'] = "(" + pd.to_datetime(volumeDF['Open time']).dt.strftime("%a") + ") " + volumeDF['Open time']
        chart = alt.Chart(volumeDF).mark_line().encode(
            x=alt.X('Open time:N'),
            y=alt.Y('Volume:Q'),
            tooltip='Volume:N'
        ).properties()
        st.altair_chart(chart, use_container_width=True)

        with col1:
            st.dataframe(HighDF)
            st.info("Highest price of each week" + " (Current week #: " + str(weekNumber) + ")")
            highestDF = HighDF.groupby(['Year', 'Week']).agg({'High': 'max'})
            highest_value_list = highestDF['High'].values.tolist()
            out1 = HighDF[HighDF['High'].isin(highest_value_list)]
            df = out1.sort_values(by=['High'], ascending=False)
            df = df.drop_duplicates(subset=['Week'], keep='first')
            st.dataframe(df.sort_index(ascending=False))

        with col2:
            st.dataframe(LowDF)
            st.info("Lowest price of each week")
            lowestDF = LowDF.groupby(['Year', 'Week']).agg({'Low': 'min'})
            lowest_value_list = lowestDF['Low'].values.tolist()
            out2 = LowDF[LowDF['Low'].isin(lowest_value_list)]
            df = out2.sort_values(by=['Low'], ascending=True)
            df = df.drop_duplicates(subset=['Week'], keep='first')
            st.dataframe(df.sort_index(ascending=False))

    coinAvgCost = coinAvgPrice(coinOption[0])
    getHLAPrice(HighDF, LowDF, coinAvgCost)
    getOrderBookInfo(coinOption[0])

    if st.button('Analyze pairs for day trading'):
        dayTradingCoins()

def GetResultsJson(coinOption, intervalOption):
    # convert requests response to json
    result = requests.get('https://api1.binance.com/api/v3/klines?symbol='+str(coinOption[0])+'&interval='+str(intervalOption)+'&limit=1000')
    if result.ok:
        json_data = json.loads(result.text)
        return json_data
    else:
        GetResultsJson(coinOption)

def GetMarketPairs():
    result = requests.get('https://api.binance.com/api/v1/exchangeInfo')
    if result.ok:
        json_data = json.loads(result.text)
        return json_data

def dow(date):
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dayNumber = date.weekday()
    return days[dayNumber]

def filterDFDate(DF, sDate, eDate):
    copiedDF = DF.copy()
    copiedDF['Week'] = pd.DatetimeIndex(copiedDF.index).isocalendar().week
    copiedDF['Year'] = pd.DatetimeIndex(copiedDF.index).isocalendar().year
    copiedDF = copiedDF[(copiedDF.index.get_level_values(0) >= sDate) & (copiedDF.index.get_level_values(0) <= eDate)]
    return copiedDF

def coinAvgPrice(coinName):
    result = requests.get('https://api1.binance.com/api/v3/avgPrice?symbol='+str(coinName))
    json_data = json.loads(result.text)
    return json_data["price"]

def getHLAPrice(HighDF, LowDF, coinAvgCost):
    column = HighDF["High"]
    max_value = column.max()
    column = LowDF["Low"]
    min_value = column.min()
    st.info("__Current Avg Price (5 mins):__" + " {:.4f}".format(float(coinAvgCost))+\
             " / __Lowest Price:__" + " {:.4f}".format(float(min_value))+\
             " / __Highest Price:__" + " {:.4f}".format(float(max_value))+\
             " / __Max Earning Percentage:__" + " {:.2f}".format(float((1 - (float(min_value)/float(max_value)))*100)) +"%")

def dayTradingCoins():
    dataMarketPairs = GetMarketPairs()
    df = pd.DataFrame()
    for i in range(0, len(dataMarketPairs['symbols'])):
        coinName = dataMarketPairs['symbols'][i]['symbol']
        result = requests.get('https://api1.binance.com/api/v3/klines?symbol='+str(coinName)+'&interval=1m')
        json_data = json.loads(result.text)
        high = float(json_data[0][2])
        low = float(json_data[0][3])
        getPercentage = percentage(low, high)
        coinDetails = {'Coin': coinName, 'Low': "{:.4f}".format(low), 'High': "{:.4f}".format(high), 'Earning %': getPercentage}
        df = df.append(coinDetails, ignore_index=True)

    st.dataframe(df)

def percentage(part, whole):
    percentage = 100 * (1-(float(part)/float(whole)))
    return str("{:.2f}".format(percentage)) + "%"

def getOrderBookInfo(coinName):
    bidOrderBookDF = pd.DataFrame()
    askOrderBookDF = pd.DataFrame()
    result = requests.get('https://api1.binance.com/api/v3/depth?symbol=' + str(coinName) + '&limit=5000')
    json_data = json.loads(result.text)
    for i in range(0, len(json_data['bids'])):
        bidPrice = float(json_data['bids'][i][0])
        Qty = float(json_data['bids'][i][1])

        bidData = {'Bid': bidPrice, 'Qty': Qty}
        bidOrderBookDF = bidOrderBookDF.append(bidData, ignore_index=True)

    bidOrderBookDF['Total price'] = bidOrderBookDF['Bid'] * bidOrderBookDF['Qty']

    for i in range(0, len(json_data['asks'])):
        askPrice = float(json_data['asks'][i][0])
        Qty = float(json_data['asks'][i][1])

        askData = {'Ask': askPrice, 'Qty': Qty}
        askOrderBookDF = askOrderBookDF.append(askData, ignore_index=True)

    askOrderBookDF['Total price'] = askOrderBookDF['Ask'] * askOrderBookDF['Qty']

    col1, col2 = st.beta_columns(2)
    with col1:
        st.info("__Support__ - " + getBestBidPriceQty(coinName))
        st.dataframe(bidOrderBookDF.sort_values(by=['Bid'], ascending=False))
    with col2:
        st.info("__Resistance__ - " + getBestAskPriceQty(coinName))
        st.dataframe(askOrderBookDF.sort_values(by=['Ask']))

def getBestBidPriceQty(coinName):
    result = requests.get('https://api1.binance.com/api/v3/ticker/bookTicker?symbol=' + str(coinName))
    json_data = json.loads(result.text)
    bidPrice = float(json_data['bidPrice'])
    bidQty = float(json_data['bidQty'])

    bidString = "Best Bid Price: " + str(bidPrice) + " / Qty:" + str(bidQty)
    return bidString

def getBestAskPriceQty(coinName):
    result = requests.get('https://api1.binance.com/api/v3/ticker/bookTicker?symbol=' + str(coinName))
    json_data = json.loads(result.text)
    askPrice = float(json_data['askPrice'])
    askQty = float(json_data['askQty'])

    askString = "Best Ask Price: " + str(askPrice) + " / Qty: " + str(askQty)
    return askString



