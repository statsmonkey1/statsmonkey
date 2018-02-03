# -*- coding: utf-8 -*-
"""
Created on Sat Jul  8 18:54:22 2017

@author: Brian LeBlanc

Use requests v2.17.1

"""
import pandas as pd
import numpy as np
from steem import Steem
import requests
import matplotlib.pyplot as plt
import dropbox
import matplotlib.dates as mdates
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys

"""
*******************************************************************************
PARAMETERS
*******************************************************************************
"""

# Output folder location where graphs are stored before uploading to dropbox
# *** MAKE SURE YOU USE / AND NOT \ ***
output_folder = "C:/steemit/Plots/"

# Which currency to create the report for
currency = "bitshares"

# Dropbox access token to upload/host graphs from dropbox
#dropbox_access_token = 'PfrXjIbJVAwAAAAAAAACfDJ5CjfBzWdZ6kJZyvdJfXdc0jX-OVTj-3z0zSrNnDvF'
dropbox_access_token = 'UTVWT3th_5AAAAAAAAAADEvAYd5eIQWIyhl75-JNl4D8MjF_79FegOYvHqRHtecS'

# Steemit keys for posting
private_posting_key = '5K8v58LbciuZEwfKvSmwWcE8UBaJVvv8gNMEAg7RnSYNCivSVHP'
private_active_key = '5KGv5NsrgdDXHpXYAj8txgNvNAwL4AYq3LkRy3GnNrqE4hP2Tof'

# Parameters for EMA Fast, EMA Slow, Signal line, and RSI respectively
FASTX_PERIOD = 12
SLOWY_PERIOD = 26
SIGNAL_PERIOD = 9
RSI_PERIOD = 14

# Parameters for RSI graph
OVERBOUGHT = 70
OVERSOLD = 30
MIDDLE = 50

# Lookback window for Aroon graph
aroon_window = 25

# Indicate range of data for analysis. e.g. 40 = last 40 days of data
data_window = 40

# Tags for post. First is the currency.
tags = [currency, 'money', 'cryptocurrency', 'crypto-news', 'stats']

# Link to cover photo
cover_photo_link = 'https://www.dropbox.com/s/i1hy8ptuxojg1md/cover.PNG?dl=1'

# Email to send alerts to
from_email = "steemit.alerts@gmail.com"

# Password for from_email
from_pswd = "Steemit1!"

# Where to send emails to
to_email = "bl1741@nyu.edu"

"""
*******************************************************************************
*******************************************************************************
"""
#%% Function to send email alerts

def emailer(currency, body, from_email, from_pswd, to_email):
    fromaddr = from_email
    toaddr = to_email
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Error posting Steemit post: " + currency
     
    msg.attach(MIMEText(body, 'plain'))
     
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, from_pswd)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()

#%% Grab data from coinmarketcap

try: # Try pulling data from coinmarketcap
    link = 'https://graphs.coinmarketcap.com/currencies/' + currency
    
    df = pd.DataFrame(requests.get(link).json())
    
    
    df2 = pd.concat([pd.DataFrame([x for x in df[df.columns[y]]], columns = ['Date', df.columns[y]]).set_index('Date', drop = True) for y in range(len(df.columns))],axis = 1)
    
    df2.index = pd.to_datetime(df2.index, unit = 'ms').date
    
    df2 = df2[~df2.index.duplicated(keep='first')]
except: # If the above fails, send a notification email
    body_ = "Error pulling market data from coinmarketcap.com. Try going to " + link + " to see if any data appears"
    emailer(currency, body_, from_email, from_pswd, to_email)
    sys.exit()

#%% do calculations to get MACD, Rsi, etc.

