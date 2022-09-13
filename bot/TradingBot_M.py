'''
pandas.concat
print(OrderContract.symbol) 
Multiple pairs trading:  
differ symbok the first 2 characters 'IB'
Increment:XAGUSD,GBPPLN,ZARJPY,SGDJPY--to get the PriceIncements.app.reqContractDetails(1, contract)
cannot historicall data...(JPY cannot?)
concurrent signal occured
auto calculate position size by SL ppt and risk amount and point value
Forex rate conversion
must read positions first in voild of double position due to restart,
position and avgcost not normal:use BOT/SLD與self.direction去累加扣除self.position與avgcost，
check exist position and no place order,set second entry > average cost and profit
'BUY EURUSD','SELL GBPUSD'
save position & avgcost to csv
re-entry instantly after exit
IBDE30 currency EUR
EURJPY,EURCHF risk amout usd right?
DeprecationWarning: setDaemon()
IB indecies no contractDetails
config.cfg to setup
currency in dict to lookup.ex: 'JPY':132.24,rewrite line 942
use trade and open_trade list record trades for simulated and save to csv for multi-program use.write PnL to csv
close first when use self.trade.commisionReport cannot accept non-in-pair symbol.
xxxUSD and USDxxx all / ?
usdmxn problem
realized and unrealized PNL convert
continue input symbol
commision currency transform

2nd time signal entry,scale-in,modify order
MKT2LMT,open order=0
Take a look at Minimum Price Increment to see how you can use the MarketRuleIds field in the ContractDetails object and IBApi::EClient::reqMarketRule: 
K bar time lag
volumn increment
stocks CFD trading:need to subscribe market data streaming    




'''
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.commission_report import CommissionReport
from ibapi.order import *
from ibapi.ticktype import TickTypeEnum
from threading import Timer
import numpy as np
import pandas as pd
import threading
import time
from datetime import datetime
# from Strategies._SB4 import *
# from Strategies._SB3 import *
# from Strategies._SB2 import *
import logging
# from ..Backtest_Python.AllStrategies import *
import sys
sys.path.append('/Users/apple/Documents/code/Python/backtest')
from AllStrategies import *
import os
import csv
import configparser
import json

