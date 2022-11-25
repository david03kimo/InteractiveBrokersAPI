'''
-----Finished
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
UNSET_DOUBLE
commision currency transform
realizedPNL to USD in updateportfolio and self.trade
pyramiding need close the trade then run
sl!=np.nan
reqUpdatePortfolio after executeDetails to update Unrealized and realized PNL
list convert to df after Bar time change ,check any errors
clear df_tick after resample
add IBAPI path to default
K bar time lag：use shioaji method
trade record disappered :write the trade record to csv:use shioaji tradeRecord csv.read csv：self.trade to_csv and read from csv can continiue previous position.restart the positions and trade：previous position ,Save the trade to csv,and read again,
add 2 timeframe to filt signal
filter every timeframe:2,3,4,5
df collum add direction
check all TFs missed direction of dataframe
all_trades is fail when not in pair exit.
ifMultiTimeFrame to toggle mode


-----testing----
2nd time signal entry,scale-in,modify order: trade:'last_price':if open_trade didn't work:check Cumulative Quantity
same_direction not fit chart:api timestamp local timezone:same_direction doesn't delete old.
daily restart and csv all gone：del open_trades record when empty：no opentrade
place 2 order:record the timedelta with pre-order to make beyond 10 secs.
xagusd error
SL/TP:at least 10 pips

-----To do
event trigger structure
try a test.openorder and orderstatus and completedOrder to get SL order and avoid order repeat. MKT2LMT,open order=0.network lag,send order but not yet execute,so send again at next bar.
realtime HTF/turn-off HTF
data resample structure.dict:symbol,action,mode,rr,bet,info(mintick),trade,self.trade and all_position combine and use dict. use for j in trade.keys():取代 for j in open_trade:,and considerate renew csv or add tradingview alert.
change self.trade and self.opentrade to df to csv and easy restart
re-read pair and re-reqHistoricalData function
historicalDataUpdate send double same order
updateprofolio by all_trades df:handle not in pair list positions.
report open order of SL to check：auto add SL to positions without SL order
alert at 2,3,4,5 TF ready to support manual trading:for screen stocks and stock options.
considerate margin availability
market close,open time,don't need to data lag and restart
test AUD:Take a look at Minimum Price Increment to see how you can use the MarketRuleIds field in the ContractDetails object and IBApi::EClient::reqMarketRule: 
volumn increment
hang cannot restart,use quqe,check ram and cpu，unlimit isBusy，que
Warning: Your order was repriced so as not to cross a related resting order
strange XAUUSD SL
nextOrderId plus ()
sync pyramiding and non-pyramiding trade dict items.
delete df out of date data in case too big.
if SL didn't execute
change UI:tradingview sent:'signal':buy/pyramiding,'symbol'into self.pair and historicalupdate.pair=0,if signal pair+=1.self.OrderContract[pair].schedulely re-read csv or tradingview,if new order,add symbol dict to run.
stocks CFD/options trading:need to subscribe market data streaming 


'''
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.commission_report import CommissionReport
from ibapi.order import *
from threading import Timer
import numpy as np
import pandas as pd
import threading
import time
from datetime import datetime,timedelta
import sys
sys.path.append('/Users/apple/Documents/code/Python/backtest')
from AllStrategies import *
import requests
import configparser
import json
import os

# multi-level dict transformation
def dictTransform(trade):
    dict={}
    lst=[]
    for key,value in trade.items():
        if '-' in str(key):
            lst=key.split('-')
            # print(lst)
            dict[int(lst[0])]={int(lst[1]):trade[key]} # level 2  to level 3 dict
            # print('level 2 dict to level 3')
        else:
            for key2 in value.keys():
                dict[str(key)+'-'+str(key2)]=value[key2]
            # print('level 3 dict to level 2')
            
    return dict

