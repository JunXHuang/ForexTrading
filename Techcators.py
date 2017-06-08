def MovingAverage(data,start,end):
    sum = 0
    for i in range(start,end):
        sum += float(data['candles'][i]['mid']['c'])
    return sum/(end-start)

# need to fix calculations
def RSI(data,period):
    gain = 0
    loss = 0
    RS = 0
    for i in range(1,period-1):
        temp = float(data['candles'][i]['mid']['c'])-float(data['candles'][i-1]['mid']['c'])
        if temp > 0:
            gain += temp
        else:
            loss += abs(temp)
    gain /= (period-2)
    loss /= (period-2)
    currentCandle = float(data['candles'][period-1]['mid']['c'])-float(data['candles'][period-2]['mid']['c'])
    if currentCandle > 0:
        gain = (gain * (period-3) + currentCandle) / (period-2)
        loss = (loss * (period-3)) / (period-2)
    else:
        if loss == 0 and currentCandle == 0:
            return 100.0
        gain = (gain * (period-3)) / (period-2)
        loss = (loss * (period-3) - currentCandle) / (period-2)
 
    RS = gain/loss
    return  100 - (100 / ( 1 + RS ))
    print str(Techcators.MovingAverage(getCandles(50,'H1'),50))
    print str(Techcators.RSI(getCandles(16,'H1'),16))