class TestApp(EWrapper,EClient):
    def __init__(self):
        EClient.__init__(self,self)
        
        df_order=pd.read_csv('/Users/apple/Documents/code/Python/IB-native-API/Output/Orders.csv')
        df_order=df_order.values.tolist()
        self.order=[]
        for i in range(len(df_order)):
            self.order.insert(len(self.order),df_order[i][0].upper())
        
        # self.order=['BUY CADJPY','BUY USDNOK','BUY USDDKK','SELL GBPCAD','SELL XAUUSD']    
        self.pair=[]
        self.direction=[]
        
        for i in self.order:
            a=i.split()
            # print(a)
            if a[0].upper() in ['BUY','SELL']:
                for j in range(1,len(a)):
                    self.pair.append(a[j].upper())
                    self.direction.append(a[0].upper())
            else:
                input('Wrong action!!!')
        
        # print(self.pair)
        # print(self.direction)
        
        # c=input('xxxx')
        
        # for i in range(len(self.order)):   
        #     if 'BUY' in self.order[i].upper():
        #         self.pair.append(self.order[i][4:].upper())
        #         self.direction.append(self.order[i][:3].upper())
        #     elif 'SELL' in self.order[i].upper():
        #         self.pair.append(self.order[i][5:].upper())
        #         self.direction.append(self.order[i][:4].upper())
                
        # self.pair=['USDNOK','GBPCAD','CADJPY','EURUSD','XAUUSD']
        # self.direction=['BUY','SELL','BUY','SELL','SELL']

        config=configparser.ConfigParser()
        config.read('/Users/apple/Documents/code/Python/IB-native-API/Output/config.cfg')
        self.BetAmout=float(config.get('MM','BetAmout'))
        self.rr=float(config.get('MM','rr'))
        self.mode=config.get('MM','mode') 
        self.period=int(config.get('MM','period')) #3m K
        
        self.StrategyType='API'  # 告訴策略用API方式來處理訊號
        self.size=1
        self.nextOrderId=0
        self.isUSstock=False
        # self.isUSstock=True
        self.isEUstock=False
        self.data = {} #Historical
        self.data1 = {} #Update
        self.df={} # Historical
        self.df1={} #Update 
        # resample method dictionary
        self.res_dict = {
            'Open':'first',
            'High':'max',
            'Low':'min',
            'Close': 'last',
            'Volume': 'sum'
            }
        self.now_date=np.nan
        self.pre_date=np.nan

        self.signal={} # For placing Bracket Order
        
        self.entryprice={}
        self.tp={}
        self.sl={}
        self.position={}
        self.AvgCost={}
        self.OrderPlaced={}
        self.LastReceivedDataTime=int(datetime.now().timestamp())
        self.LastOrderTime={}
        
        self.LastRealizedPnl=np.nan
        self.RealizedPnl=np.nan
        self.d=1
        # self.permId2ord=[]
        self.EntryPrice=np.nan
        self.EntryTime=int(datetime.now().timestamp())
        
        self.LastAction=False
        
        self.st=Strategies(self.StrategyType)
        self.rm=RiskManage(self.StrategyType,self.rr)
        
        self.info={}
        self.QuoteContract={}
        self.OrderContract={}
        self.qty={}
        self.reqId=0
        
        self.isBusy=False
        self.ConversionRate={'USD':1.0}
        
        # self.all_positions0 = pd.DataFrame([], columns = ['Symbol', 'Sec Type','Quantity', 'Average Cost']) 
        self.all_positions = pd.DataFrame([], columns = ['Symbol', 'Sec Type','Quantity', 'Average Cost','UnrealizedPNL','RealizedPNL']) 
        # self.all_positions=self.all_positions.set_index('Symbol')
        # self.all_CompletedOrders = pd.DataFrame([], columns = ['Symbol','Currency', 'Sec Type','Quantity']) 
        # self.PnL=[]
        self.trade={}
        self.open_trade={}
        self.lep={}
        self.ltp={}
        self.lsl={}
        self.sep={}
        self.stp={}
        self.ssl={}
        self.j=0
        
        
        
        self.FX_cfd=['AUDCAD','AUDCHF','AUDJPY','AUDNZD','AUDUSD','CADCHF','CADJPY','CHFJPY','EURAUD','EURCAD','EURCHF','EURGBP','EURJPY',
                     'EURNZD','EURUSD','GBPAUD','GBPCAD','GBPCHF','GBPJPY','GBPNZD','GBPUSD','NZDCAD','NZDCHF','NZDJPY','NZDUSD','USDCAD',
                     'USDCHF','USDJPY','USDRUB','USDSEK','USDHUF','USDCNH','USDCZK','USDDKK','USDHKD','USDMXN','USDNOK','USDPLN','USDSGD',
                     'USDTRY','USDZAR','GBPZAR','EURZAR','GBPSGD','GBPPLN','ZARJPY','SGDJPY','EURHUF','GBPHKD','EURPLN','EURNOK','GBPSGD']
        self.Index_cfd=['IBUS500','IBUS30','IBUST100','IBGB100','IBEU50','IBDE30','IBFR40','IBES35','IBNL25','IBCH20','IBJP225','IBHK50','IBAU200']
        self.Index_currency={'IBUS500':'USD','IBUS30':'USD','IBUST100':'USD','IBGB100':'GBP','IBEU50':'EUR','IBDE30':'EUR','IBFR40':'EUR','IBES35':'EUR',
                             'IBNL25':'EUR','IBCH20':'CHF','IBJP225':'JPY','IBHK50':'HKD','IBAU200':'AUD'}
        self.Metal_cfd=['XAUUSD','XAGUSD']
        
    
        
        for pair in range(len(self.pair)):
            # self.QuoteContract[pair]={}
            # self.OrderContract[pair]={}
            self.info[pair]={}
            
            self.data[pair] = [] #Historical
            self.data1[pair] = [] #Update
            self.df[pair]=[] # Historical
            self.df1[pair]=[] #Update 
            
            self.position[pair]=0.0
            self.AvgCost[pair]=0.0
            
            self.signal[pair]=False
            
            self.entryprice[pair]=np.nan
            self.tp[pair]=np.nan
            self.sl[pair]=np.nan
            
            self.OrderPlaced[pair]=0
            
            self.LastOrderTime[pair]=int(datetime.now().timestamp())-5*self.period*60
            # self.ConversionRate[pair]=1.0
            
            self.trade[pair]={}
            self.open_trade[pair]=[]
             
            if self.pair[pair] in self.FX_cfd:
                self.QuoteContract[pair]=self.cash(self.pair[pair])
                self.OrderContract[pair]=self.cashCFD(self.pair[pair])
                self.qty[pair]=5000
                
                if ('JPY' in self.pair[pair]) or (self.pair[pair]=='USDHUF'):
                    self.info[pair]={
                    'size':float(self.size)*float(100),
                    'pip':0.01,
                    'round':2
                    }
                
                elif 'USDCZK' in self.pair[pair]:
                    self.info[pair]={
                    'size':float(self.size)*float(1000),
                    'pip':0.001,
                    'round':3
                    }
                    
                else:
                    self.info[pair]={
                    'size':float(self.size)*float(10000),
                    'pip':0.0001,
                    'round':4
                    }
                
                
                
            elif self.pair[pair] in self.Index_cfd:
                self.QuoteContract[pair]=self.indexCFD(self.pair[pair])
                self.OrderContract[pair]=self.indexCFD(self.pair[pair])
                
                self.qty[pair]=1
                self.info[pair]={
                'size':float(self.size),
                'pip':0.01,
                'round':2
                }
                
            
            elif self.pair[pair] in self.Metal_cfd:
                self.QuoteContract[pair]=self.metalCFD(self.pair[pair])
                self.OrderContract[pair]=self.metalCFD(self.pair[pair])
                self.qty[pair]=1
                if 'XAG' in self.pair[pair]:
                    self.info[pair]={
                    'size':float(self.size),
                    'pip':0.0001,
                    'round':4
                    }
                else:    
                    self.info[pair]={
                    'size':float(self.size),
                    'pip':0.01,
                    'round':2
                    }
            else:
                input('Wrong Symbol!!!')
                
            
            # if self.isUSstock==True:
            #     self.QuoteContract[pair]=self.USStockAtSmart(self.pair[pair])
            #     self.OrderContract[pair]=self.USStockCFD(self.pair[pair])
            #     self.qty[pair]=100
            #     self.info[pair]={
            #     'size':float(self.size),
            #     'pip':0.01,
            #     'round':2
            #     }
                
            
            # if self.isEUstock==True:
            #     self.QuoteContract[pair]=self.EuropeanStockCFD(self.pair[pair])
            #     self.OrderContract[pair]=self.EuropeanStockCFD(self.pair[pair])
            #     self.qty[pair]=100
            #     self.info[pair]={
            #     'size':float(self.size),
            #     'pip':0.01,
            #     'round':2
            #     }
                
            self.all_positions.loc[self.pair[pair]]=self.pair[pair],self.OrderContract[pair].secType,0.0,0.0,0.0,0.0
            df_trade=pd.DataFrame(self.trade)
            df_trade.to_csv('/Users/apple/Documents/code/Python/IB-native-API/Output/trades.csv',sep=' ',index=1 )   
        
                
            
            # if self.OrderContract[pair].currency!='USD':
                
                
                # self.reqMarketDataType(1) #if live not available,switch to delayed-forzen data.
                # self.reqMktData(1004,self.QuoteContract[pair],"",False,False,[])
                # self.reqMktData(1002, self.QuoteContract[pair], "", True, False, [])
                # self.reqMktData(pair,self.QuoteContract[pair],"",False,False,[])
                
                # self.reqRealTimeBars(pair, self.QuoteContract[pair], 5, "MIDPOINT", False, [])
                
            
            # print('Pair: ',self.pair[pair],'pip:',self.info[pair].get('pip'),'minTick:',self.info[pair].get('minTick'))
            # print(self.OrderContract[pair])    
            
            # print('OrderContract:',self.QuoteContract[pair].symbol,self.QuoteContract[pair].currency)
            
                
        return

    def error(self,reqId,errorCode,errorString):
        
        if errorCode==2104 or errorCode==2106 or errorCode==2158 or errorCode==300:
            return
            
            
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Error: ',reqId,' ',errorCode,' ',errorString)   
        # if errorCode==202:
            # self.reqCompletedOrders(True)
        
        return

    def historicalData(self,reqId,bar):
        self.data[reqId].append([bar.date, bar.open,bar.high,bar.low,bar.close,bar.volume])
        self.now_date=int(bar.date)
        return
         
    def historicalDataEnd(self, reqId, start: str, end: str):
        self.data1[reqId].append(self.data[reqId][-1])
        del self.data[reqId][-1]
        self.df[reqId] = pd.DataFrame(self.data[reqId],columns=['DateTime','Open','High','Low', 'Close','Volume'])
        self.df[reqId]['DateTime'] = pd.to_datetime(self.df[reqId]['DateTime'],unit='s')
        dfPath='/Users/apple/Documents/code/Python/IB-native-API/Output/df'+str(reqId)+'.csv'
        # print(dfPath)
        self.df[reqId].to_csv(dfPath,index=0 ,float_format='%.5f')   
        self.data[reqId]=[] #清掉是否有助於記憶體的節省？
        super().historicalDataEnd(reqId, start, end)
        # print( datetime.fromtimestamp(int(datetime.now().timestamp())),'HistoricalDataEnd. ReqId:', reqId, 'from', start, 'to', end)
        # if 'IB' in self.OrderContract[reqId].symbol[:2]:
        #     return
        self.reqContractDetails(reqId, self.OrderContract[reqId])
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Conversion Rate:',self.ConversionRate)
        return

    def historicalDataUpdate(self, reqId: int, bar):
        self.data1[reqId].append([bar.date,bar.open,bar.high,bar.low,bar.close,bar.volume])
        self.LastReceivedDataTime=int(datetime.now().timestamp())
        self.df1[reqId] = pd.DataFrame(self.data1[reqId],columns=['DateTime','Open','High','Low', 'Close','Volume'])
        self.df1[reqId]['DateTime'] = pd.to_datetime(self.df1[reqId]['DateTime'],unit='s') 
        self.df1[reqId]=self.df1[reqId].set_index('DateTime')
        # self.df1[reqId].to_csv('/Users/apple/Documents/code/Python/IB-native-API/df['+str(reqId)+'].csv',index=0 ,float_format='%.5f')  
        self.pre_date=self.now_date #Calculate the bar.date and previous bar.date
        self.now_date=int(bar.date)
        
        if self.now_date != self.pre_date : #Resample once after the bar closed
            res_df=self.df1[reqId].resample(str(self.period)+'min', closed='left', label='left').agg(self.res_dict)
            del self.data1[reqId][0:len(self.data1[reqId])-1]
            res_df.drop(res_df.index[-1], axis=0, inplace=True) #delete the new open bar at lastest appended row
            # res_df.to_csv('/Users/davidliao/Documents/code/Github/IB-native-API/data/3K.csv', mode='a', header=False,float_format='%.5f')
            # print('Resampled',datetime.fromtimestamp(self.now_date-60*self.period))
            res_df.reset_index(inplace=True) 

            # self.df[reqId] = self.df[reqId].append(res_df, ignore_index=True) 
            # pd.concat([df1, df2, df3])
            self.df[reqId]=pd.concat([self.df[reqId], res_df],ignore_index=True)
            
            self.df[reqId].to_csv('/Users/apple/Documents/code/Python/IB-native-API/Output/df'+str(reqId)+'.csv',index=0 ,float_format='%.5f')  
            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'self.position=',self.position)
            # if self.position == 0.0 and  int(datetime.now().timestamp())-self.LastOrderTime>self.period*60:        
            
            # if self.position[reqId] == 0.0 and bar.close>self.AvgCost[reqId] and self.OpenOrder[reqId]==0 and int(datetime.now().timestamp())-self.LastOrderTime[reqId]>5*self.period:
            # if self.position[reqId] == 0.0 and bar.close>self.AvgCost[reqId] and int(datetime.now().timestamp())-self.LastOrderTime[reqId]>5*self.period and self.OrderPlaced[reqId]==0:
            # print(reqId)
            # print(self.all_positions.loc[self.pair[reqId]])
            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Quantity:',self.all_positions.loc[self.pair[reqId],'Quantity'])
            # print(reqId,self.all_positions.loc[self.pair[reqId],'Quantity'])
            # if self.all_positions.loc[self.pair[reqId],'Quantity']==0.0 and bar.close>self.all_positions.loc[self.pair[reqId],'Average Cost'] and int(datetime.now().timestamp())-self.LastOrderTime[reqId]>5*self.period:
            if self.all_positions.loc[self.pair[reqId],'Quantity']==0.0 and bar.close>self.all_positions.loc[self.pair[reqId],'Average Cost'] and int(datetime.now().timestamp())-self.LastOrderTime[reqId]>5*self.period*60:
                
                # self.signal,self.qty,self.entryprice,self.tp,self.sl=SB(self.df,self.d,self.direction) # Call _SB3.py
                # self.signal,self.qty,self.entry price,self.tp,self.sl=SB(self.df,self.d) # Call _SB2.py
                # self.signal,self.qty,self.entryprice,self.tp,self.sl=SB(self.df) # Call _SB4.py
            
                # self.signal,self.tp,self.sl,self.df=self.st._RSI(self.df,len(self.df)-1)
                
                # print(self.signal,'|',self.tp,'|',self.sl)
                
                # print('-----------------------')
                self.signal[reqId]=self.st._RSI(self.df[reqId],len(self.df[reqId])-1,reqId)
                
                
                # if self.signal != False:
                    
                #     print(self.signal)
                
                #     self.tp=self.rm.TP(self.df,self.info,self.signal,self.rr,len(self.df)-1)
                #     print(self.tp)
                
                #     self.sl=self.rm.SL(self.df,self.info,self.signal,len(self.df)-1)
                #     print(self.sl)
                
                
                # self.tp,self.sl,self.df=RmFunc_list.get(risks_list[risk])()
                # if self.signal != False: # if entry signal produced and check no position then entry
                if self.signal[reqId] == self.direction[reqId]: # if entry signal produced and check no position then entry
                    while self.isBusy:
                        time.sleep(1)
                    self.tp[reqId]=self.rm.TP(self.df[reqId],self.info[reqId],self.signal[reqId],self.rr,len(self.df[reqId])-1)
                    self.sl[reqId]=self.rm.SL(self.df[reqId],self.info[reqId],self.signal[reqId],len(self.df[reqId])-1)
                    self.entryprice[reqId]=round(bar.close,self.info[reqId].get('round'))
                    # print(self.OrderContract[reqId],self.ConversionRate)
                    
                    # self.qty[reqId]=max(1,round(self.BetAmout/(abs(self.entryprice[reqId]-self.sl[reqId])/self.ConversionRate[reqId]),0))
                    self.qty[reqId]=max(1,round(self.BetAmout/(abs(self.entryprice[reqId]-self.sl[reqId])/self.ConversionRate[self.OrderContract[reqId].currency]),0))
                    
                    self.reqId=reqId
                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),'historicalDataUpdate reqId:',self.reqId,'Symbol:',self.pair[self.reqId],'current positions:',self.position[reqId],self.signal[reqId],'Entry:',self.entryprice[reqId],'Quantity:',self.qty[reqId],'TP:',self.tp[reqId],'SL:',self.sl[reqId])
                    # self.isBusy=True
                    # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Busy:',self.isBusy)
                    self.start()       
        return
    
    def tickPrice(self,reqId,tickType,price,attrib):
        self.ConversionRate[self.OrderContract.currency]=price
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.OrderContract[reqId].symbol+self.OrderContract[reqId].currency,'Conversion Rate:',self.ConversionRate[self.OrderContract.currency])
        self.cancelMktData(reqId)
        return	
    
    def realtimeBar(self, reqId, time:int, open_: float, high: float, low: float, close: float,volume, wap, count: int):
        super().realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)
        if not self.OrderContract[reqId].currency in self.ConversionRate:
            if self.OrderContract[reqId].currency in ['EUR','GBP','AUD','NZD']:
                self.ConversionRate[self.OrderContract[reqId].currency]=1/close
            else:
                self.ConversionRate[self.OrderContract[reqId].currency]=close
            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'realtimeBar:',self.OrderContract[reqId].currency,'Conversion Rate:',self.ConversionRate[self.OrderContract[reqId].currency])
            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Conversion Rate:',self.ConversionRate)
            a=[]
            a.append(self.ConversionRate)
            df=pd.DataFrame(a)
            df.to_csv('/Users/apple/Documents/code/Python/IB-native-API/Output/ConversionRate.csv',index=0 )  
            self.cancelRealTimeBars(reqId)
        return
    
    
    # def nextValidId(self,orderId):
    #     self.nextOrderId=orderId
    #     print(datetime.fromtimestamp(int(datetime.now().timestamp())),"NextValidId:", orderId)
    #     return

    def start(self):
        # OrderContract = Contract() # Contract
        # OrderContract.symbol = self.pair[:3]
        # OrderContract.secType = "CFD" 
        # OrderContract.currency = self.pair[3:]
        # OrderContract.exchange = "SMART" 
        
        # self.OrderContract=self.cashCFD(self.pair)
        # print('Order',self.OrderContract.currency)
             
        bracket = self.BracketOrder(self,self.nextOrderId, self.signal[self.reqId], self.qty[self.reqId], self.entryprice[self.reqId], self.tp[self.reqId], self.sl[self.reqId]) # Order
        for o in bracket:
            self.placeOrder(o.orderId, self.OrderContract[self.reqId], o)
            self.nextOrderId # need to advance this we’ll skip one extra oid, it’s fine
            # time.sleep(5)
            
            # self.position[self.reqId]+=self.qty[self.reqId]
            # self.AvgCost[self.reqId]=self.entryprice[self.reqId]
        
        self.LastAction=self.signal[self.reqId]
        self.reqIds(-1)
        self.OrderPlaced[self.reqId]=1
        # print('self.OpenOrder[self.reqId]',self.OpenOrder[self.reqId])

        #Update Portfolio
        
        # self.reqAccountUpdates(True,"") 
        
        return

    
    
    def cash(self,symbol):
        contract = Contract()
        contract.symbol = symbol[:3]
        contract.secType = 'CASH'
        # contract.secType = 'CFD'  #if CFD
        contract.currency = symbol[3:]
        contract.exchange = 'IDEALPRO'
        # contract.exchange = 'SMART'  #if CFD
        return contract
    
    def cashCFD(self,symbol):
        contract = Contract()
        contract.symbol = symbol[:3]
        # contract.secType = 'CASH'
        contract.secType = 'CFD'  #if CFD
        # contract.exchange = 'IDEALPRO'
        contract.currency = symbol[3:]
        contract.exchange = 'SMART'  #if CFD 
        return contract
    
    def indexCFD(self,symbol):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'CFD'
        contract.currency = self.Index_currency.get(symbol)
        contract.exchange = 'SMART'
        return contract
    
    def metalCFD(self,symbol):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'CMDTY'
        contract.currency = symbol[3:]
        contract.exchange = 'SMART'
        return contract
    
    def USStockAtSmart(self,symbol):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.currency = "USD"
        contract.exchange = "SMART"
        return contract
    
    def USStockCFD(self,symbol):
        # ! [usstockcfd_conract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "CFD"
        contract.currency = "USD"
        contract.exchange = "SMART"
        # ! [usstockcfd_conract]
        return contract
    
    def EuropeanStockCFD(self,symbol):
        # ! [europeanstockcfd_contract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "CFD"
        contract.currency = "EUR"
        contract.exchange = "SMART"
        # ! [europeanstockcfd_contract]
        return contract
    
    def xxxUSD(self,symbol):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = 'CASH'
        # contract.secType = 'CFD'  #if CFD
        contract.currency = 'USD'
        contract.exchange = 'IDEALPRO'
        # contract.exchange = 'SMART'  #if CFD
        return contract
    
    def USDxxx(self,symbol):
        contract = Contract()
        contract.symbol = 'USD'
        contract.secType = 'CASH'
        # contract.secType = 'CFD'  #if CFD
        contract.currency = symbol
        contract.exchange = 'IDEALPRO'
        # contract.exchange = 'SMART'  #if CFD
        return contract
    
    
    @staticmethod
    def BracketOrder(self,
        parentOrderId, #OrderId
        action,  #'BUY' or 'SELL'
        quantity,  #quantity of order
        limitPrice,  # Entry Price
        takeProfitLimitPrice,  # Exit price
        stopLossPrice # Stop-loss price
        ):

        #This will be our main or “parent” order
        parent = Order()
        parent.orderId = parentOrderId
        parent.action = action
        parent.orderType = 'MKT' #直接下market 單不用擔心沒成交的問題？
        # parent.orderType = 'LMT' #直接下market 單不用擔心沒成交的問題？
        parent.totalQuantity = quantity
        parent.lmtPrice = limitPrice
        #The parent and children orders will need this attribute set to False to prevent accidental executions.
        #The LAST CHILD will have it set to True, 
        parent.transmit = False
        self.EntryPrice=limitPrice
        self.EntryTime=int(datetime.now().timestamp())

        takeProfit = Order()
        takeProfit.orderId = parent.orderId + 1
        takeProfit.action = 'SELL' if action == 'BUY' else 'BUY'
        takeProfit.orderType = 'LMT'
        takeProfit.totalQuantity = quantity
        takeProfit.lmtPrice = takeProfitLimitPrice
        takeProfit.parentId = parentOrderId
        takeProfit.transmit = False
        

        stopLoss = Order()
        stopLoss.orderId = parent.orderId + 2
        stopLoss.action = 'SELL' if action == 'BUY' else 'BUY'
        stopLoss.orderType = 'STP'
        #Stop trigger price
        stopLoss.auxPrice = stopLossPrice
        stopLoss.totalQuantity = quantity
        stopLoss.parentId = parentOrderId
        #In this case, the low side order will be the last child being sent. Therefore, it needs to set this attribute to True 
        #to activate all its predecessors
        stopLoss.transmit = True
        bracketOrder = [parent, takeProfit, stopLoss]
        return bracketOrder
    
    def execDetails(self, reqId: int, contract: Contract, execution):
        super().execDetails(reqId, contract, execution)
        
        '''
        Watchout,the reqId of execDetails is different with historicalData
        
        '''
        
        self.isBusy=False
        
        sym=''
        
        if 'IB' in contract.symbol[:2] and contract.symbol in self.pair:
            sym=contract.symbol
        elif contract.symbol+contract.currency in self.pair:
            sym=contract.symbol+contract.currency
        elif contract.symbol in self.pair:
            sym=contract.symbol
        else:
            # print('execDetails:Error sym:',contract.symbol,contract.currency)
            return
        
        # print('sym:',sym)
        self.reqId=self.pair.index(sym)
        # print('pair:',self.reqId)
        
            
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),"ExecDetails. ReqId:", reqId, "Symbol:", sym, "SecType:", contract.secType, 'Side:',execution.side,'Shares:',execution.shares,'Price:',execution.price)
        # self.all_positions.loc[sym]=sym,contract.secType,self.all_positions.loc[sym,'Quantity']+execution.shares if execution.side=='BOT' else self.all_positions.loc[sym,'Quantity']-execution.shares,execution.price if execution.cumQty!=0 else 0.0
        self.LastOrderTime[self.reqId]=int(datetime.now().timestamp()) 
        
        if (execution.side=='BOT' and self.direction[self.reqId]=='BUY') or (execution.side=='SLD' and self.direction[self.reqId]=='SELL'): 
            # print('0:',self.df[pair])
            # print('1:',self.df[pair].iloc[-1,0])
            # print('2:',self.df[self.reqId].loc[self.df[self.reqId].index[-1],'DateTime'])
            # print('3:',self.df[pair].loc[self.df[pair].index[len(self.df[pair])-1],'DateTime'])
            # print('4:',self.df[pair].loc[-1,'DateTime'])
            self.j=len(self.df[self.reqId])-1
            self.trade[self.reqId][self.j]={'ID':self.j,
                             'DateTime':self.df[self.reqId].loc[self.df[self.reqId].index[-1],'DateTime'],
                             'Symbol':self.pair[self.reqId],
                             'Side':'BUY' if execution.side=='BOT' else 'SELL',
                             'EntryPrice':execution.avgPrice,
                             'Position':execution.cumQty,
                             'ExitPrice':0.0,
                             'Realized PNL':0.0,
                             'Commision':0.0,
                             'TP':self.tp[self.reqId],
                             'SL':self.sl[self.reqId]
                             }
            # print(self.trade[pair])
            
            self.open_trade[self.reqId].append(self.j)
            
            # print(self.open_trade[self.reqId])
            
        else:
            try:
                for j in self.open_trade[self.reqId]:
                    self.j=j
                    # self.trade[self.reqId][self.j].update({'PnL':'commisionReport'})
                    self.trade[self.reqId][self.j].update({'Position':0})
                    self.trade[self.reqId][self.j].update({'ExitPrice':execution.price})
                    
                    # print(self.trade[self.reqId][self.j])
                    self.open_trade[self.reqId].remove(self.j)
                    # print('open_trade[pair]:',self.open_trade[self.reqId])
            except KeyError:
                return
            
                
                 
            
            
            
            # 'last_price':round(df[reqId]['Close'][i],self.info[reqId].get('round'))
        
        

            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'execDetails:','reqId',reqId,'self.reqId',self.reqId,'Symbol:',contract.symbol,'Currency:',contract.currency,'SecType:',contract.secType,'Price:', execution.avgPrice,'CumQty:',execution.cumQty)       
        # self.reqAccountUpdates(True,"") 
        # self.reqPositions()
        # self.reqOpenOrders()	
        # self.reqAutoOpenOrders(True)	
        
        
        
        # for pair in range(len(self.pair)):
        #     if self.OrderContract[pair].symbol==contract.symbol and self.OrderContract[pair].currency==contract.currency and self.OrderContract[pair].secType==contract.secType:
        
        #         if (execution.side=='BOT' and self.direction[pair]=='SELL') or (execution.side=='SLD' and self.direction[pair]=='BUY'):
        #             self.LastOrderTime[pair]=int(datetime.now().timestamp())
        #             self.position[pair]=0.0
        #             self.AvgCost[pair]=0.0
                    
        #         elif (execution.side=='BOT' and self.direction[pair]=='BUY') or (execution.side=='SLD' and self.direction[pair]=='SELL'):
        #             self.position[pair]=execution.cumQty if execution.side=='BOT' else -1*execution.cumQty
        #             self.AvgCost[pair]=execution.avgPrice
                    
        #         self.all_positions.loc[self.pair[pair]]=self.pair[pair],self.OrderContract[pair].secType,self.position[pair],self.AvgCost[pair]   
        #         print(self.all_positions)
        
        
        
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Busy:',self.isBusy)
        return
    
    def execDetailsEnd(self, reqId: int):
        super().execDetailsEnd(reqId)
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),"ExecDetailsEnd. ReqId:", reqId)
        # self.reqAccountUpdates(True,"")
        # time.sleep(3)
        # self.reqAccountUpdates(False,"")
        return    
    
    
    def nextValidId(self,orderId):
        super().nextValidId(orderId)
        # logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextOrderId=orderId
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),"NextValidId:", orderId)
        return
    
    # def nextValidId(self, orderId: int):
    #     super().nextValidId(orderId)
    #     # logging.debug("setting nextValidOrderId: %d", orderId)
    #     self.nextValidOrderId = orderId
    #     print("NextValidId:", orderId)
    
    def updatePortfolio(self,contract:Contract,position:float,marketPrice:float,marketValue:float,averageCost:float,unrealizedPNL:float,realizedPNL:float,accountName:str):
            
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'UpdatePortfolio.','Symbol:',contract.symbol,'SecType:',contract.secType,'Exchange:',contract.exchange,'Position:',position,'MarketPrice:',marketPrice,'MarketValue:',marketValue,'AverageCost:',averageCost,'UnrealizedPNL:',unrealizedPNL,'RealizedPNL:',realizedPNL,'AccountName:',accountName)
        # print(accountName)
        
        sym=''
        # if 'IB' in contract.symbol[:2] and contract.symbol in self.pair and position!=0.0:
        if 'IB' in contract.symbol[:2] and contract.symbol in self.pair:
            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Positions:',contract.symbol,contract.secType,'Position:',position,'Average Cost:',averageCost)
            sym=contract.symbol
        elif contract.symbol+contract.currency in self.pair:
        # elif contract.symbol+contract.currency in self.pair and position!=0.0:
            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Positions:',contract.symbol+contract.currency,contract.secType,'Position:',position,'Average Cost:',averageCost)
            sym=contract.symbol+contract.currency
        elif contract.symbol in self.pair:
            # print(  datetime.fromtimestamp(int(datetime.now().timestamp())),'Positions:',contract.symbol,contract.secType,'Position:',position,'Average Cost:',averageCost)
            sym=contract.symbol
        else:
            # print('updatePortfolio:Error sym:',contract.symbol,contract.currency)
            return    
        
        # pair=self.pair.index(sym)
        try:
            self.all_positions.loc[sym]=sym,contract.secType,position,averageCost,round(unrealizedPNL/self.ConversionRate[contract.currency],2),round(realizedPNL/self.ConversionRate[contract.currency],2)
            self.all_positions.to_csv('/Users/apple/Documents/code/Python/IB-native-API/Output/all_positions.csv',index=0 )  
        except KeyError:
            return
        
        
        

        # for pair in range(len(self.pair)):
        #     if self.OrderContract[pair].symbol==contract.symbol and self.OrderContract[pair].currency==contract.currency and self.OrderContract[pair].secType==contract.secType:
        #         # self.position[pair]=position
        #         # self.AvgCost[pair]=averageCost
                
        #         if self.position[pair]!=0.0: 
        #             print('Pair:',self.pair[pair],contract.secType,'Position:',position,'Average Cost:',averageCost)
        #         self.all_positions0.loc[self.pair[pair]]=self.pair[pair],self.OrderContract[pair].secType,position,averageCost
                # print(self.all_positions0.loc[self.pair[pair]])
                
                # self.OpenOrder[pair]=0
                
        # if self.OrderContract[self.reqId].symbol==contract.symbol and self.OrderContract[self.reqId].currency==contract.currency and self.OrderContract[self.reqId].secType==contract.secType:
            
            # print('self.OrderContract[self.reqId].symbol',self.OrderContract[self.reqId].symbol,'contract.symbol',contract.symbol)
            # print('self.OrderContract[self.reqId].currency',self.OrderContract[self.reqId].currency,'contract.currency',contract.currency)
            # self.position[self.reqId]=position
            # self.AvgCost[self.reqId]=averageCost
           
            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'UpdatePortfolio:','self.reqId',self.reqId,'Symbol:',contract.symbol,'Currency:',contract.currency,'SecType:',contract.secType,'Position:',position,'MarketPrice:',marketPrice,'MarketValue:',marketValue,'AverageCost:',averageCost,'UnrealizedPNL:',unrealizedPNL,'RealizedPNL:',realizedPNL,'AccountName:',accountName)
            
            # print('self.position[self.reqId]',self.position[self.reqId],'self.AvgCost[self.reqId]',self.AvgCost[self.reqId])
            # print('updatePortfolio:','self.OrderContract[self.reqId].symbol',self.OrderContract[self.reqId].symbol,'self.OrderContract[self.reqId].currency',self.OrderContract[self.reqId].currency,'self.OrderContract[self.reqId].exchange',self.OrderContract[self.reqId].exchange)

        
            # print('not match','self.reqId',self.reqId,'Symbol:',contract.symbol,'Currency:',contract.currency,'SecType:',contract.secType,'Exchange:',contract.exchange,'Position:',position,'AverageCost:',averageCost,'self.position[self.reqId]',self.position[self.reqId],'self.AvgCost[self.reqId]',self.AvgCost[self.reqId],'self.OpenOrder[self.reqId]',self.OpenOrder[self.reqId])
            
            
        # elif self.OrderContract[reqId].symbol==contract.symbol and self.OrderContract[reqId].currency== contract.currency:
            
        return

    # def position(self, account: str, contract: Contract, position: float,avgCost: float):
    #     super().position(account, contract, position, avgCost)
        # print("Position.", "Account:", account, "Symbol:", contract.symbol, "SecType:",contract.secType, "Currency:", contract.currency,"Position:", position, "Avg cost:", avgCost)
        # print('This is position callback')
        # for pair in range(len(self.pair)):
        #     if self.OrderContract[pair].symbol==contract.symbol and self.OrderContract[pair].currency==contract.currency and self.OrderContract[pair].secType==contract.secType:
        #         self.posion[pair]=position
        #         self.AvgCost[pair]=avgCost
        #         self.LastOrderTime[self.reqId]=int(datetime.now().timestamp())
                    
        # self.cancelPositions() 
        
        return

    # def positionEnd(self):
    #     super().positionEnd()
    #     print("PositionEnd")
    #     return
    
    # def position(self, account, contract, pos, avgCost):
    #     print('This is position callback')

    # def positionEnd(self):
    #     # self.disconnect()
    #     print('end')
    
    def commissionReport(self, commissionReport: CommissionReport):
        super().commissionReport(commissionReport)
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),"CommissionReport.", commissionReport)
        
        self.RealizedPnl=commissionReport.realizedPNL
        self.LastRealizedPnl=self.RealizedPnl
        
        # if self.position==0 and commissionReport.realizedPNL<0:
        
        #self.all_positions.to_csv('/Users/apple/Documents/code/Python/IB-native-API/Output/all_positions.csv',index=0 ,float_format='%.2f')  
        
        if commissionReport.realizedPNL<1000000:
            try:
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),'commissionReport:',self.pair[self.reqId],'SecType:',self.OrderContract[self.reqId].secType,'realizedPNL:',round(commissionReport.realizedPNL/self.ConversionRate[self.OrderContract[self.reqId].currency],2),'Commission:',round(commissionReport.commission/self.ConversionRate[self.OrderContract[self.reqId].currency],2))
                self.trade[self.reqId][self.j].update({'Realized PNL':round(commissionReport.realizedPNL/self.ConversionRate[self.OrderContract[self.reqId].currency],2)})
                # self.trade[self.reqId][self.j].update({'Commision':round(-commissionReport.commission,1)})
                self.trade[self.reqId][self.j]['Commision']=round(self.trade[self.reqId][self.j]['Commision']-commissionReport.commission/self.ConversionRate[self.OrderContract[self.reqId].currency],2)
                
            except KeyError:
                return

          
            # self.PnL.append(self.trade[self.reqId][self.j].get('PnL'))
            # print(self.PnL)
            # open the file in the write mode
            # f = open('/Users/apple/Documents/code/Python/IB-native-API/Output/PnL.csv', 'w')
            # create the csv writer
            # writer = csv.writer(f)
            # write a row to the csv file
            # writer.writerows([self.PnL])
            # close the file
            # f.close()

        
        else:
            try:
                # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'commissionReport:','realizedPNL:',-commissionReport.commission,commissionReport.currency)
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),'commissionReport:',self.pair[self.reqId],'SecType:',self.OrderContract[self.reqId].secType,'realizedPNL:',0.0,'Commission:',round(commissionReport.commission/self.ConversionRate[self.OrderContract[self.reqId].currency],2))
                # self.trade[self.reqId][self.j].update({'Commision':round(-commissionReport.commission,0)})
                self.trade[self.reqId][self.j]['Commision']=round(self.trade[self.reqId][self.j]['Commision']-commissionReport.commission/self.ConversionRate[self.OrderContract[self.reqId].currency],2)
                # self.trade[self.reqId][self.j].update({'PnL':round(-commissionReport.commission/self.ConversionRate[self.OrderContract[self.reqId].currency],0)})
                
            except KeyError:
                return
        
        # print(self.trade[self.reqId])
        a=[]
        for i in self.trade.keys():
            for j in self.trade[i].keys():
                a.append(self.trade[i][j])
        df_trade=pd.DataFrame(a)
        
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'df_trade',df_trade)
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'df_trade')
        # print(df_trade)
        df_trade.to_csv('/Users/apple/Documents/code/Python/IB-native-API/Output/trades.csv',sep=',',index=0 )   
        
        
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Direction:',self.direction)
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'The direction d:',self.d)
        
        # self.stop()
        return



    # def openOrder(self, orderId, contract: Contract, order: Order,orderState):
    #     super().openOrder(orderId, contract, order, orderState)
    #     print("OpenOrder. PermId: ", order.permId, "ClientId:", order.clientId, " OrderId:", orderId, 
    #     "Account:", order.account, "Symbol:", contract.symbol, "SecType:", contract.secType,
    #     "Exchange:", contract.exchange, "Action:", order.action, "OrderType:", order.orderType,
    #     "TotalQty:", order.totalQuantity, "CashQty:", order.cashQty, 
    #     "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status) 
    #     order.contract = contract
    #     self.permId2ord[order.permId] = order
    #     # print('self.permId2ord[order.permId]',self.permId2ord[order.permId])
        
    #     # if self.OrderContract[self.reqId].symbol==contract.symbol and self.OrderContract[self.reqId].currency==contract.currency and self.OrderContract[self.reqId].exchange==contract.exchange:
    #     #     self.OpenOrder[self.reqId]=1
                
    #     return
    
    # def orderStatus(self, orderId, status: str, filled,
    #                  remaining, avgFillPrice: float, permId: int,
    #                  parentId: int, lastFillPrice: float, clientId: int,
    #                  whyHeld: str, mktCapPrice: float):
    #     super().orderStatus(orderId, status, filled, remaining,
    #                          avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
    #     print("OrderStatus. Id:", orderId, "Status:", status, "Filled:", decimalMaxString(filled),
    #            "Remaining:", decimalMaxString(remaining), "AvgFillPrice:", floatMaxString(avgFillPrice),
    #            "PermId:", intMaxString(permId), "ParentId:", intMaxString(parentId), "LastFillPrice:",
    #            floatMaxString(lastFillPrice), "ClientId:", intMaxString(clientId), "WhyHeld:",
    #            whyHeld, "MktCapPrice:", floatMaxString(mktCapPrice))
    #     return

    
    def openOrderEnd(self):
        super().openOrderEnd()
        # print("OpenOrderEnd") 
        # logging.debug("Received %d openOrders", len(self.permId2ord)) 
        return
    
    def orderStatus(self, orderId, status: str, filled: float,
        remaining: float, avgFillPrice: float, permId: int,
        parentId: int, lastFillPrice: float, clientId: int,
        whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled, remaining,
        avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        # print("OrderStatus. Id:", orderId, "Status:", status, "Filled:", filled,"Remaining:", remaining, "AvgFillPrice:", avgFillPrice,"PermId:", permId, "ParentId:", parentId, "LastFillPrice:",lastFillPrice, "ClientId:", clientId, "WhyHeld:",whyHeld, "MktCapPrice:", mktCapPrice)
        return
    
    def completedOrder(self,contract:Contract,order:Order,orderState):
        # print('Contract',contract.symbol+contract.currency+contract.secType,'Order:',order,'orderState:',orderState)
        
        # for pair in range(len(self.pair)):
        #     if self.OrderContract[pair].symbol==contract.symbol and self.OrderContract[pair].currency==contract.currency and self.OrderContract[pair].secType==contract.secType:
        #         self.position[pair]=0.0
        #         self.AvgCost[pair]=0.0       
                
        # self.CompletedOrder=self.CompletedOrder.insert(0,contract)         
        
        return
    
    def completedOrdersEnd(self):
        # print('completeOrdersEnd')
        return		
    
    def contractDetails(self, reqId, contractDetails):
        # print(reqId, contractDetails.contract)# my version doesnt use summary
        # print(reqId, contractDetails.minTick)# my version doesnt use summary
        # print('contractDetails.contract',contractDetails.contract,'contractDetails.minTick', contractDetails.minTick,'contractDetails.marketRuleIds',contractDetails.marketRuleIds,'contractDetails.tradingHours',contractDetails.tradingHours,'contractDetails.liquidHours',contractDetails.liquidHours)# my version doesnt use summary
        
        self.info[reqId]['minTick']=contractDetails.minTick
        self.info[reqId]['marketRule']=contractDetails.marketRuleIds
        
        strr=str(self.info[reqId]['minTick'])
        
        self.info[reqId]['round'] = len(strr[strr.find('.') + 1:]) #Calculate the decimal
        
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'contractDetails reqId',reqId,self.direction[reqId]+' Pair: ',self.pair[reqId],'pip:',self.info[reqId].get('pip'),'minTick:','%f' % self.info[reqId].get('minTick'),'Round:',self.info[reqId]['round'],'MarketRule', contractDetails.marketRuleIds)
        # self.reqMarketRule(self.info[reqId].get('marketRule'))
        
        
        return

        
    def contractDetailsEnd(self, reqId):
        # print("ContractDetailsEnd. ", reqId)
        # this is the logical end of your program
        
        return
    
    def marketRule(self, marketRuleId: int, priceIncrements):
        super().marketRule(marketRuleId, priceIncrements)
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),"Market Rule ID: ", marketRuleId)
        for priceIncrement in priceIncrements:
            print(datetime.fromtimestamp(int(datetime.now().timestamp())),"Price Increment.", priceIncrement)

    def ifDataDelay(self):
        w=180
        while True:
            if int(datetime.now().timestamp()) - self.LastReceivedDataTime >w:
                # print(datetime.fromtimestamp(int(datetime.now().timestamp())),w,' sec delayed,last receieved:',datetime.fromtimestamp(self.LastReceivedDataTime))
                self.stop()
                time.sleep(3)
                while True:
                    if not self.isConnected():
                        print(datetime.fromtimestamp(int(datetime.now().timestamp())),w,' sec delayed,last receieved,Disconnected')
                        raise EOFError
                    time.sleep(10)
            time.sleep(10)
        return
    
    def stop(self):
        for pair in range(len(self.pair)):
            self.cancelHistoricalData(pair)
            time.sleep(1)
        self.done=True
        self.disconnect()
        return