class TestApp(EWrapper,EClient):
    def __init__(self):
        EClient.__init__(self,self)
        
        # read orders
        df_order=pd.read_csv('/Users/apple/Documents/code/Python/IBAPI/Settings/Orders.csv')
        df_order=df_order.values.tolist()
        order=[]
        for i in range(len(df_order)):
            order.insert(len(order),df_order[i][0].upper())
        
        self.pair=[]
        self.direction=[]
        self.direction2={}
        self.direction3={}
        self.direction4={}
        self.direction5={}
        self.direction2_pre={}
        self.direction3_pre={}
        self.direction4_pre={}
        self.direction5_pre={}
        self.mode=[]
        
        for i in order:
            a=i.split()
            # print(a)
            if a[0] in ['BUY','SELL']:
                for j in range(1,len(a)):
                    self.pair.append(a[j])
                    self.direction.append(a[0])
                    self.mode.append('')
            elif a[0] in ['PYRAMIDING'] and a[1] in ['BUY','SELL']:
                for j in range(2,len(a)):
                    self.pair.append(a[j])
                    self.direction.append(a[1])
                    self.mode.append(a[0])
                
            else:
                print(a[0],a[1])
                input('Wrong action!!!')
        
        # read config 
        config=configparser.ConfigParser()
        config.read('/Users/apple/Documents/code/Python/IBAPI/Settings/config.cfg')
        self.BetAmout=float(config.get('MM','BetAmout'))
        self.rr=float(config.get('MM','rr'))
        self.ifMultiTimeFrame=eval(config.get('MM','ifMultiTimeFrame'))
        self.timeframe1=int(config.get('MM','timeframe1'))
        self.timeframe2=int(config.get('MM','timeframe2'))
        self.timeframe3=int(config.get('MM','timeframe3'))
        self.timeframe4=int(config.get('MM','timeframe4'))
        self.timeframe5=int(config.get('MM','timeframe5'))
        
        # basic setup
        self.StrategyType='API'  # 告訴策略用API方式來處理訊號
        self.st=Strategies(self.StrategyType)
        self.rm=RiskManage(self.StrategyType,self.rr)
        self.NotInPair=[]
        self.nextOrderId=0
        self.isUSstock=False
        # self.isUSstock=True
        self.isEUstock=False
        self.data = {} #Historical
        self.data1 = {} #Update
        self.df1={}
        self.df2={} 
        self.df3={} 
        self.df4={} 
        self.df5={} 
        self.df_tick={} 
        self.df_res={}
        
        
        # preset dict
        self.res_dict = {
            'Open':'first',
            'High':'max',
            'Low':'min',
            'Close': 'last',
            'Volume': 'sum'
            }
        
        self.FX_cfd=['AUDCAD','AUDCHF','AUDCNH','AUDHKD','AUDJPY','AUDNZD','AUDUSD','AUDSGD','AUDZAR','CADCHF','CADJPY','CADCNH','CADHKD',
                     'CHFJPY','CHFCNH','CHFCZK','CHFDKK','CHFHUF','CHFNOK','CHFPLN','CHFSEK','CHFZAR','CNHHKD','CNHJPY','DKKJPY','DKKNOK','DKKSEK',
                     'EURAUD','EURCAD','EURCHF','EURCNH','EURCZK','EURDKK','EURGBP','EURJPY','EURNZD','EURUSD','EURHKD','EURHUF','EURZAR','EURPLN','EURILS',
                     'EURNOK','EURRUB','EURSEK','EURSGD','NZDCAD','NZDCHF','NZDJPY','NZDUSD','SEKJPY','SGDCNH','SGDJPY','HKDJPY','MXNJPY','NOKJPY','NOKSEK',
                     'GBPAUD','GBPCAD','GBPCHF','GBPCNH','GBPHKD','GBPCZK','GBPDKK','GBPHUF','GBPMXN','GBPNOK','GBPZAR','GBPPLN','GBPJPY','GBPNZD','GBPUSD','GBPSGD',
                     'USDCAD','USDCHF','USDJPY','USDRUB','USDSEK','USDHUF','USDCNH','USDCZK','USDDKK','USDHKD','USDMXN','USDNOK','USDPLN',
                     'USDSGD','USDILS','USDZAR','ZARJPY','GBPSEK'
                     ]
        
        self.Index_cfd=['IBUS500','IBUS30','IBUST100','IBGB100','IBEU50','IBDE30','IBFR40','IBES35','IBNL25','IBCH20','IBJP225','IBHK50','IBAU200']
        self.Index_currency={'IBUS500':'USD','IBUS30':'USD','IBUST100':'USD','IBGB100':'GBP','IBEU50':'EUR','IBDE30':'EUR','IBFR40':'EUR','IBES35':'EUR',
                             'IBNL25':'EUR','IBCH20':'CHF','IBJP225':'JPY','IBHK50':'HKD','IBAU200':'AUD'}
        
        self.Metal_cfd=['XAUUSD','XAGUSD']
        
        self.LSEStock_cfd=['WISE','FRES','BA.','VIC','FAN','AEX','JOG','SAR','IMB','KINO','TRLS','TEP','BRBY','SGLN','AVV','PHGP','PSON','NETW','ESNT']
        
        self.TSXStock_cfd=['DOL','HGU','RY','MFC','CNQ','SU','XEG','GLO','ARX','ATH','BTE','MEG','TOI','AYA','FRU','FR','ATD','L','VET','AQI','CSU','MTA','AOI']
        
        self.HK_Future=['MHI','MCH.HK','HHI.HK','1898','9633','2823']
        
        
        # ------------------
        
        self.USStock_cfd=['DVN','EWZ','SLV']
        
        self.AUStock_cfd=['AGY','WHC','BRN','MIN','IGO','PLS']
        
        self.Mutual_Fund=['VENAX','VGELX','VGENX']
        
        self.Future=['YC','YK','YW','M6B','MYM','MNQ','MGC','YI']
        
        
        
        
        # Time control
        self.now_date=np.nan
        self.pre_date=np.nan
        self.LastReceivedDataTime=int(datetime.now().timestamp())
        self.lastNoticeTime=np.nan
        self.EntryTime=int(datetime.now().timestamp())
        self.LastOrderTime={}
        self.isBusy=False
        
        # Order control
        self.signal1={} 
        self.signal2={} 
        self.signal3={} 
        self.signal4={} 
        self.signal5={} 
        self.entryprice={}
        self.tp={}
        self.sl={}
        self.SLOrderId={}
        self.info={}
        self.QuoteContract={}
        self.OrderContract={}
        self.qty={}
        self.reqId=0
        self.j=0
        self.trade={}
        self.open_trade={}
        self.ConversionRate={'USD':1.0}

        # maybe useless
        self.d=1
        self.position={}
        self.EntryPrice=np.nan
        # self.permId2ord=[]
        
        self.all_positions = pd.DataFrame([], columns = ['Symbol', 'Sec Type','Quantity', 'Average Cost','UnrealizedPNL','RealizedPNL']) 
        self.all_timeframes = pd.DataFrame([], columns = ['Symbol', str(self.timeframe2),str(self.timeframe3),str(self.timeframe4),str(self.timeframe5)]) 
        self.same_direction = pd.DataFrame([], columns = ['Symbol', str(self.timeframe2),str(self.timeframe3),str(self.timeframe4),str(self.timeframe5)]) 
        self.all_trades = pd.DataFrame([], columns = ['DateTime', 'Symbol','Side','Price','Shares','Average Price','Cumulative Quantity','Exit Price','Unrealized PNL','Realized PNL','Commision','TP','SL']) 
        self.open_trades = pd.DataFrame([], columns = ['Symbol','Pair NO.','DateTime']) 
        self.account = pd.DataFrame([], columns = ['DateTime', 'Account Name','Account Key','Account Value','Currency']) 

        # basic setup
        for pair in range(len(self.pair)):
            self.info[pair]={}
            self.data[pair] = [] #Historical
            self.data1[pair] = [] #Update
            self.df1[pair]=[] # Historical
            self.df2[pair]=[] # Historical
            self.df3[pair]=[] # Historical
            self.df4[pair]=[] # Historical
            self.df5[pair]=[] # Historical
            self.df_tick[pair]=[] #Update 
            self.df_res[pair]=[]
            self.position[pair]=0.0
            self.signal1[pair]=False
            self.signal2[pair]=False
            self.signal3[pair]=False
            self.signal4[pair]=False
            self.signal5[pair]=False
            self.direction2[pair]='None'
            self.direction3[pair]='None'
            self.direction4[pair]='None'
            self.direction5[pair]='None'
            self.direction2_pre[pair]='None'
            self.direction3_pre[pair]='None'
            self.direction4_pre[pair]='None'
            self.direction5_pre[pair]='None'
            self.entryprice[pair]=np.nan
            self.tp[pair]=np.nan
            self.sl[pair]=np.nan
            self.LastOrderTime[pair]=int(datetime.now().timestamp())-5*self.timeframe1*60
            self.trade[pair]={}
            self.open_trade[pair]=[]
            self.SLOrderId[pair]=np.nan
            # build contract
            self.PairToContract(pair)    
            self.all_positions.loc[self.pair[pair]]=self.pair[pair],self.OrderContract[pair].secType,0.0,0.0,0.0,0.0
        
        self.all_positions.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_positions.csv',index=0 )  
        # self.all_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv',index=1)
        # self.open_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/open_trades.csv',index=1)
        
        #save self.trade and self.open_trade csv
        tradeRecord=dictTransform(self.trade)
        toCSV(tradeRecord,self.open_trade)
        
        #read 
        self.all_trades,self.open_trades=fromCSV()
        # self.open_trade=fromCSV0()
        
        # if os.path.isfile('/Users/apple/Documents/code/Python/IBAPI/Output/trades.csv') and os.path.isfile('/Users/apple/Documents/code/Python/IBAPI/Output/openTrade.csv'):
        #     self.trade,self.open_trade=fromCSV()
        # else:
        #     pass
             
        return

    def error(self,reqId,errorCode,errorString):
        
        # if errorCode==2104 or errorCode==2106 or errorCode==2158 or errorCode==300:
        #     return
            
            
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
        self.df1[reqId] = pd.DataFrame(self.data[reqId],columns=['DateTime','Open','High','Low', 'Close','Volume'])
        self.df1[reqId]['DateTime'] = pd.to_datetime(self.df1[reqId]['DateTime'],unit='s')
        # self.df1[reqId].to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/df1_'+str(reqId)+'.csv',index=0 ,float_format='%.5f')   
        self.data[reqId]=[] #清掉是否有助於記憶體的節省？
        super().historicalDataEnd(reqId, start, end)
        # print( datetime.fromtimestamp(int(datetime.now().timestamp())),'HistoricalDataEnd. ReqId:', reqId, 'from', start, 'to', end)
        # if 'IB' in self.OrderContract[reqId].symbol[:2]:
        #     return
        # self.reqContractDetails(reqId, self.OrderContract[reqId])
        self.reqContractDetails(reqId, self.QuoteContract[reqId])
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Conversion Rate:',self.ConversionRate)
        
        
        # check the direction of higher time frame
        self.df1[reqId].DateTime = pd.to_datetime(self.df1[reqId].DateTime)
        self.df1[reqId].index = self.df1[reqId].DateTime
        self.df2[reqId] = self.df1[reqId].resample(str(self.timeframe2)+'min', closed='left',label='left').agg(self.res_dict)  
        # self.df2[reqId].reset_index(inplace=True)
        self.df3[reqId] = self.df1[reqId].resample(str(self.timeframe3)+'min', closed='left',label='left').agg(self.res_dict)  
        # self.df3[reqId].reset_index(inplace=True)
        self.df4[reqId] = self.df1[reqId].resample(str(self.timeframe4)+'min', closed='left',label='left').agg(self.res_dict)  
        self.df5[reqId] = self.df1[reqId].resample(str(self.timeframe5)+'min', closed='left',label='left').agg(self.res_dict)  
        # self.df4[reqId].reset_index(inplace=True)
        
        self.df1[reqId].dropna(axis=0, how='any', inplace=True)  
        self.df1[reqId].reset_index(drop=True)   
        self.df2[reqId].dropna(axis=0, how='any', inplace=True)  
        self.df2[reqId].reset_index(drop=True)   
        self.df3[reqId].dropna(axis=0, how='any', inplace=True)  
        self.df3[reqId].reset_index(drop=True)   
        self.df4[reqId].dropna(axis=0, how='any', inplace=True)  
        self.df4[reqId].reset_index(drop=True)   
        self.df5[reqId].dropna(axis=0, how='any', inplace=True)  
        self.df5[reqId].reset_index(drop=True)   
           
        
        self.direction2[reqId]=self.st._RSI_HTF(reqId,self.df2[reqId],self.timeframe2)
        self.direction3[reqId]=self.st._RSI_HTF(reqId,self.df3[reqId],self.timeframe3)
        self.direction4[reqId]=self.st._RSI_HTF(reqId,self.df4[reqId],self.timeframe4)
        self.direction5[reqId]=self.st._RSI_HTF(reqId,self.df5[reqId],self.timeframe5)
        self.direction2_pre[reqId]=self.direction2[reqId]
        self.direction3_pre[reqId]=self.direction3[reqId]
        self.direction4_pre[reqId]=self.direction4[reqId]
        self.direction5_pre[reqId]=self.direction5[reqId]
        
        # save all time frames direction
        self.all_timeframes.loc[self.pair[reqId]]=self.pair[reqId],self.direction2[reqId],self.direction3[reqId],self.direction4[reqId],self.direction5[reqId]
        self.all_timeframes.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_timeframe.csv',index=0)
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],self.timeframe2,self.direction2[reqId],self.timeframe3,self.direction3[reqId],self.timeframe4,self.direction4[reqId],self.timeframe5,self.direction5[reqId])

        # save the same direction of all time frames
        # condition=(self.all_timeframes[str(self.timeframe2)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe3)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe4)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe5)]==self.direction[reqId])
        # condition=(self.all_timeframes[str(self.timeframe2)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe3)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe4)]==self.direction[reqId])
        # self.same_direction = pd.concat([self.same_direction, self.all_timeframes[condition]], ignore_index=True) 
        # self.same_direction=self.same_direction.drop_duplicates(keep='last')
        # self.same_direction.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_same_direction.csv',index=0)
        
        self.same_direction.drop(self.same_direction.index,inplace=True)
        for pair in range(len(self.pair)):
            if self.direction[pair]==self.direction2[pair]==self.direction3[pair]==self.direction4[pair]:
                self.same_direction.loc[self.pair[pair]]=self.pair[pair],self.direction2[pair],self.direction3[pair],self.direction4[pair],self.direction5[pair]
        
        self.same_direction.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_same_direction.csv',index=0)
                
        
        
        return

    def historicalDataUpdate(self, reqId: int, bar):
        self.data1[reqId].append([bar.date,bar.open,bar.high,bar.low,bar.close,bar.volume])
        self.LastReceivedDataTime=int(datetime.now().timestamp())
        self.pre_date=self.now_date #Calculate the bar.date and previous bar.date
        self.now_date=int(bar.date)
        
        # for test df_tick ticks income,delete after test
        # self.df_tick[reqId] = pd.DataFrame(self.data1[reqId],columns=['DateTime','Open','High','Low', 'Close','Volume'])
        # self.df_tick[reqId]['DateTime'] = pd.to_datetime(self.df_tick[reqId]['DateTime'],unit='s') 
        # self.df_tick[reqId]=self.df_tick[reqId].set_index('DateTime')
        # self.df_tick[reqId].to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/df['+str(reqId)+'].csv',index=1 ,float_format='%.5f')  

        # read telegram token and chat id
        token,chatid=read_token()
        
        if self.now_date != self.pre_date : #Resample once after the bar closed
            self.df_tick[reqId] = pd.DataFrame(self.data1[reqId],columns=['DateTime','Open','High','Low', 'Close','Volume'])
            self.df_tick[reqId]['DateTime'] = pd.to_datetime(self.df_tick[reqId]['DateTime'],unit='s') 
            # self.df_tick[reqId]['DateTime'] = pd.to_datetime(self.df_tick[reqId]['DateTime'],unit='s',tzinfo=timezone('UTC')) 
            # self.df_tick[reqId]['DateTime'] =self.df_tick[reqId]['DateTime'].astimezone(timezone('Asia/Taipei'))
            # self.df_tick[reqId]['DateTime'] = pd.to_datetime(self.df_tick[reqId]['DateTime'],unit='s', utc=True).map(lambda x: x.tz_convert('Asia/Taipei')) 
            # self.df_tick[reqId]['DateTime'] = pd.to_datetime(self.df_tick[reqId]['DateTime'],unit='s', utc=True)\
            #           .map(lambda x: x.tz_convert('Asia/Taipei')) 
            self.df_tick[reqId]=self.df_tick[reqId].set_index('DateTime')
            # self.df_tick[reqId].to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/df['+str(reqId)+'].csv',index=1 ,float_format='%.5f')  


            self.df_res[reqId]=self.df_tick[reqId].resample(str(self.timeframe1)+'min', closed='left', label='left').agg(self.res_dict)
            # self.df_tick.drop(self.df_tick.index, axis=0,inplace=True) 
            self.df_tick[reqId]=[]
            del self.data1[reqId][0:len(self.data1[reqId])-1]
            self.df_res[reqId].drop(self.df_res[reqId].index[-1], axis=0, inplace=True) #delete the new open bar at lastest appended row
            # print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],str(self.timeframe1)+'K Bar:',self.df_res[reqId].index[-1].strftime('%F %H:%M') if len(self.df_res[reqId])!=0 else 'No Resample Bar')
            # self.df_res[reqId].to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/df_res'+str(reqId)+'.csv', mode='a', header=False,float_format='%.5f')
            # self.df_res[reqId].to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/df_res'+str(reqId)+'.csv',index=1 ,float_format='%.5f')
            self.df_res[reqId].reset_index(inplace=True) 

            self.df1[reqId]=pd.concat([self.df1[reqId], self.df_res[reqId]],ignore_index=True)
            
            # if self.pair[reqId] in self.LSEStock_cfd:
            # self.df1[reqId].to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/df1_'+str(reqId)+'.csv',index=0 ,float_format='%.5f') 
            
            # print('type of df_tick:',type(self.df_tick))
            
            
            # higher time frame Bar close
            if self.ifMultiTimeFrame==True and self.now_date != self.pre_date and self.now_date/(self.timeframe2*60)==self.now_date//(self.timeframe2*60):
                # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'self.timeframe2',self.timeframe2)
                # print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.now_date,bar.date,self.now_date/self.timeframe2,self.now_date//self.timeframe2)
                # self.df2[reqId]=self.df1[reqId].set_index('DateTime')
                self.df2[reqId]=self.df1[reqId].set_index('DateTime').resample(str(self.timeframe2)+'min', closed='left', label='left').agg(self.res_dict)
                # self.df1[reqId].reset_index(inplace=True) 
                self.df2[reqId].dropna(axis=0, how='any', inplace=True)  # 去掉交易時間外的空行
                self.df2[reqId].reset_index(drop=True)
                
                
                self.direction2[reqId]=self.st._RSI_HTF(reqId,self.df2[reqId],self.timeframe2)
                if self.direction2_pre[reqId]!=self.direction2[reqId] and self.direction2[reqId] in ['BUY','SELL']:
                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],str(self.timeframe2),'['+self.direction2[reqId]+']',self.timeframe3,self.direction3[reqId],self.timeframe4,self.direction4[reqId],self.timeframe5,self.direction5[reqId])
                    self.direction2_pre[reqId]=self.direction2[reqId]
                    
                    # save all time frames and same direction
                    self.all_timeframes.loc[self.pair[reqId]]=self.pair[reqId],self.direction2[reqId],self.direction3[reqId],self.direction4[reqId],self.direction5[reqId]
                    self.all_timeframes.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_timeframe.csv',index=0)
                    # condition=(self.all_timeframes[str(self.timeframe2)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe3)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe4)]==self.direction[reqId])
                    # self.same_direction = pd.concat([self.same_direction, self.all_timeframes[condition]], ignore_index=True) 
                    # self.same_direction=self.same_direction.drop_duplicates(keep='last')
                    # self.same_direction.drop(index=self.same_direction[condition==False],axis=0,inplace=True)
                    # self.same_direction.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_same_direction.csv',index=0)
                    
                    # save all time frames and same direction
                    self.same_direction.drop(self.same_direction.index,inplace=True)
                    for pair in range(len(self.pair)):
                        if self.direction[pair]==self.direction2[pair]==self.direction3[pair]==self.direction4[pair]:
                            self.same_direction.loc[self.pair[pair]]=self.pair[pair],self.direction2[pair],self.direction3[pair],self.direction4[pair],self.direction5[pair]
                    
                    self.same_direction.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_same_direction.csv',index=0)
                
                    
                    
                    # if self.direction[reqId]==self.direction2[reqId] and self.direction2[reqId]==self.direction3[reqId] and self.direction3[reqId]==self.direction4[reqId] and self.direction4[reqId]==self.direction5[reqId]:
                    if self.direction[reqId]==self.direction2[reqId] and self.direction2[reqId]==self.direction3[reqId] and self.direction3[reqId]==self.direction4[reqId]:
                        print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],'all direction:',self.direction[reqId])
                        send(self.pair[reqId]+' all direction: '+self.direction[reqId],token,chatid)
                        
                
                # print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],str(self.timeframe2)+'K Bar:',self.df2[reqId].index[-1].strftime('%F %H:%M'))
                # self.df2[reqId].reset_index(inplace=True) 
                # self.df2[reqId].to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/df2_'+str(reqId)+'.csv',index=0 ,float_format='%.5f') 
                
                
                if self.ifMultiTimeFrame==True and self.now_date != self.pre_date and self.now_date/(self.timeframe3*60)==self.now_date//(self.timeframe3*60):
                    # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'self.timeframe3',self.timeframe3)
                    # print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.now_date,bar.date,self.now_date/self.timeframe3,self.now_date//self.timeframe3)
                    self.df3[reqId]=self.df1[reqId].set_index('DateTime').resample(str(self.timeframe3)+'min', closed='left', label='left').agg(self.res_dict)
                    
                    self.df3[reqId].dropna(axis=0, how='any', inplace=True)  # 去掉交易時間外的空行
                    self.df3[reqId].reset_index(drop=True)
                    
                    self.direction3[reqId]=self.st._RSI_HTF(reqId,self.df3[reqId],self.timeframe3)
                    if self.direction3_pre[reqId]!=self.direction3[reqId] and self.direction3[reqId] in ['BUY','SELL']:
                        print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],self.timeframe2,self.direction2[reqId],str(self.timeframe3),'['+self.direction3[reqId]+']',self.timeframe4,self.direction4[reqId],self.timeframe5,self.direction5[reqId])
                        self.direction3_pre[reqId]=self.direction3[reqId]
                        
                        # save all time frames and same direction
                        self.all_timeframes.loc[self.pair[reqId]]=self.pair[reqId],self.direction2[reqId],self.direction3[reqId],self.direction4[reqId],self.direction5[reqId]
                        self.all_timeframes.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_timeframe.csv',index=0)
                        # condition=(self.all_timeframes[str(self.timeframe2)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe3)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe4)]==self.direction[reqId])
                        # self.same_direction = pd.concat([self.same_direction, self.all_timeframes[condition]], ignore_index=True) 
                        # self.same_direction=self.same_direction.drop_duplicates(keep='last')
                        # self.same_direction.drop(index=self.same_direction[condition==False],axis=0,inplace=True)
                        # self.same_direction.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_same_direction.csv',index=0)
                        
                         # save all time frames and same direction
                        self.same_direction.drop(self.same_direction.index,inplace=True)
                        for pair in range(len(self.pair)):
                            if self.direction[pair]==self.direction2[pair]==self.direction3[pair]==self.direction4[pair]:
                                self.same_direction.loc[self.pair[pair]]=self.pair[pair],self.direction2[pair],self.direction3[pair],self.direction4[pair],self.direction5[pair]
                        
                        self.same_direction.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_same_direction.csv',index=0)
                
                        
                        # if self.direction[reqId]==self.direction2[reqId] and self.direction2[reqId]==self.direction3[reqId] and self.direction3[reqId]==self.direction4[reqId] and self.direction4[reqId]==self.direction5[reqId]:
                        if self.direction[reqId]==self.direction2[reqId] and self.direction2[reqId]==self.direction3[reqId] and self.direction3[reqId]==self.direction4[reqId]:
                            print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],'all direction:',self.direction[reqId])
                            send(self.pair[reqId]+' all direction: '+self.direction[reqId],token,chatid)
                            
                    # print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],str(self.timeframe3)+'K Bar:',self.df3[reqId].index[-1].strftime('%F %H:%M'))
                    # self.df3[reqId].reset_index(inplace=True) 
                    # self.df3[reqId].to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/df3_'+str(reqId)+'.csv',index=0 ,float_format='%.5f') 
                    
                    
                    if self.ifMultiTimeFrame==True and self.now_date != self.pre_date and self.now_date/(self.timeframe4*60)==self.now_date//(self.timeframe4*60):
                        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'self.timeframe4',self.timeframe4)
                        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.now_date,bar.date,self.now_date/self.timeframe4,self.now_date//self.timeframe3)
                        self.df4[reqId]=self.df1[reqId].set_index('DateTime').resample(str(self.timeframe4)+'min', closed='left', label='left').agg(self.res_dict)
                        
                        self.df4[reqId].dropna(axis=0, how='any', inplace=True)
                        self.df4[reqId].reset_index(drop=True)
                        
                        self.direction4[reqId]=self.st._RSI_HTF(reqId,self.df4[reqId],self.timeframe4)
                        if self.direction4_pre[reqId]!=self.direction4[reqId] and self.direction4[reqId] in ['BUY','SELL']:
                            
                            print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],self.timeframe2,self.direction2[reqId],self.timeframe3,self.direction3[reqId],str(self.timeframe4),'['+self.direction4[reqId]+']',self.timeframe5,self.direction5[reqId])
                            self.direction4_pre[reqId]=self.direction4[reqId]
                            
                            # save all time frames and same direction
                            self.all_timeframes.loc[self.pair[reqId]]=self.pair[reqId],self.direction2[reqId],self.direction3[reqId],self.direction4[reqId],self.direction5[reqId]
                            self.all_timeframes.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_timeframe.csv',index=0)
                            # condition=(self.all_timeframes[str(self.timeframe2)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe3)]==self.direction[reqId])&(self.all_timeframes[str(self.timeframe4)]==self.direction[reqId])
                            # self.same_direction = pd.concat([self.same_direction, self.all_timeframes[condition]], ignore_index=True) 
                            # self.same_direction=self.same_direction.drop_duplicates(keep='last')
                            # self.same_direction.drop(index=self.same_direction[condition==False],axis=0,inplace=True)
                            # self.same_direction.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_same_direction.csv',index=0)
                            
                             # save all time frames and same direction
                            self.same_direction.drop(self.same_direction.index,inplace=True)
                            for pair in range(len(self.pair)):
                                if self.direction[pair]==self.direction2[pair]==self.direction3[pair]==self.direction4[pair]:
                                    self.same_direction.loc[self.pair[pair]]=self.pair[pair],self.direction2[pair],self.direction3[pair],self.direction4[pair],self.direction5[pair]
                            
                            self.same_direction.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_same_direction.csv',index=0)
                
                            # if self.direction[reqId]==self.direction2[reqId] and self.direction2[reqId]==self.direction3[reqId] and self.direction3[reqId]==self.direction4[reqId] and self.direction4[reqId]==self.direction5[reqId]:
                            if self.direction[reqId]==self.direction2[reqId] and self.direction2[reqId]==self.direction3[reqId] and self.direction3[reqId]==self.direction4[reqId]:
                                print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],'all direction:',self.direction[reqId])
                                send(self.pair[reqId]+' all direction: '+self.direction[reqId],token,chatid)
                                
                        
                        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],str(self.timeframe4)+'K Bar:',self.df4[reqId].index[-1].strftime('%F %H:%M'))
                        # self.df4[reqId].reset_index(inplace=True) 
                        # self.df4[reqId].to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/df4_'+str(reqId)+'.csv',index=0 ,float_format='%.5f') 
                       
                            
                        if self.ifMultiTimeFrame==True and self.now_date != self.pre_date and self.now_date/(self.timeframe5*60)==self.now_date//(self.timeframe5*60):
                            self.df5[reqId]=self.df1[reqId].set_index('DateTime').resample(str(self.timeframe5)+'min', closed='left', label='left').agg(self.res_dict)
                        
                            self.df5[reqId].dropna(axis=0, how='any', inplace=True)  # 去掉交易時間外的空行
                            self.df5[reqId].reset_index(drop=True)
                        
                            self.direction5[reqId]=self.st._RSI_HTF(reqId,self.df5[reqId],self.timeframe5)
                            if self.direction5_pre[reqId]!=self.direction5[reqId] and self.direction5[reqId] in ['BUY','SELL']:
                                
                                print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],self.timeframe2,self.direction2[reqId],self.timeframe3,self.direction3[reqId],self.timeframe4,self.direction4[reqId],str(self.timeframe5),'['+self.direction5[reqId]+']')
                                self.direction5_pre[reqId]=self.direction5[reqId]
                                
                                # save all time frames and same direction
                                self.all_timeframes.loc[self.pair[reqId]]=self.pair[reqId],self.direction2[reqId],self.direction3[reqId],self.direction4[reqId],self.direction5[reqId]
                                self.all_timeframes.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_timeframe.csv',index=0)
                                
                                if self.direction[reqId]==self.direction2[reqId] and self.direction2[reqId]==self.direction3[reqId] and self.direction3[reqId]==self.direction4[reqId] and self.direction4[reqId]==self.direction5[reqId]:
                                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),self.pair[reqId],'all direction:',self.direction[reqId])
                                    send(self.pair[reqId]+' all direction: '+self.direction[reqId],token,chatid)
                                    
            
            # update the unrealized P&L
            self.reqAccountUpdates(True,"")
            
            
            #check the signal
            if (self.all_positions.loc[self.pair[reqId],'Quantity']==0.0 or (self.all_positions.loc[self.pair[reqId],'Quantity']!=0.0 and self.mode[reqId]=='PYRAMIDING')) and bar.close>self.all_positions.loc[self.pair[reqId],'Average Cost'] and int(datetime.now().timestamp())-self.LastOrderTime[reqId]>5*self.timeframe1*60:
                
                # self.signal1[reqId]=self.st._RSI(self.df1[reqId],reqId)
                self.signal1[reqId]=self.st._RSI_SMA(self.df1[reqId],reqId)
                if self.isBusy:
                    time.sleep(2)
                
                # print(self.signal1[reqId])
                # print(self.direction[reqId])
                # print(self.direction2[reqId])
                
                if self.ifMultiTimeFrame==True: 
                    d2='SELL' if self.direction2[reqId]=='BUY' else 'BUY' if self.direction2[reqId]=='SELL' else 'None'
                    d3='SELL' if self.direction3[reqId]=='BUY' else 'BUY' if self.direction3[reqId]=='SELL' else 'None'
                    d4='SELL' if self.direction4[reqId]=='BUY' else 'BUY' if self.direction4[reqId]=='SELL' else 'None'
                    ifEntry=self.signal1[reqId] ==self.direction[reqId] and self.signal1[reqId] != d2 and self.signal1[reqId] != d3 and self.signal1[reqId] != d4
                elif self.ifMultiTimeFrame==False:
                    ifEntry=self.signal1[reqId] in ['BUY','SELL']
                else:
                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Wrong setting ifMultiTimeFrame')

                
                # if self.signal1[reqId] == self.direction2[reqId] and self.signal1[reqId] ==self.direction[reqId]: # if entry signal produced and check no position then entry
                # if self.signal1[reqId] ==self.direction[reqId] and self.signal1[reqId] == self.direction2[reqId] and self.signal1[reqId] == self.direction3[reqId] and self.signal1[reqId] == self.direction4[reqId] : # if entry signal produced and check no position then entry
                if ifEntry: # if entry signal produced and check no position then entry
                    if self.all_positions.loc[self.pair[reqId],'Quantity']==0.0 and self.mode[reqId]=='':
                        
                        self.entryprice[reqId]=round(bar.close,self.info[reqId].get('round'))
                        self.tp[reqId]=self.rm.TP(self.df1[reqId],self.info[reqId],self.signal1[reqId],self.rr,len(self.df1[reqId])-1)
                        self.sl[reqId]=self.rm.SL(self.df1[reqId],self.info[reqId],self.signal1[reqId],len(self.df1[reqId])-1)
                        # print(self.OrderContract[reqId],self.ConversionRate)
                        
                        # self.qty[reqId]=max(1,round(self.BetAmout/(abs(self.entryprice[reqId]-self.sl[reqId])/self.ConversionRate[reqId]),0))
                        self.qty[reqId]=max(1,round(self.BetAmout/(abs(self.entryprice[reqId]-self.sl[reqId])/self.ConversionRate[self.OrderContract[reqId].currency]),0))
                        
                        self.reqId=reqId
                        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'historicalDataUpdate reqId:',self.reqId,'Symbol:',self.pair[self.reqId],'current positions:',self.all_positions.loc[self.pair[self.reqId],'Quantity'],self.signal1[reqId],'Quantity:',self.qty[reqId],'Entry:',self.entryprice[reqId],'TP:',self.tp[reqId],'SL:',self.sl[reqId])
                        self.isBusy=True
                        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Busy:',self.isBusy)
                        self.start()    
                        
                    elif self.mode[reqId]=='PYRAMIDING':
                        self.entryprice[reqId]=round(bar.close,self.info[reqId].get('round'))
                        # print('entryprice:',self.entryprice[reqId])
                        self.sl[reqId]=self.rm.Risk4(self.df1[reqId],self.info[reqId],self.signal1[reqId],self.trade[reqId],self.open_trade[reqId])
                        # if len(self.open_trade[reqId])==0:
                        if self.all_positions.loc[self.pair[reqId],'Quantity']==0.0:
                            self.qty[reqId]=max(1,round(self.BetAmout/(abs(self.entryprice[reqId]-self.sl[reqId])/self.ConversionRate[self.OrderContract[reqId].currency]),0))
                            self.reqId=reqId
                            self.isBusy=True
                            print(datetime.fromtimestamp(int(datetime.now().timestamp())),'historicalDataUpdate reqId:',self.reqId,'Symbol:',self.pair[reqId],'current positions:',self.all_positions.loc[self.pair[reqId],'Quantity'],self.signal1[reqId],'Quantity:',self.qty[reqId],'Entry:',self.entryprice[reqId],'SL:',self.sl[reqId])
                            self.start1() 
                        elif self.all_positions.loc[self.pair[reqId],'Quantity']==0.0:
                            for j in self.open_trade[reqId]:
                                if self.sl[reqId]!=self.trade[reqId][j].get('SL') and not np.isnan(self.sl[reqId]):
                                    self.qty[reqId]=self.trade[reqId][j].get('Cumulative Quantity')*0.6
                                    self.reqId=reqId
                                    self.isBusy=True
                                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),'historicalDataUpdate reqId:',self.reqId,'Symbol:',self.pair[reqId],'current positions:',self.all_positions.loc[self.pair[reqId],'Quantity'],self.signal1[reqId],'Quantity:',self.qty[reqId],'Entry:',self.entryprice[reqId],'SL:',self.sl[reqId])
                                    # if len(self.SLOrderId[reqId])!=0:
                                    #     for j in self.SLOrderId[reqId]:
                                    #         self.cancelOrder(self.SLOrderId[reqId][j])
                                    #         print('cancel order:',self.SLOrderId[reqId][j])
                                    #     time.sleep(3)
                                    	
                                    self.start2() 
                                          
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
            df.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/ConversionRate.csv',index=0 )  
            self.cancelRealTimeBars(reqId)
        return
    
    
    def start(self):
        bracket = self.BracketOrder(self,self.nextOrderId, self.signal1[self.reqId], self.qty[self.reqId], self.entryprice[self.reqId], self.tp[self.reqId], self.sl[self.reqId]) # Order
        for o in bracket:
            self.placeOrder(o.orderId, self.OrderContract[self.reqId], o)
            self.nextOrderId # need to advance this we’ll skip one extra oid, it’s fine
            # time.sleep(5)
        
        self.reqIds(-1)

        return
    
    def start1(self):
        bracket = self.BracketOrder1(self,self.nextOrderId, self.signal1[self.reqId], self.qty[self.reqId], self.entryprice[self.reqId], self.sl[self.reqId]) # Order
        for o in bracket:
            self.placeOrder(o.orderId, self.OrderContract[self.reqId], o)
            self.nextOrderId # need to advance this we’ll skip one extra oid, it’s fine
            # time.sleep(5)
            
        self.reqIds(-1)

        return
    
    def start2(self):
             
        # bracket = self.BracketOrder2(self,self.nextOrderId, self.signal1[self.reqId], self.qty[self.reqId], self.sl[self.reqId]) # Order
        bracket = self.BracketOrder2(self,self.nextOrderId, self.signal1[self.reqId], self.qty[self.reqId], self.entryprice[self.reqId], self.sl[self.reqId]) # Order

        for o in bracket:
            self.placeOrder(o.orderId, self.OrderContract[self.reqId], o)
            self.nextOrderId # need to advance this we’ll skip one extra oid, it’s fine
            # time.sleep(5)
            
        self.reqIds(-1)

        return
    
    def PairToContract(self,pair):
        if self.pair[pair] in self.FX_cfd:
            self.QuoteContract[pair]=self.cash(self.pair[pair])
            self.OrderContract[pair]=self.cashCFD(self.pair[pair])
        
        elif self.pair[pair] in self.Index_cfd:
            self.QuoteContract[pair]=self.indexCFD(self.pair[pair])
            self.OrderContract[pair]=self.indexCFD(self.pair[pair])
        
        elif self.pair[pair] in self.Metal_cfd:
            self.QuoteContract[pair]=self.metalCFD(self.pair[pair])
            self.OrderContract[pair]=self.metalCFD(self.pair[pair])
        
        elif self.pair[pair] in self.USStock_cfd:
            self.QuoteContract[pair]=self.USStockAtSmart(self.pair[pair])
            self.OrderContract[pair]=self.USStockCFD(self.pair[pair])
        
        elif self.pair[pair] in self.AUStock_cfd:
            self.QuoteContract[pair]=self.AustraliaStock(self.pair[pair])
            self.OrderContract[pair]=self.AustraliaStockCFD(self.pair[pair])
        
        elif self.pair[pair] in self.LSEStock_cfd:
            self.QuoteContract[pair]=self.LSEStock(self.pair[pair])
            self.OrderContract[pair]=self.LSEStockCFD(self.pair[pair])
        
        elif self.pair[pair] in self.TSXStock_cfd:
            self.QuoteContract[pair]=self.TSXStock(self.pair[pair])
            self.OrderContract[pair]=self.TSXStock(self.pair[pair])
            
        elif self.pair[pair] in self.HK_Future:
            self.QuoteContract[pair]=self.HKFuture(self.pair[pair])
            self.OrderContract[pair]=self.HKFuture(self.pair[pair])
        # ----------------------------------------------------------
        elif self.pair[pair] in self.Mutual_Fund:
            self.QuoteContract[pair]=self.MutualFund(self.pair[pair])
            self.OrderContract[pair]=self.MutualFund(self.pair[pair])
        
        elif self.pair[pair] in self.Future:
            self.QuoteContract[pair]=self.SimpleFuture(self.pair[pair])
            self.OrderContract[pair]=self.SimpleFuture(self.pair[pair])
        
        else:
            print(self.pair[pair])
            input('Wrong Symbol!!!')
        
        return
            
    def ContractToPair(self,contract):
        if 'IB' in contract.symbol[:2] and contract.symbol in self.pair:
            sym=contract.symbol
        elif contract.symbol+contract.currency in self.pair:
            sym=contract.symbol+contract.currency
        elif contract.symbol in self.pair:
            sym=contract.symbol
        else:
            sym='Not In Pair:'+contract.symbol+contract.currency
            pair=-1
            # if not contract in self.NotInPair:
            #     self.NotInPair.append(contract)

            return sym,pair
            
        pair=self.pair.index(sym)
        
        
        return sym,pair

    
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
    
    def EuropeanStock():
        contract = Contract()
        contract.symbol = "BMW"
        contract.secType = "STK"
        contract.currency = "EUR"
        contract.exchange = "SMART"
        contract.primaryExchange = "IBIS"
        return contract

    
    def EuropeanStock2():
        contract = Contract()
        contract.symbol = "NOKIA"
        contract.secType = "STK"
        contract.currency = "EUR"
        contract.exchange = "SMART"
        contract.primaryExchange = "HEX"
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
    
    def AustraliaStock(self,symbol):
        # ! [australiastockcfd_contract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.currency = "AUD"
        contract.exchange = "SMART"
        # ! [europeanstockcfd_contract]
        return contract
    
    def AustraliaStockCFD(self,symbol):
        # ! [australiastockcfd_contract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "CFD"
        contract.currency = "AUD"
        contract.exchange = "SMART"
        # ! [europeanstockcfd_contract]
        return contract
    
    def LSEStock(self,symbol):
        # ! [australiastockcfd_contract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.currency = "GBP"
        contract.exchange = "SMART"
        # ! [europeanstockcfd_contract]
        return contract
    
    def LSEStockCFD(self,symbol):
        # ! [australiastockcfd_contract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "CFD"
        contract.currency = "GBP"
        contract.exchange = "SMART"
        # ! [europeanstockcfd_contract]
        return contract
    
    def TSXStock(self,symbol):
        # ! [australiastockcfd_contract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.currency = "CAD"
        contract.exchange = "SMART"
        # ! [europeanstockcfd_contract]
        return contract
    
    def TSXStockCFD(self,symbol):
        # ! [australiastockcfd_contract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "CFD"
        contract.currency = "CAD"
        contract.exchange = "SMART"
        # ! [europeanstockcfd_contract]
        return contract
    
    def MutualFund(self,symbol):
        #! [fundcontract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "FUND"
        contract.exchange = "FUNDSERV"
        # contract.exchange = "SMART"
        contract.currency = "USD"
        #! [fundcontract]
        return contract
    
    def SimpleFuture(self,symbol):
        #! [futcontract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "FUT"
        contract.exchange = "GLOBEX"
        # contract.exchange = "ECBOT"
        contract.currency = "USD"
        contract.lastTradeDateOrContractMonth = "202212"
        #! [futcontract]
        return contract
    
    def HKFuture(self,symbol):
        #! [futcontract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "FUT"
        contract.exchange = "HKFE"
        # contract.exchange = "ECBOT"
        contract.currency = "HKD"
        contract.lastTradeDateOrContractMonth = "202210"
        #! [futcontract]
        return contract
    
    def ContFut():
        #! [continuousfuturescontract]
        contract = Contract()
        contract.symbol = "ES"
        contract.secType = "CONTFUT"
        contract.exchange = "GLOBEX"
        #! [continuousfuturescontract]
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
    
    @staticmethod
    def BracketOrder1(self,
        parentOrderId, #OrderId
        action,  #'BUY' or 'SELL'
        quantity,  #quantity of order
        limitPrice,  # Entry Price
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

        stopLoss = Order()
        stopLoss.orderId = parent.orderId + 1
        stopLoss.action = 'SELL' if action == 'BUY' else 'BUY'
        stopLoss.orderType = 'STP'
        #Stop trigger price
        stopLoss.auxPrice = stopLossPrice
        stopLoss.totalQuantity = quantity
        stopLoss.parentId = parentOrderId
        #In this case, the low side order will be the last child being sent. Therefore, it needs to set this attribute to True 
        #to activate all its predecessors
        stopLoss.transmit = True
        bracketOrder = [parent, stopLoss]
        
        
        return bracketOrder

    @staticmethod
    def BracketOrder2(self,
        parentOrderId, #OrderId
        action,  #'BUY' or 'SELL'
        quantity,  #quantity of order
        limitPrice,  # Entry Price
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
        
        stopLoss = Order()
        stopLoss.orderId = self.SLOrderId[self.reqId]
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'SL orderId:',self.SLOrderId[self.reqId])

        stopLoss.action = 'SELL' if action == 'BUY' else 'BUY'
        stopLoss.orderType = 'STP'
        #Stop trigger price
        stopLoss.auxPrice = stopLossPrice
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Origin Cumulative Qty:','scale-in Qty:',quantity,'all_positions Qty:',self.all_positions.loc[self.pair[self.reqId],'Quantity'])

        for j in self.open_trade[self.reqId]:
            print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Origin Cumulative Qty:',self.trade[self.reqId][j].get('Cumulative Quantity'))
            stopLoss.totalQuantity = quantity+self.trade[self.reqId][j].get('Cumulative Quantity')
            
        stopLoss.parentId = parentOrderId
        #In this case, the low side order will be the last child being sent. Therefore, it needs to set this attribute to True 
        #to activate all its predecessors
        stopLoss.transmit = True
        bracketOrder = [parent, stopLoss]
        
        return bracketOrder
    
    
    def execDetails(self, reqId: int, contract: Contract, execution):
        super().execDetails(reqId, contract, execution)
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'execDetails:','reqId',reqId,'self.reqId',self.reqId,'Symbol:',contract.symbol,'Currency:',contract.currency,'SecType:',contract.secType,'Price:', execution.avgPrice,'CumQty:',execution.cumQty)       

        self.isBusy=False
        
        
        sym,pair=self.ContractToPair(contract)
        if sym[:12]=='Not In Pair:':
            pass
            # print(sym)
            return
        
        self.reqId=pair
        
        
        token,chatid=read_token()
        
        self.LastOrderTime[self.reqId]=int(datetime.now().timestamp()) 
        
        if (execution.side=='BOT' and self.direction[self.reqId]=='BUY') or (execution.side=='SLD' and self.direction[self.reqId]=='SELL'): 
            if self.all_positions.loc[self.pair[self.reqId],'Quantity']!=0:
                while len(self.open_trade[self.reqId])==0:
                    print(datetime.fromtimestamp(int(datetime.now().timestamp())),'self.open_trade[self.reqId] empty')
                    time.sleep(1)
                    
                for j in self.open_trade[self.reqId]:
                    self.j=j #For linking to commissionReport
                self.trade[self.reqId][self.j].update({'Price':execution.price})
                self.trade[self.reqId][self.j].update({'Shares':execution.shares})
                
                self.trade[self.reqId][self.j].update({'SL':self.sl[self.reqId]})
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),"ExecDetails. ReqId:", reqId, "Symbol:", sym, "SecType:", contract.secType,'Scale-in', 'Side:',execution.side,'Shares:',execution.shares,'Price:',execution.price)
                send('Scale-in '+execution.side+' '+str(execution.shares)+' '+sym+'@'+str(execution.price),token,chatid)
                
                tradeRecord=dictTransform(self.trade)
                # print(tradeRecord,self.open_trade)
                toCSV(tradeRecord,self.open_trade)
                
                # update self.all_trades
                condition=(self.all_trades['Symbol']==sym)&(self.all_traders['Exit Price']==0)
                self.all_trades.loc[self.all_trades[condition].index[-1],'Price']=execution.price
                self.all_trades.loc[self.all_trades[condition].index[-1],'Shares']=execution.shares
                self.all_trades.loc[self.all_trades[condition].index[-1],'Average Price']=execution.avgPrice
                self.all_trades.loc[self.all_trades[condition].index[-1],'Cumulative Quantity']=execution.cumQty
                self.all_trades.loc[self.all_trades[condition].index[-1],'SL']=self.sl[self.reqId]
                self.all_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv',index=1)
                
            else:
            
                self.j=len(self.df1[self.reqId])-1
                # print(self.j)
                # print(self.trade[self.reqId])
                self.trade[self.reqId][self.j]={'ID':self.j,
                                'DateTime':self.df1[self.reqId].loc[self.df1[self.reqId].index[-1],'DateTime'],
                                'Symbol':self.pair[self.reqId],
                                'Side':'BUY' if execution.side=='BOT' else 'SELL',
                                'Price':execution.price,
                                'Shares':execution.shares,
                                'Average Price':execution.avgPrice,
                                'Cumulative Quantity':execution.cumQty,
                                'Exit Price':0.0,
                                'Unrealized PNL':0.0,
                                'Realized PNL':0.0,
                                'Commision':0.0,
                                'TP':self.tp[self.reqId],
                                'SL':self.sl[self.reqId]
                                }
                
                
                # print(self.trade[pair])
                
                self.open_trade[self.reqId].append(self.j)
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),"ExecDetails. ReqId:", reqId, "Symbol:", sym, "SecType:", contract.secType,'Entry', 'Side:',execution.side,'Shares:',execution.shares,'Price:',execution.price)
                send('Entry '+execution.side+' '+str(execution.shares)+' '+sym+'@'+str(execution.price),token,chatid)
                # toCSV(self.trade[self.reqId],self.open_trade[self.reqId])
                tradeRecord=dictTransform(self.trade)
                # print(tradeRecord,self.open_trade)
                toCSV(tradeRecord,self.open_trade)
                
                # add self.all_trades
                # self.all_trades.loc[self.df1[self.reqId].loc[self.df1[self.reqId].index[-1],'DateTime']]=self.df1[self.reqId].loc[self.df1[self.reqId].index[-1],'DateTime'],self.pair[self.reqId],'BUY' if execution.side=='BOT' else 'SELL',execution.price,execution.shares,execution.avgPrice,execution.cumQty,0.0,0.0,0.0,0.0,self.tp[self.reqId],self.sl[self.reqId]
                try:
                    while not self.all_trades.loc[datetime.now().strftime("%F %H:%M:%S")].empty:
                        time.sleep(1)
                except:
                    pass
                self.all_trades.loc[datetime.now().strftime("%F %H:%M:%S")]=datetime.now().strftime("%F %H:%M:%S"),self.pair[self.reqId],'BUY' if execution.side=='BOT' else 'SELL',execution.price,execution.shares,execution.avgPrice,execution.cumQty,0.0,0.0,0.0,0.0,self.tp[self.reqId],self.sl[self.reqId]
                self.all_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv',index=1)

                
                 # add self.open_trades
                condition=(self.all_trades['Symbol']==sym)&(self.all_trades['Exit Price']==0)
                self.open_trades.loc[sym]=sym,pair,self.all_trades.loc[self.all_trades[condition].index[-1],'DateTime']
                self.open_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/open_trades.csv',index=1)

                 
        else:
            try:
                for j in self.open_trade[self.reqId]:
                    self.j=j
                    # self.trade[self.reqId][self.j].update({'PnL':'commisionReport'})
                    self.trade[self.reqId][self.j].update({'Cumulative Quantity':0})
                    self.trade[self.reqId][self.j].update({'Exit Price':execution.price})
                    
                    # print(self.trade[se
                    # lf.reqId][self.j])
                    self.open_trade[self.reqId].remove(self.j)
                    # print('open_trade[pair]:',self.open_trade[self.reqId])
                
                self.SLOrderId[self.reqId]=np.nan
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),"ExecDetails. ReqId:", reqId, "Symbol:", sym, "SecType:", contract.secType,'Exit', 'Side:',execution.side,'Shares:',execution.shares,'Price:',execution.price)
                send('Exit '+execution.side+' '+str(execution.shares)+' '+sym+'@'+str(execution.price),token,chatid)
                # toCSV(tradeRecord,openTrade)
                tradeRecord=dictTransform(self.trade)
                # print(tradeRecord,self.open_trade)
                
                toCSV(tradeRecord,self.open_trade)
                
                # update self.all_trades
                try:
                    condition=(self.all_trades['Symbol']==sym)&(self.all_trades['Exit Price']==0)
                    self.all_trades.loc[self.all_trades[condition].index[-1],'Exit Price']=execution.price
                    self.all_trades.loc[self.all_trades[condition].index[-1],'Average Price']=execution.avgPrice
                    self.all_trades.loc[self.all_trades[condition].index[-1],'Cumulative Quantity']=execution.cumQty
                    self.all_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv',index=1)
                except:
                    pass 
                
                # update self.open_trades
                self.open_trades.drop([sym],axis = 0,inplace = True) 
                self.open_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/open_trades.csv',index=1)

            except KeyError:
                return
        return
    
    def execDetailsEnd(self, reqId: int):
        super().execDetailsEnd(reqId)
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),"ExecDetailsEnd. ReqId:", reqId)
        # self.reqAccountUpdates(False,"")
        self.reqAccountUpdates(True,"") 
        # self.reqPositions()
        self.reqOpenOrders()	
        return    
    
    
    def nextValidId(self,orderId):
        super().nextValidId(orderId)
        # logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextOrderId=orderId
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),"NextValidId:", orderId)
        return
    
    def updateAccountValue(self, key: str, val: str, currency: str,accountName: str):
        super().updateAccountValue(key, val, currency, accountName)
        # print("UpdateAccountValue. Key:", key, "Value:", val,"Currency:", currency, "AccountName:", accountName)
        self.account.loc[datetime.now().strftime("%F %H:%M:%S")]=datetime.now().strftime("%F %H:%M:%S"),accountName,key,val,currency
        self.account.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/account.csv',index=1)
        return
    
    def updatePortfolio(self,contract:Contract,position:float,marketPrice:float,marketValue:float,averageCost:float,unrealizedPNL:float,realizedPNL:float,accountName:str):
            
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'UpdatePortfolio.','Symbol:',contract.symbol,'SecType:',contract.secType,'Exchange:',contract.exchange,'Position:',position,'MarketPrice:',marketPrice,'MarketValue:',marketValue,'AverageCost:',averageCost,'UnrealizedPNL:',unrealizedPNL,'RealizedPNL:',realizedPNL,'AccountName:',accountName)
        # print(accountName)
        
        sym,pair=self.ContractToPair(contract)
        if sym[:12]=='Not In Pair:':
            pass
            # print(sym)
            return
        
        if len(self.open_trade[pair])!=0:
            for j in self.open_trade[pair]:
                self.trade[pair][j].update({'Average Price':averageCost})
                self.trade[pair][j].update({'Cumulative Quantity':abs(position)})
                self.trade[pair][j].update({'Unrealized PNL':round(unrealizedPNL/self.ConversionRate[contract.currency],2)})
                tradeRecord=dictTransform(self.trade)
                # print(tradeRecord,self.open_trade)
                toCSV(tradeRecord,self.open_trade)
                
            # update self.all_trades
            # condition=(self.all_trades['Symbol']==self.pair[self.reqId])&(self.all_trades['Cumulative Quantity']!=0)
            # self.all_trades.loc[self.all_trades[condition].index[-1],'Average Price']=round(self.all_trades.loc[self.all_trades[condition].index[-1],'Commision']+commissionReport.commission/self.ConversionRate[commissionReport.currency],2)
            # self.all_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv',index=1)
        
        try:
            self.all_positions.loc[sym]=sym,contract.secType,position,averageCost,round(unrealizedPNL/self.ConversionRate[contract.currency],2),round(realizedPNL/self.ConversionRate[contract.currency],2)
            self.all_positions.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_positions.csv',index=0 )  
            
            # update self.all_trades
            condition=(self.all_trades['Symbol']==sym)&(self.all_trades['Exit Price']==0)
            self.all_trades.loc[self.all_trades[condition].index[-1],'Unrealized PNL']=round(unrealizedPNL/self.ConversionRate[contract.currency],2)
            self.all_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv',index=1)
        except:
            pass

        return

    
    def commissionReport(self, commissionReport: CommissionReport):
        super().commissionReport(commissionReport)
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),"CommissionReport.", commissionReport)
        
        # Update trade dict
        if commissionReport.realizedPNL == UNSET_DOUBLE:
            try:
                self.trade[self.reqId][self.j]['Commision']=round(self.trade[self.reqId][self.j]['Commision']+commissionReport.commission/self.ConversionRate[commissionReport.currency],2)
                
                # update self.all_trades
                # condition=(self.all_trades['Symbol']==self.pair[self.reqId])
                condition=(self.all_trades['Symbol']==self.pair[self.reqId])&(self.all_trades['Exit Price']==0)
                self.all_trades.loc[self.all_trades[condition].index[-1],'Commision']=round(self.all_trades.loc[self.all_trades[condition].index[-1],'Commision']+commissionReport.commission/self.ConversionRate[commissionReport.currency],2)
                self.all_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv',index=1)
                
            except KeyError:
                pass
        else:
             
            try:
                self.trade[self.reqId][self.j].update({'Realized PNL':round(commissionReport.realizedPNL/self.ConversionRate[self.OrderContract[self.reqId].currency],2)})
                self.trade[self.reqId][self.j].update({'Unrealized PNL':0.0})
                self.trade[self.reqId][self.j]['Commision']=round(self.trade[self.reqId][self.j]['Commision']+commissionReport.commission/self.ConversionRate[commissionReport.currency],2)
                tradeRecord=dictTransform(self.trade)
                # print(tradeRecord,self.open_trade)
                toCSV(tradeRecord,self.open_trade)
            except:
                pass
                
            try: 
                # update self.all_trades
                condition=(self.all_trades['Symbol']==self.pair[self.reqId])&(self.all_trades['Exit Price']!=0)
                self.all_trades.loc[self.all_trades[condition].index[-1],'Commision']=round(self.all_trades.loc[self.all_trades[condition].index[-1],'Commision']+commissionReport.commission/self.ConversionRate[commissionReport.currency],2)
                self.all_trades.loc[self.all_trades[condition].index[-1],'Realized PNL']=round(commissionReport.realizedPNL/self.ConversionRate[self.OrderContract[self.reqId].currency],2)
                self.all_trades.loc[self.all_trades[condition].index[-1],'Unrealized PNL']=0.0
                self.all_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv',index=1)
                
            except:
                pass
        return



    def openOrder(self, orderId, contract: Contract, order: Order,orderState):
        super().openOrder(orderId, contract, order, orderState)
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),"OpenOrder. PermId: ", order.permId, "ClientId:", order.clientId, " OrderId:", orderId, 
        # "Account:", order.account, "Symbol:", contract.symbol, "SecType:", contract.secType,
        # "Exchange:", contract.exchange, "Action:", order.action, "OrderType:", order.orderType,
        # "TotalQty:", order.totalQuantity, "CashQty:", order.cashQty, 
        # "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status) 
        
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'OpenOrder:','PermId: ', order.permId," OrderId:", orderId, 
        # "Symbol:", contract.symbol,"Currency:", contract.currency, "SecType:", contract.secType,"Action:", order.action, "OrderType:", order.orderType,
        # "TotalQty:", order.totalQuantity, "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status) 
        
        
        sym,pair=self.ContractToPair(contract)
            
        if sym[:12]=='Not In Pair:':
            pass
            # print(sym)
            return
        
        
        
        if order.orderType=='STP' and np.isnan(self.SLOrderId[pair]):
            self.SLOrderId[pair]=orderId
        
        order.contract = contract
        # self.permId2ord[order.permId] = order
        
                
        return
    
    def openOrderEnd(self):
        super().openOrderEnd()
        # print("OpenOrderEnd") 
        # logging.debug("Received %d openOrders", len(self.permId2ord)) 
        return
    
    
    
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

    
    
    
    def orderStatus(self, orderId, status: str, filled: float,
        remaining: float, avgFillPrice: float, permId: int,
        parentId: int, lastFillPrice: float, clientId: int,
        whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled, remaining,
        avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        # print(datetime.fromtimestamp(int(datetime.now().timestamp())),'orderStatus:',"PermId:", permId,"Order Id:", orderId, "ParentId:", parentId, "Filled:", filled,"Remaining:", remaining, "AvgFillPrice:", avgFillPrice,  "LastFillPrice:",lastFillPrice,"Status:", status )

        
        return
    
    def completedOrder(self,contract:Contract,order:Order,orderState):
        # print('Contract',contract.symbol+contract.currency+contract.secType,'Order:',order,'orderState:',orderState)
        
        self.CompletedOrder=self.CompletedOrder.insert(0,contract)         
        
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
        
        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'contractDetails reqId',reqId,self.mode[reqId]+' '+self.direction[reqId]+' Pair:',self.pair[reqId],'minTick:','%f' % self.info[reqId].get('minTick'),'Round:',self.info[reqId]['round'],'MarketRule', contractDetails.marketRuleIds)
        # self.reqMarketRule(self.info[reqId].get('marketRule'))
        
        
        return

        
    # def contractDetailsEnd(self, reqId):
    #     # print("ContractDetailsEnd. ", reqId)
    #     # this is the logical end of your program
        
    #     return
    
    # def marketRule(self, marketRuleId: int, priceIncrements):
    #     super().marketRule(marketRuleId, priceIncrements)
    #     print(datetime.fromtimestamp(int(datetime.now().timestamp())),"Market Rule ID: ", marketRuleId)
    #     for priceIncrement in priceIncrements:
    #         print(datetime.fromtimestamp(int(datetime.now().timestamp())),"Price Increment.", priceIncrement)

    def ifDataDelay(self):
        w=5*self.timeframe1*60
        while True:
            if int(datetime.now().timestamp()) - self.LastReceivedDataTime >w:
                print(datetime.fromtimestamp(int(datetime.now().timestamp())),w,' sec delayed,last receieved:',datetime.fromtimestamp(self.LastReceivedDataTime))
                token,chatid=read_token()
                send('Data lag',token,chatid)
                self.stop()
                time.sleep(3)
                while True:
                    if not self.isConnected():
                        print(datetime.fromtimestamp(int(datetime.now().timestamp())),'Disconnected and Restart API')
                        if int(datetime.now().timestamp())-self.lastNoticeTime>300:
                            token,chatid=read_token()
                            send('Data lag',token,chatid)
                            self.lastNoticeTime=int(datetime.now().timestamp())
                        raise EOFError
                        
                    time.sleep(3)
            time.sleep(self.timeframe1*60)
        return
    
    
    # def ifDataDelay(self):
    #     w=5*self.timeframe1*60
        
    #     if int(datetime.now().timestamp()) - self.LastReceivedDataTime >w:
    #         if int(datetime.now().timestamp())-self.lastNoticeTime>300:
    #             print(datetime.fromtimestamp(int(datetime.now().timestamp())),w,' sec delayed,last receieved:',datetime.fromtimestamp(self.LastReceivedDataTime))
    #             token,chatid=read_token()
    #             send('Data lag',token,chatid)
    #             self.lastNoticeTime=int(datetime.now().timestamp())
        
    #     return
    
    def stop(self):
        for pair in range(len(self.pair)):
            self.cancelHistoricalData(pair)
        self.done=True
        self.disconnect()
        
        return
    
    
    
    # def restart(self):
        
    #     self.connect('127.0.0.1',7497,0) # IB TWS paper account
    #     time.sleep(2)
        
    #     for pair in range(len(self.pair)):
    #         self.reqHistoricalData(pair,self.QuoteContract[pair],'','1 W',str(self.timeframe1)+' mins','MIDPOINT',0,2,True,[])
    #     self.run()
    #     return