try: # Try doing calculations for plots
    FASTX_ALPHA = 2/(1+FASTX_PERIOD)
    SLOWY_ALPHA = 2/(1+SLOWY_PERIOD)
    SIGNAL_ALPHA = 2/(1+SIGNAL_PERIOD)
    RSI_ALPHA = 1/RSI_PERIOD
    FASTX_1_ALPHA = 1-FASTX_ALPHA
    SLOWY_1_ALPHA = 1-SLOWY_ALPHA
    SIGNAL_1_ALPHA = 1-SIGNAL_ALPHA
    RSI_1_ALPHA = 1-RSI_ALPHA
    
    df2.ix[df2.index[0],'EMA_FAST'] = df2['price_usd'].loc[df2.index[0]]
    df2.ix[df2.index[0],'EMA_SLOW'] = df2['price_usd'].loc[df2.index[0]]
    
    for x in df2.index[1:]:
        df2.ix[x, 'EMA_FAST'] = FASTX_ALPHA*df2.ix[x,'price_usd'] + FASTX_1_ALPHA*df2.shift().ix[x,'EMA_FAST']
        df2.ix[x, 'EMA_SLOW'] = SLOWY_ALPHA*df2.ix[x,'price_usd'] + SLOWY_1_ALPHA*df2.shift().ix[x,'EMA_SLOW']
    
    
    df2['MACD'] = df2['EMA_FAST'] - df2['EMA_SLOW']
    
    df2.ix[df2.index[0], 'SIGNAL LINE'] = 0
    
    for x in df2.index[1:]:
        df2.ix[x,'SIGNAL LINE'] = SIGNAL_ALPHA*df2.ix[x, 'MACD'] + SIGNAL_1_ALPHA*df2.shift().ix[x, 'MACD']
    
    df2['MACD-HISTOGRAM'] = df2['MACD'] - df2['SIGNAL LINE']
    
    df2['d_price'] = df2['price_usd'] - df2['price_usd'].shift()
    
    df2['U'] = df2[df2['d_price']>0]['d_price']
    df2['U'] = df2['U'].replace(np.nan, 0)
    
    df2['D'] = -df2[df2['d_price']<0]['d_price']
    df2['D'] = df2['D'].replace(np.nan, 0)
    
    df2.ix[df2.index[0], 'SMMA_U'] = 0
    df2.ix[df2.index[0], 'SMMA_D'] = 0
    
    for x in df2.index[1:]:
        df2.ix[x, 'SMMA_U'] = RSI_ALPHA*df2.ix[x,'U'] + RSI_1_ALPHA*df2.shift().ix[x,'SMMA_U']
        df2.ix[x, 'SMMA_D'] = RSI_ALPHA*df2.ix[x,'D'] + RSI_1_ALPHA*df2.shift().ix[x,'SMMA_D']
    
    df2['RS'] = df2['SMMA_U']/df2['SMMA_D']
    df2['RSI'] = 100 - (100/(1+df2['RS']))
    
    df2['OVERBOUGHT'] = OVERBOUGHT
    df2['OVERSOLD'] = OVERSOLD
    df2['MIDDLE'] = MIDDLE
    
    for x in range(len(df2)-aroon_window):
        aroon_up = np.argmax(df2['price_usd'].loc[df2.index[-aroon_window-x]:df2.index[-x-1]].reset_index(drop=True))
        aroon_down = np.argmin(df2['price_usd'].loc[df2.index[-aroon_window-x]:df2.index[-x-1]].reset_index(drop=True))
        
        df2.ix[df2.index[-x-1],'aroon_up']  = (aroon_window - (aroon_window - aroon_up))/aroon_window*100
        df2.ix[df2.index[-x-1],'aroon_down'] = (aroon_window - (aroon_window - aroon_down))/aroon_window*100
    
    df2['UP_DOWN'] = df2[(df2['volume_usd'].diff()>0)]['volume_usd'] - df2[(df2['volume_usd'].diff()>0)]['volume_usd'] + 1
    df2['UP_DOWN'] = df2['UP_DOWN'].replace(np.nan, -1.0)
    
    df2['VOL_PLUS_MIN'] = df2['UP_DOWN']*df2['volume_usd']/df2['price_usd']
    
    for x in df2.index:
        df2.ix[x, 'OBV'] = df2['VOL_PLUS_MIN'].loc[:x].sum()
        
except: # Send email if above fails
    body_ = "An error occured conducting calculations for charts. That data is reading in correctly."
    emailer(currency, body_, from_email, from_pswd, to_email)
    sys.exit()
    
#%% PLOTS
    