def main():
    # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'main() run')
    app=TestApp()
    # app.connect('127.0.0.1',7497,1) # IB TWS
    app.connect('127.0.0.1',7497,0) # IB TWS paper account
    # app.connect('127.0.0.1',4002,0) # IB Gateway
    
    # QuoteContract = Contract()
    # QuoteContract.symbol = app.pair[:3]
    # QuoteContract.secType = "CASH" 
    # QuoteContract.currency = app.pair[3:]
    # QuoteContract.exchange = "IDEALPRO" 
    
    time.sleep(3)
    

    #Update Portfolio
    app.reqAccountUpdates(True,"") # update if open positions exist.
    # app.reqAccountUpdates(False,"") # update if open positions exist.
    # app.reqPositions()
    # app.reqPositions('DU1687304')
    # app.cancelPositions()				

    #request historical data
    
    for pair in range(len(app.pair)):
        app.reqHistoricalData(pair,app.QuoteContract[pair],'','1 W',str(app.period)+' mins','MIDPOINT',0,2,True,[])
        if not app.OrderContract[pair].currency in app.ConversionRate and app.OrderContract[pair].currency !='USD':
            # print(pair,':',app.OrderContract[pair].currency)
            # app.reqMarketDataType(1)
            # app.reqMktData(pair,app.QuoteContract[pair],"",False,False,[])
            
            if app.OrderContract[pair].currency in ['EUR','GBP','AUD','NZD']:
                QuoteContract=app.xxxUSD(app.OrderContract[pair].currency)
                app.reqRealTimeBars(pair, QuoteContract, 5, "MIDPOINT", False, [])
            else:
                QuoteContract=app.USDxxx(app.OrderContract[pair].currency)
                app.reqRealTimeBars(pair, QuoteContract, 5, "MIDPOINT", False, [])
            
        
        

            
            
    t = threading.Thread(target = app.ifDataDelay,name='CheckDelay')
    # t.setDaemon(True)
    t.daemon = True
    t.start()  
    app.run()

if __name__=="__main__":
    os.system('clear')
    while True:
        try:
            main()
        except EOFError as e:
            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'main() error due to :',type(e),e)
            time.sleep(1)
        time.sleep(10)