def read_token():
    config=configparser.ConfigParser()
    config.read('/Users/apple/Documents/code/Python/IBAPI/Settings/telegramConfig.cfg')
    token=config.get('Section_A','token')
    chatid=config.get('Section_A','chatid')
    return token,chatid

def send(text,token,chatid):
    params = {'chat_id':chatid, 'text': 'IB:'+text, 'parse_mode': 'HTML'}
    resp = requests.post('https://api.telegram.org/bot{}/sendMessage'.format(token), params)
    resp.raise_for_status()

# write trades record to csv
def toCSV(tradeRecord,openTrade):
    df_tradeRecord=pd.DataFrame.from_dict(tradeRecord,orient='index')
    df_tradeRecord.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/trades.csv',mode='w',index=1)
        
    df_openTrade=pd.DataFrame.from_dict(openTrade,orient='index')
    df_openTrade.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/openTrade.csv',mode='w',index=1)
        
    return

# write all_trades record to CSV
def toCSV1(all_trades):
    all_trades.to_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv',mode='w',index=1)
    

# read trades record from csv
'''
def fromCSV():
    dict_tradeRecord={}
    dict_openTrade={}
    df_tradeRecord=pd.read_csv('/Users/apple/Documents/code/Python/IBAPI/Output/trades.csv',index_col=0)
    for index in df_tradeRecord.index:
        dict_tradeRecord[index]=df_tradeRecord.loc[index].to_dict()
    dict_tradeRecord=dictTransform(dict_tradeRecord)
    df_openTrade=pd.read_csv('/Users/apple/Documents/code/Python/IBAPI/Output/openTrade.csv',index_col=0)
    df_openTrade['0']=df_openTrade['0'].fillna(-1)
    df_openTrade['0']=df_openTrade['0'].astype(int)
    df_openTrade['0']=df_openTrade['0'].astype(str)
    df_openTrade['0']=df_openTrade['0'].replace('-1',np.nan)
    for index in df_openTrade.index:
        dict_openTrade[index]=list(df_openTrade.loc[index])
    for key in dict_openTrade:
        if dict_openTrade[key]==[np.nan]:
            dict_openTrade[key]=[]
        else:
            dict_openTrade[key]=[int(x) for x in dict_openTrade[key]]
    return dict_tradeRecord,dict_openTrade
'''