try:
    df3 = df2.loc[df2.index[-data_window]:]
    MACD, ax = plt.subplots(2, figsize = (12,8))
    ax[0].plot(df3['price_usd'], alpha = 0.7, lw = 2.0, label = currency + " price (USD)")
    ax[0].plot(df3['EMA_FAST'], alpha = 0.7, lw = 2.0, label = "EMA Fast (C," + str(FASTX_PERIOD) + ")")
    ax[0].plot(df3['EMA_SLOW'], alpha = 0.7, lw = 2.0, label = "EMA Slow (C," + str(SLOWY_PERIOD) + ")")
    ax[1].plot(df3['MACD'], alpha = 0.7, lw = 2.0, label = "MACD")
    ax[1].plot(df3['SIGNAL LINE'], alpha = 0.7, lw = 2.0, label = "Signal Line")
    ax[1].bar(df3.index, df3['MACD-HISTOGRAM'], alpha = 0.7, label = "MACD-Histogram")
    ax[1].set_xticks(ax[0].get_xticks())
    
    for x in ax:
        x.spines['right'].set_color('none')
        x.spines['top'].set_color('none')
        
    ax[1].spines['bottom'].set_position('zero')   
    ax[1].axes.get_xaxis().set_visible(False)
    ax[0].set_xticklabels(ax[0].xaxis.get_majorticklabels(), rotation=30)
    myFmt = mdates.DateFormatter('%m/%d/%y')
    ax[0].xaxis.set_major_formatter(myFmt)
    ax[0].xaxis.set_ticks_position('bottom')
    ax[0].yaxis.set_ticks_position('left')
    ax[1].yaxis.set_ticks_position('left')
    ax[0].legend(loc=2)
    ax[1].legend(loc=2)
    
    RSI_PLOT, ax = plt.subplots(2, figsize = (12,8))
    ax[0].plot(df3['price_usd'], alpha = 0.7, lw = 2.0, label = currency + " price (USD)")
    ax[1].plot(df3['RSI'], alpha = 0.7, lw = 2.0, label = 'RSI', color = 'r')
    ax[1].plot(df3['OVERBOUGHT'], alpha = 0.7, lw = 2.0, label = 'Overbought(70)', ls = "--", color = 'k')
    ax[1].plot(df3['MIDDLE'], alpha = 0.7, lw = 2.0, label = 'Middle(50)', color = 'k')
    ax[1].plot(df3['OVERSOLD'], alpha = 0.7, lw = 2.0, label = 'Undersold(30)', ls = "--", color = 'k')
    for x in ax:
        x.spines['right'].set_color('none')
        x.spines['top'].set_color('none')
        
    ax[1].spines['bottom'].set_position('zero')   
    ax[1].axes.get_xaxis().set_visible(False)
    ax[0].set_xticklabels(ax[0].xaxis.get_majorticklabels(), rotation=30)
    myFmt = mdates.DateFormatter('%m/%d/%y')
    ax[0].xaxis.set_major_formatter(myFmt)
    ax[0].xaxis.set_ticks_position('bottom')
    ax[0].yaxis.set_ticks_position('left')
    ax[1].yaxis.set_ticks_position('left')
    ax[0].legend(loc=2)
    ax[1].legend(loc=3, ncol = 4)
    ax[1].set_ylim([0,100])
    
    AROON_PLOT, ax = plt.subplots(2, figsize = (12,8))
    ax[0].plot(df3['price_usd'], alpha = 0.7, lw = 2.0, label = currency + " price (USD)")
    ax[1].plot(df3['aroon_up'], alpha = 0.7, lw = 2.0, label = 'Aroon-Up', color = 'r')
    ax[1].plot(df3['aroon_down'], alpha = 0.7, lw = 2.0, label = 'Aroon-Down', color = 'r')
    ax[1].plot(df3['OVERBOUGHT'], alpha = 0.7, lw = 2.0, ls = "--", color = 'k')
    ax[1].plot(df3['MIDDLE'], alpha = 0.7, lw = 2.0, color = 'k')
    ax[1].plot(df3['OVERSOLD'], alpha = 0.7, lw = 2.0, ls = "--", color = 'k')
    
    for x in ax:
        x.spines['right'].set_color('none')
        x.spines['top'].set_color('none')
        
    ax[1].spines['bottom'].set_position('zero')   
    ax[1].axes.get_xaxis().set_visible(False)
    ax[0].set_xticklabels(ax[0].xaxis.get_majorticklabels(), rotation=30)
    myFmt = mdates.DateFormatter('%m/%d/%y')
    ax[0].xaxis.set_major_formatter(myFmt)
    ax[0].xaxis.set_ticks_position('bottom')
    ax[0].yaxis.set_ticks_position('left')
    ax[1].yaxis.set_ticks_position('left')
    ax[0].legend(loc=2)
    handles, labels = ax[1].get_legend_handles_labels()
    ax[1].legend(handles[:2], labels[:2], loc=2, ncol = 4)
    ax[1].set_ylim([0,100])
    
    OBV_PLOT, ax = plt.subplots(2, figsize = (12,8))
    ax[0].plot(df3['price_usd'], alpha = 0.7, lw = 2.0, label = currency + " price (USD)")
    ax[1].plot(df3['OBV'], alpha = 0.7, lw = 2.0, label = 'OBV', color = 'r')
    
    for x in ax:
        x.spines['right'].set_color('none')
        x.spines['top'].set_color('none')
        
    ax[1].spines['bottom'].set_position('zero')   
    ax[1].axes.get_xaxis().set_visible(False)
    ax[0].set_xticklabels(ax[0].xaxis.get_majorticklabels(), rotation=30)
    myFmt = mdates.DateFormatter('%m/%d/%y')
    ax[0].xaxis.set_major_formatter(myFmt)
    ax[0].xaxis.set_ticks_position('bottom')
    ax[0].yaxis.set_ticks_position('left')
    ax[1].yaxis.set_ticks_position('left')
    ax[0].legend(loc=2)
    ax[1].set_ylim([0,ax[1].get_ylim()[1]])
    ax[1].legend(loc=3)

    MACD_file_from = output_folder + "MACD" + str(df3.index[-1]).replace("-","") + "_" + str(int(time.time())) + ".PNG"
    RSI_file_from = output_folder + "RSI" + str(df3.index[-1]).replace("-","") + "_" + str(int(time.time())) + ".PNG"
    AROON_file_from = output_folder + "AROON" + str(df3.index[-1]).replace("-","") + "_" + str(int(time.time())) + ".PNG"
    OBV_file_from = output_folder + "OBV" + str(df3.index[-1]).replace("-","") + "_" + str(int(time.time())) + ".PNG"
    
    MACD.savefig(MACD_file_from)
    RSI_PLOT.savefig(RSI_file_from)
    AROON_PLOT.savefig(AROON_file_from)
    OBV_PLOT.savefig(OBV_file_from)
    
