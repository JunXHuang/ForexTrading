import requests
import json
import time
from time import gmtime, strftime
from twilio.rest import TwilioRestClient
import datetime
import sys
import Techcators

with open(sys.argv[1]) as f:
    fileOpen = f.readlines()
fileOpen = [x.strip() for x in fileOpen] 

access_token = fileOpen[0]
account_id = fileOpen[1]
instruments = fileOpen[2]
domain = fileOpen[3]
account_sid = fileOpen[4]
auth_token = fileOpen[5]
TakeProfit = float(fileOpen[6])
IncreasePip = float(fileOpen[7])
InitialUnits = int(fileOpen[8])

twilioClient = TwilioRestClient(account_sid, auth_token)
TrailingStop = False
def executeOrder(orderType,endpoint,params,body):
    try:
        s = requests.Session()
        headers = {'Authorization' : 'Bearer ' + access_token}
        req = requests.Request(orderType, domain+endpoint, headers = headers, params = params, json = body)
        pre = req.prepare()
        resp = s.send(pre, stream = False, verify = True)
        s.close()
        return resp
    except Exception as e:
        s.close()
        print ('Caught exception when trying to executeOrder = ' + str(e))
        message = twilioClient.messages.create(to='+17186352186', from_='+12678675972',
                                body=strftime('%Y-%m-%d %H:%M:%S',gmtime())+'Caught exception when trying to executeOrder = ' + str(e)+' on '+instruments
                                +' ordertype = '+ orderType
                                +' endpoint = '+ domain+endpoint
                                +' headers = '+ headers
                                +' params = '+ params
                                +' body = '+ body)

def getReponse(endpoint,params):
    response = executeOrder('GET',endpoint,params,{})
    if response.status_code != 200:
        print 'ERROR ' + str(response.status_code) +' on '+ instruments+' error content = '+response.content
        message = twilioClient.messages.create(to='+17186352186', from_='+12678675972',
                                     body=strftime('%Y-%m-%d %H:%M:%S',gmtime())+' ERROR Code = '+str(response.status_code)+' on '+instruments
                                     +' error content = '+response.content)
        return
    for line in response.iter_lines(1):
        if line:
            try:
                msg = json.loads(line)
                return msg
            except Exception as e:
                print ("Caught exception when converting message into json\n" + str(e))+' error content = '+response.content
                message = twilioClient.messages.create(to='+17186352186', from_='+12678675972',
                                     body=strftime('%Y-%m-%d %H:%M:%S',gmtime())+'Caught exception when converting message into json' + str(e) +' on '+instruments
                                     +' error content = '+response.content)
                return

def getCurrentPrices():
    endpoint = 'accounts/'+account_id+'/pricing'
    params = {'instruments' : instruments}
    return getReponse(endpoint,params)

def getOpenTrades():
    endpoint = 'accounts/'+account_id+'/openTrades'
    msg = getReponse(endpoint,{})
    return msg['trades']

def getMovingAverage(period,timeframe):
    endpoint = 'instruments/'+instruments+'/candles'
    params = {'count' : period+1, 'price' : 'M', 'granularity' : timeframe}
    msg = getReponse(endpoint,params)
    sum1 = 0
    for i in range(0,period):
        sum1 += float(msg['candles'][i]['mid']['c'])
    sum2 = sum1 + float(msg['candles'][period]['mid']['c'])-float(msg['candles'][0]['mid']['c'])
    return (sum1/period - sum2/period)  # if return greater than 0 short else long


def createOrder(units):
    endpoint = 'accounts/'+account_id+'/orders'
    body = {'order':{'units': units,  'instrument': instruments, "timeInForce": "FOK", "type": "MARKET", "positionFill": "DEFAULT"}}
    response = executeOrder('POST',endpoint,{},body)
    if response.status_code != 201:
        print 'ERROR ' + str(response.status_code)+' error content = '+response.content
        message = twilioClient.messages.create(to='+17186352186', from_='+12678675972',
                                     body='create order ERROR ' + str(response.status_code)
                                     +' error content = '+response.content)
    else:
        message = twilioClient.messages.create(to='+17186352186', from_='+12678675972',
                                     body=strftime('%Y-%m-%d %H:%M:%S',gmtime())+' Created new order with units = '+str(units)+' on '+instruments)

def closeOrder(tradeID):
    endpoint = 'accounts/'+account_id+'/trades/'+str(tradeID)+'/close'
    response = executeOrder('PUT',endpoint,{},{})
    if response.status_code != 200:
        print 'ERROR trying to close tradeID = {'+str(tradeID)+'} and error code = '+ str(response.status_code)
        message = twilioClient.messages.create(to='+17186352186', from_='+12678675972',
                                     body='ERROR trying to close tradeID = '+str(tradeID)+' and error code = '+ str(response.status_code)+' error content = '+response.content
                                     +' error content = '+response.content)
    else:
        message = twilioClient.messages.create(to='+17186352186', from_='+12678675972',
                                     body = strftime('%Y-%m-%d %H:%M:%S',gmtime())+' Closed tradeID = '+str(tradeID)+' on '+instruments)