def fromCSV0():
    dict_openTrade={}
    df_openTrade=pd.read_csv('/Users/apple/Documents/code/Python/IBAPI/Output/openTrade.csv',index_col=0)
    df_openTrade['0']=df_openTrade['0'].fillna(-1)
    df_openTrade['0']=df_openTrade['0'].astype(int)
    df_openTrade['0']=df_openTrade['0'].astype(str)
    df_openTrade['0']=df_openTrade['0'].replace('-1',np.nan)
    for index in df_openTrade.index:
        dict_openTrade[index]=list(df_openTrade.loc[index])
    for key in dict_openTrade:
        if dict_openTrade[key]==[np.nan]:
            dict_openTrade[key]=[]
        else:
            dict_openTrade[key]=[int(x) for x in dict_openTrade[key]]
    return dict_openTrade



# Read all_trades dataframe from CSV
def fromCSV():
    if not os.path.isfile('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv') or not os.path.isfile('/Users/apple/Documents/code/Python/IBAPI/Output/open_trades.csv'):
        return pd.DataFrame([], columns = ['DateTime', 'Symbol','Side','Price','Shares','Average Price','Cumulative Quantity','Exit Price','Unrealized PNL','Realized PNL','Commision','TP','SL']),pd.DataFrame([], columns = ['Symbol','Pair NO.','DateTime']) 
    elif os.path.isfile('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv') and os.path.isfile('/Users/apple/Documents/code/Python/IBAPI/Output/open_trades.csv'):
        df1=pd.read_csv('/Users/apple/Documents/code/Python/IBAPI/Output/all_trades.csv',index_col=0)
        df2=pd.read_csv('/Users/apple/Documents/code/Python/IBAPI/Output/open_trades.csv',index_col=0)
        return df1,df2
            