except:
    body_ = "An error occured when plotting the charts or saving them to your local drive. Check to make sure the file location you inputted is still valid."
    emailer(currency, body_, from_email, from_pswd, to_email)
    sys.exit()

#%% Function to save graphs to dropbox

def write_to_dropbox(file_from, access_token):
    dbx = dropbox.Dropbox(access_token)
    file_to = '/graphs/' + file_from.split("/")[-1]
    
    with open(file_from, 'rb') as f:
        dbx.files_upload(f.read(), file_to)
        
    url = dbx.sharing_create_shared_link(file_to).url
    url = url.replace(r"?dl=0", "?dl=1")
    return url
    
try:
    MACD_url = write_to_dropbox(MACD_file_from, dropbox_access_token)    
    RSI_url = write_to_dropbox(RSI_file_from, dropbox_access_token)    
    AROON_url = write_to_dropbox(AROON_file_from, dropbox_access_token)   
    OBV_url = write_to_dropbox(OBV_file_from, dropbox_access_token) 
except:
    body_ = "An error occured when outputing the files to dropbox. Check to make sure internet is working."
    emailer(currency, body_, from_email, from_pswd, to_email)
    sys.exit()
    
#%%

if df2['MACD-HISTOGRAM'].loc[df2.index[-1]]>0:
    MACD_TEXT_REPLACE_1 = "above"
    MACD_TEXT_REPLACE_2 = "bullish"
    MACD_TEXT_REPLACE_3 = "buy"
    MACD_TEXT_REPLACE_4 = "upward"
else:  
    MACD_TEXT_REPLACE_1 = "below"
    MACD_TEXT_REPLACE_2 = "bearish"
    MACD_TEXT_REPLACE_3 = "sell"
    MACD_TEXT_REPLACE_4 = "downward"
    
if df2['RSI'].loc[df2.index[-1]]<30:
    RSI_TEXT_REPLACE_1 = "below 30"
    RSI_TEXT_REPLACE_2 = "becoming oversold" 
    RSI_TEXT_REPLACE_3 = "a price reversal to the upside" 
else:
    if df2['RSI'].loc[df2.index[-1]]>70:
        RSI_TEXT_REPLACE_1 = "above 70"
        RSI_TEXT_REPLACE_2 = "becoming overbought" 
        RSI_TEXT_REPLACE_3 = "a price reversal to the downside" 
    else:
        RSI_TEXT_REPLACE_1 = "between 30 and 70"
        RSI_TEXT_REPLACE_2 = "neither overbought or oversold" 
        RSI_TEXT_REPLACE_3 = "no material price change" 