def trailingStopOrder(tradeID,price):
    endpoint = 'accounts/'+account_id+'/trades/'+str(tradeID)+'/orders'
    body = {'trailingStopLoss':{'distance':price}}
    response = executeOrder('PUT',endpoint,{},body)
    if response.status_code != 200:
        print 'ERROR trying to close tradeID = {'+str(tradeID)+'} and error code = '+ str(response.status_code) +' error content = '+response.content
        message = twilioClient.messages.create(to='+17186352186', from_='+12678675972',
                                     body='ERROR trying to set trailingStop for tradeID = '+str(tradeID)+' error code = '+ str(response.status_code)
                                     +' error content = '+response.content)
    else:
        message = twilioClient.messages.create(to='+17186352186', from_='+12678675972',
                                     body = strftime('%Y-%m-%d %H:%M:%S',gmtime())+' Set trailingStop for tradeID = '+str(tradeID)+' on '+instruments+ ' with '+str(price)+' pips')
def checkProfit(openTrades):
    sum = 0
    tradeID = []
    units = 0
    openTradePrices = []
    for trade in openTrades:
        sum += float(trade['unrealizedPL'])
        tradeID.append(int(trade['id']))   
        units += int(trade['currentUnits']) 
        openTradePrices.append(str(trade['price'])) 
    openTradePrices.sort()
    decimal = openTradePrices[0]
    d = decimal[::-1].find('.') - 1
    tradeID.sort()
    if sum >= TakeProfit and len(tradeID)>=4:
        for i in tradeID:
            closeOrder(i)
        return True
    if sum >= TakeProfit*(abs(units)/InitialUnits):
        print 'set trailing stop with total profit = ' + str(sum)
        message = twilioClient.messages.create(to='+17186352186', from_='+12678675972',
                                     body = strftime('%Y-%m-%d %H:%M:%S',gmtime())+' Set trailing stop with total profit = ' + str(sum)+' on '+instruments)
        for i in tradeID:
            trailingStopOrder(i,(IncreasePip/2)*pow(10,-d))
            #closeOrder(i)
        return True
    return False

def checkNextTrade(openTrades):
    newPrice = getCurrentPrices()
    units = 0
    tradeID = []
    openTradePrices = []
    for trade in openTrades:
        units += int(trade['currentUnits'])
        tradeID.append(int(trade['id']))   
        openTradePrices.append(float(trade['price'])) 
    openTradePrices.sort()
    decimal = str(newPrice['prices'][0]['asks'][0]['price'])
    d = decimal[::-1].find('.') - 1

    if units > 0:
        if float(newPrice['prices'][0]['asks'][0]['price']) <= openTradePrices[0]-IncreasePip*pow(10,-d):
            if len(tradeID)>=6:
                for i in tradeID:
                    closeOrder(i)
                return
            createOrder(units)
    else:
        if float(newPrice['prices'][0]['bids'][0]['price']) >= openTradePrices.pop()+IncreasePip*pow(10,-d):
            if len(tradeID)>=6:
                for i in tradeID:
                    closeOrder(i)
                return
            createOrder(units)

def getCandles(period,timeframe):
    endpoint = 'instruments/'+instruments+'/candles'
    params = {'count' : period, 'price' : 'M', 'granularity' : timeframe}
    return getReponse(endpoint,params)

def mainLoop():
    #print 'short' if getMovingAverage(5,'H1') > 0 else 'long'   
    #print 'short' if getMovingAverage(10,'H1') > 0 else 'long'
    #print 'short' if getMovingAverage(20,'H1') > 0 else 'long'
    #print 'short' if getMovingAverage(50,'H1') > 0 else 'long'
    #print 'short' if getMovingAverage(100,'H1') > 0 else 'long'
    #print 'short' if getMovingAverage(200,'H1') > 0 else 'long'
    candleData = getCandles(200,'H1');
    currentPrice = float(candleData['candles'][199]['mid']['c'])
    MA10 = Techcators.MovingAverage(candleData,190,200)
    MA20 = Techcators.MovingAverage(candleData,180,200)
    MA50 = Techcators.MovingAverage(candleData,150,200)
    MA100 = Techcators.MovingAverage(candleData,100,200)
    MA200 = Techcators.MovingAverage(candleData,0,200)
    print 'short' if MA10 > currentPrice else 'long'
    print 'short' if MA20 > currentPrice else 'long'
    print 'short' if MA50 > currentPrice else 'long'
    print 'short' if MA100 > currentPrice else 'long'
    print 'short' if MA200 > currentPrice else 'long'
    candleData = getCandles(201,'H1');
    MA10 = Techcators.MovingAverage(candleData,191,201)-Techcators.MovingAverage(candleData,190,200)
    MA20 = Techcators.MovingAverage(candleData,181,201)-Techcators.MovingAverage(candleData,180,200)
    MA50 = Techcators.MovingAverage(candleData,151,201)-Techcators.MovingAverage(candleData,150,200)
    MA100 = Techcators.MovingAverage(candleData,101,201)-Techcators.MovingAverage(candleData,100,200)
    MA200 = Techcators.MovingAverage(candleData,1,201)-Techcators.MovingAverage(candleData,0,200)
    print 'slope -----------'
    print MA10 
    print MA20 
    print MA50 
    print MA100 
    print MA200 
    print 'short' if MA10 < 0 else 'long'
    print 'short' if MA20 < 0 else 'long'
    print 'short' if MA50 < 0 else 'long'
    print 'short' if MA100 < 0 else 'long'
    print 'short' if MA200 < 0 else 'long'
def main():
    print 'Tester'
    #while(1):
    mainLoop()
        #time.sleep(10)




if __name__ == "__main__":
    main()