def main():
    # Connect
    app=TestApp()
    # app.connect('127.0.0.1',7497,1) # IB TWS
    # app.connect('127.0.0.1',7497,0) # IB TWS paper account
    app.connect('127.0.0.1',4002,0) # IB Gateway
    time.sleep(1)
    
    # Update Portfolio
    app.reqAccountUpdates(True,"") # update if open positions exist.

    # request historical data
    for pair in range(len(app.pair)):
        app.reqHistoricalData(pair,app.QuoteContract[pair],'','1 W',str(app.timeframe1)+' mins','MIDPOINT',0,2,True,[])
        if not app.OrderContract[pair].currency in app.ConversionRate and app.OrderContract[pair].currency !='USD':
            if app.OrderContract[pair].currency in ['EUR','GBP','AUD','NZD']:
                QuoteContract=app.xxxUSD(app.OrderContract[pair].currency)
                app.reqRealTimeBars(pair, QuoteContract, 5, "MIDPOINT", False, [])
            else:
                QuoteContract=app.USDxxx(app.OrderContract[pair].currency)
                app.reqRealTimeBars(pair, QuoteContract, 5, "MIDPOINT", False, [])
            
    # t = threading.Thread(target = app.ifDataDelay,name='CheckDelay')
    # t.daemon = True
    # t.start() 
    
    # app.start() 
    app.run()

if __name__=="__main__":
    while True:
        try:
            main()
        except EOFError as e:
            print(datetime.fromtimestamp(int(datetime.now().timestamp())),'main() error due to :',type(e),e)
            time.sleep(3)
        time.sleep(10)