if df2['aroon_up'].loc[df2.index[-1]]>50:
    if df2['aroon_down'].loc[df2.index[-1]]<50:
        AROON_TEXT_REPLACE = "the Aroon-Up is above 50 and the Aroon-Down is below 50 indicating a bullish signal"
    else:
        AROON_TEXT_REPLACE = "the Aroon-Up is above 50 and the Aroon-Down is below 50 indicating neither bullish or bearish signal"
else:
    if df2['aroon_down'].loc[df2.index[-1]]>50:   
        AROON_TEXT_REPLACE = "the Aroon-Up is below 50 and the Aroon-Down is above 50 indicating a bearish signal"
    else:
        AROON_TEXT_REPLACE = "the Aroon-Up is below 50 and the Aroon-Down is above 50 indicating neither a bullish or bearish signal" 
        
        
#%%

s = Steem(keys=[private_posting_key, private_active_key])
body = """
<html>
<p><img src="COVER_PHOTO_REPLACE"/></p>
<h1>Price Forecast Report for CURRENCY_TEXT_REPLACE &#8212; DATE_TEXT_REPLACE&nbsp;</h1>
<p>Welcome to the Price Forecast Report for CURRENCY_TEXT_REPLACE &#8212; DATE_TEXT_REPLACE. &nbsp;&nbsp;</p>
<p>This report investigates 4 popular technical analysis indicators:&nbsp;</p>
<ul>
  <li>Moving Average Convergence Divergence&nbsp;</li>
  <li>Relative Strength Index</li>
  <li>Aroon Indicator</li>
  <li>On-Balance Volume</li>
</ul>
<p>&nbsp;The above indicators are used in technical analysis as tools for forecasting the direction of prices through the study of past market data, primarily price and volume.<br>
<br>
They are based on the idea that the market for buying and selling digital currencies is not efficient and historic prices can be used to predict future price movements, and using these tools can be advantageous to investors and traders. &nbsp;</p>
<h2>Moving Average Convergence Divergence (MACD)&nbsp;</h2>
<p>Moving average convergence divergence (MACD) is a trend-following indicator of momentum that illustrates the relationship between two moving averages of prices. The MACD is estimated by subtracting the 26-day exponential moving average from the 12-day moving average. A nine-day exponential moving average of the MACD, the "signal line", is then plotted on top of the MACD, functioning as an identifier for both buy and sell signals. &nbsp;</p>
<p>The graph below shows the MACD applied to the price of CURRENCY_TEXT_REPLACE using daily price data for the last DATA_WINDOW_REPLACE days. &nbsp;&nbsp;</p>
<p><img src="MACD_URL_REPLACE"/></p>
<p>&nbsp;As shown in the chart above, the MACD is currently MACD_TEXT_REPLACE_1 the signal line, implying a MACD_TEXT_REPLACE_2 signal, indicating that it may be an optimal time to MACD_TEXT_REPLACE_3. &nbsp;</p>
<p>According to the MACD, a MACD_TEXT_REPLACE_2 signal suggests that the price of the asset is likely to experience MACD_TEXT_REPLACE_4 momentum. &nbsp;&nbsp;</p>
<h2>Relative Strength Index (RSI)</h2>
<p>&nbsp;The relative strength index (RSI) is another price momentum indicator that compares the size of recent gains and losses over a specified time period to calculate speed and change of price movements of a digital currency. It is mainly used to identify <a href="http://www.investopedia.com/terms/o/overbought.asp">overbought</a> or <a href="http://www.investopedia.com/terms/o/oversold.asp">oversold</a> situations in the trading of a digital currency. &nbsp;</p>
<p>RSI values of 70 or above are traditionally seen to indicate that a security is becoming overbought or overvalued, and therefore may be set for a trend reversal or corrective reduction in the price. On the other side, an RSI reading of below 30 is generally interpreted as indicating an oversold or undervalued condition that may signal a change in the direction of the price to the upside.&nbsp;</p>
<p>The graph below shows the RSI applied to the price of Steem based on daily price data for the last DATA_WINDOW_REPLACE days. &nbsp;&nbsp;</p>
<p><img src="RSI_URL_REPLACE"/></p>
<p>Since the RSI is currently RSI_TEXT_REPLACE_1, this would indicate that CURRENCY_TEXT_REPLACE is RSI_TEXT_REPLACE_2 and that RSI_TEXT_REPLACE_3 is expected. &nbsp;</p>
<h2>Aroon Indicator</h2>
<p>The Aroon indicator can be used to identify trends in digital currency prices and the likelihood that the trends will reverse. It is made up of two trend lines: an "Aroon up" line, which measures the magnitude of the uptrend, and an "Aroon down", which measures the size of a downtrend. The indicator reports the time it is taking for the price to reach, from a beginning point, the highest and lowest points over a given time period, each reported as a percentage of total time. &nbsp;&nbsp;</p>
<p>The graph below shows the Aroon Indicator using the price of CURRENCY_TEXT_REPLACE over the last DATA_WINDOW_REPLACE days. &nbsp;&nbsp;</p>
<p>The Aroon indicators move above and below the centerline (50) and are bound between 0 and 100. These three levels can be explained as follows: When the Aroon-Up is above 50 and the Aroon-Down is below 50, the bulls have an edge. This indicates a greater propensity for new x-day highs than lows. The opposite is true for a downtrend. The bears have an edge when Aroon-Up is below 50 and Aroon-Down is above 50. &nbsp;&nbsp;</p>
<p>In the graph below, AROON_TEXT_REPLACE.</p>
<p><img src="AROON_URL_REPLACE"/></p>
<h2>On-Balance Volume (OBV)&nbsp;</h2>
<p>The OBV indicator can be used to measure the positive and negative movement of volume of a currency relative to its price over time. &nbsp;&nbsp;&nbsp;</p>
<p>The idea is that volume precedes price movement, so if a currency is experiencing an increasing OBV it is a signal that the level of volume traded is increasing on upward price moves. Decreases mean that the security is seeing growing levels of volume on down days. &nbsp;&nbsp;&nbsp;</p>
<p>The graph below shows the OBV applied to the price of CURRENCY_TEXT_REPLACE using daily price data for the last DATA_WINDOW_REPLACE days. &nbsp;&nbsp;</p>
<p><img src="OBV_URL_REPLACE" width="564" height="564"/></p>
<p><strong>Please note that the above indicators can give false trade signals and use of such tools should be treated with caution. Blindly using technical pricing indicators without a general knowledge of fundamentals or an understanding of the currency being analysed is not advisable.</strong></p>
<p>Thank you for reading</p>
<p>&nbsp;<em>Source of data: www.coinmarketcap.com</em>&nbsp;</p>
<p><br></p>
</html>
"""

date = df2.index[-1]

day = date.day

if 4 <= day <= 20 or 24 <= day <= 30:
    suffix = "th"
else:
    suffix = ["st", "nd", "rd"][day % 10 - 1]

body = body.replace("COVER_PHOTO_REPLACE", cover_photo_link)  
body = body.replace("CURRENCY_TEXT_REPLACE", currency.capitalize())
body = body.replace("DATE_TEXT_REPLACE", str(day) + suffix + " " + str(date.strftime("%B")) + " " + str(date.year))
body = body.replace("MACD_URL_REPLACE", MACD_url)
body = body.replace("RSI_URL_REPLACE", RSI_url)
body = body.replace("AROON_URL_REPLACE", AROON_url)
body = body.replace("OBV_URL_REPLACE", OBV_url)
body = body.replace("DATA_WINDOW_REPLACE", str(int(data_window)))
body = body.replace("MACD_TEXT_REPLACE_1", MACD_TEXT_REPLACE_1).replace("MACD_TEXT_REPLACE_2", MACD_TEXT_REPLACE_2).replace("MACD_TEXT_REPLACE_3", MACD_TEXT_REPLACE_3).replace("MACD_TEXT_REPLACE_4", MACD_TEXT_REPLACE_4)
body = body.replace("RSI_TEXT_REPLACE_1", RSI_TEXT_REPLACE_1).replace("RSI_TEXT_REPLACE_2", RSI_TEXT_REPLACE_2).replace("RSI_TEXT_REPLACE_3", RSI_TEXT_REPLACE_3)
body = body.replace("AROON_TEXT_REPLACE", AROON_TEXT_REPLACE)

title = currency.capitalize() + " Price Forecast - " + str(day) + suffix + " " +  str(date.strftime("%B"))

try:
    s.commit.post(title, body, "bl1741", tags = tags)
except:
    body_ = "An error occured while trying to post the steemit.com. Note that you have to wait 5 minutes before writing new blog posts"
    emailer(currency, body_, from_email, from_pswd, to_email)
    sys.exit()
