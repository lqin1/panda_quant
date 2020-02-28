import pdb

import hashlib
import time
from datetime import datetime
import pickle
import os

import uuid
import getpass
import requests
from pandas import DataFrame
from pytz import timezone

from endpoints import Urls


class WeBullApi():
    def __init__(self):
        self.urls = Urls()
        self.session = requests.session()
        self.headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
        }
        # self.auth_method = self.login_prompt
        self.did = self._get_did()
        self.access_token = ''
        self.account_id = ''
        self.refresh_token = ''
        self.token_expire = ''
        self.trade_token = ''
        self.uuid = ''
        self.trade_pin = ''
        self.get_trade_token()

    def _get_did(self):
        """
        Makes a unique device id from a random uuid (uuid.uuid4).
        if the pickle file doesn't exist, this func will generate a random 32 character hex string
        uuid and save it in a pickle file for future use. if the file already exists it will
        load the pickle file to reuse the did. Having a unique did appears to be very important
        for the MQTT web socket protocol
        :return: hex string of a 32 digit uuid
        """
        if os.path.exists('did.bin'):
            did = pickle.load(open('did.bin', 'rb'))
        else:
            did = uuid.uuid4().hex
            pickle.dump(did, open('did.bin', 'wb'))
        return did

    def build_req_headers(self, include_trade_token=False, include_time=False):
        '''
        Build default set of header params
        '''
        headers = self.headers
        headers['did'] = self.did
        headers['access_token'] = self.access_token
        if include_trade_token:
            headers['t_token'] = self.trade_token
        if include_time:
            headers['t_time'] = str(round(time.time() * 1000))
        return headers

    def login(self, username='', password=''):
        password = ('wl_app-a&b@!423^' + password).encode('utf-8')
        md5_hash = hashlib.md5(password)
        data = {
            'account': username,
            'accountType': 2,
            'deviceId': self.did,
            'pwd': md5_hash.hexdigest(),
            'regionId': 13
        }
        response = requests.post(
            self.urls.login(), json=data, headers=self.headers)

        result = response.json()
        if 'data' in result and 'accessToken' in result['data']:
            self.access_token = result['data']['accessToken']
            self.refresh_token = result['data']['refreshToken']
            self.token_expire = result['data']['tokenExpireTime']
            self.uuid = result['data']['uuid']
            self.get_account_id()
            return True
        else:
            return False

    def login_prompt(self):
        """
        End login session
        """
        uname = input("Enter Webull Username:")
        pwd = getpass.getpass("Enter Webull Password:")
        self.trade_pin = getpass.getpass("Enter 6 digit Webull Trade PIN:")
        self.login(uname, pwd)
        return self.get_trade_token(self.trade_pin)

    def logout(self):
        """
        End login session
        """
        headers = self.build_req_headers()
        response = requests.get(self.urls.logout(), headers=headers)
        if response.status_code != 200:
            return False
        else:
            return True

    def refresh_login(self):
        headers = self.build_req_headers()
        data = {'refreshToken': self.refresh_token}
        response = requests.post(
            self.urls.refresh_login() + self.refresh_token,
            json=data,
            headers=headers)

        result = response.json()
        if 'accessToken' in result and result['accessToken'] != '' and result['refreshToken'] != '' and result['tokenExpireTime'] != '':
            self.access_token = result['accessToken']
            self.refresh_token = result['refreshToken']
            self.token_expire = result['tokenExpireTime']
            return True
        else:
            return False

    def get_detail(self):
        '''
        get some contact details of your account name, email/phone, region, avatar...etc
        '''
        headers = self.build_req_headers()

        response = requests.get(self.urls.user(), headers=headers)
        result = response.json()

        return result

    def get_account_id(self):
        '''
        get account id
        call account id before trade actions
        '''
        headers = self.build_req_headers()

        response = requests.get(self.urls.account_id(), headers=headers)
        result = response.json()

        if result['success']:
            self.account_id = str(result['data'][0]['secAccountId'])
            return True
        else:
            return False

    def get_account(self):
        '''
        get important details of account, positions, portfolio stance...etc
        '''
        headers = self.build_req_headers()

        response = requests.get(
            self.urls.account(self.account_id), headers=headers)
        result = response.json()

        return result

    def get_positions(self):
        '''
        output standing positions of stocks
        '''
        data = self.get_account()

        return data['positions']

    def get_portfolio(self):
        '''
        output numbers of portfolio
        '''
        data = self.get_account()

        output = {}
        for item in data['accountMembers']:
            output[item['key']] = item['value']

        return output

    def get_current_orders(self):
        '''
        Get open/standing orders
        '''
        data = self.get_account()

        return data['openOrders']

    def get_history_orders(self, status='Cancelled'):
        '''
        Historical orders, can be cancelled or filled
        status = Cancelled / Filled / Working / Partially Filled / Pending / Failed / All
        '''
        headers = self.build_req_headers(
            include_trade_token=True, include_time=True)
        response = requests.get(
            self.urls.orders(self.account_id) + str(status), headers=headers)

        return response.json()

    def get_trade_token(self, password=''):
        '''
        Trading related
        authorize trade, must be done before trade action
        '''
        headers = self.build_req_headers()

        # with webull md5 hash salted
        password = ('wl_app-a&b@!423^' + password).encode('utf-8')
        md5_hash = hashlib.md5(password)
        # password = md5_hash.hexdigest()
        data = {'pwd': md5_hash.hexdigest()}

        response = requests.post(
            self.urls.trade_token(), json=data, headers=headers)
        result = response.json()

        if result['success']:
            self.trade_token = result['data']['tradeToken']
            return True
        else:
            return False

    def get_ticker(self, stock=''):
        '''
        lookup ticker_id
        '''
        response = requests.get(self.urls.stock_id(stock))
        result = response.json()

        ticker_id = 0
        if len(result['list']) == 1:
            for item in result['list']:
                ticker_id = item['tickerId']
        return ticker_id

    def place_order(self,
                    stock='',
                    price=0,
                    action='BUY',
                    orderType='LMT',
                    enforce='GTC',
                    quant=0):
        '''
        ordering
        action: BUY / SELL
        ordertype : LMT / MKT / STP / STP LMT
        timeinforce:  GTC / DAY / IOC
        '''
        headers = self.build_req_headers(
            include_trade_token=True, include_time=True)

        data = {
            'action': action,
            'lmtPrice': float(price),
            'orderType': orderType,
            'outsideRegularTradingHour': True,
            'quantity': int(quant),
            'serialId': str(uuid.uuid4()),
            'tickerId': self.get_ticker(stock),
            'timeInForce': enforce
        }

        response = requests.post(
            self.urls.place_orders(self.account_id),
            json=data,
            headers=headers)
        result = response.json()

        return result['orderId']

    def cancel_order(self, order_id=''):
        '''
        retract an order
        '''
        headers = self.build_req_headers(
            include_trade_token=True, include_time=True)

        data = {}

        response = requests.post(
            self.urls.cancel_order(self.account_id) + str(order_id) + '/' +
            str(uuid.uuid4()),
            json=data,
            headers=headers)
        result = response.json()

        return result['success']

    def get_quote(self, stock=None, tId=None):
        '''
        get price quote
        '''
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')

        response = requests.get(self.urls.quotes(tId))
        result = response.json()

        return result

    def get_tradable(self, stock=''):
        '''
        get if stock is tradable
        '''
        response = requests.get(self.urls.is_tradable(self.get_ticker(stock)))
        return response.json()

    def get_active_gainer_loser(self, direction='gainer'):
        '''
        gets active / gainer / loser stocks sorted by change
        direction: active / gainer / loser
        '''
        headers = self.build_req_headers()

        params = {'regionId': 6, 'userRegionId': 6}
        response = requests.get(
            self.urls.active_gainers_losers(direction),
            params=params,
            headers=headers)
        result = response.json()
        result = sorted(result, key=lambda k: k['change'], reverse=True)

        return result

    def get_analysis(self, stock=None):
        '''
        get analysis info and returns a dict of analysis ratings
        '''
        return requests.get(self.urls.analysis(self.get_ticker(stock))).json()

    def get_financials(self, stock=None):
        '''
        get financials info and returns a dict of financial info
        '''
        return requests.get(self.urls.fundamentals(
            self.get_ticker(stock))).json()

    def get_news(self, stock=None, Id=0, items=20):
        '''
        get news and returns a list of articles
        params:
            Id: 0 is latest news article
            items: number of articles to return
        '''
        params = {'currentNewsId': Id, 'pageSize': items}
        return requests.get(
            self.urls.news(self.get_ticker(stock)), params=params).json()

    def get_bars(self,
                 stock=None,
                 tId=None,
                 interval='m1',
                 count=1,
                 extendTrading=0):
        '''
        get bars returns a pandas dataframe
        params:
            interval: m1, m5, m15, m30, h1, h2, h4, d1, w1
            count: number of bars to return
            extendTrading: change to 1 for pre-market and afterhours bars
        '''
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')

        params = {
            'type': interval,
            'count': count,
            'extendTrading': extendTrading
        }
        df = DataFrame(
            columns=['open', 'high', 'low', 'close', 'volume', 'vwap'])
        df.index.name = 'timestamp'
        response = requests.get(self.urls.bars(tId), params=params)
        result = response.json()
        time_zone = timezone(result[0]['timeZone'])
        pdb.set_trace()
        for row in result[0]['data']:
            row = row.split(',')
            row = ['0' if value == 'null' else value for value in row]
            data = {
                'open': float(row[1]),
                'high': float(row[3]),
                'low': float(row[4]),
                'close': float(row[2]),
                'volume': float(row[6]),
                'vwap': float(row[7])
            }
            df.loc[datetime.fromtimestamp(int(
                row[0])).astimezone(time_zone)] = data
        return df.iloc[::-1]

    def get_dividends(self):
        """ Return account's dividend info """
        headers = self.build_req_headers()
        data = {}
        response = requests.post(
            self.urls.dividends(self.account_id), json=data, headers=headers)
        return response.json()


if __name__ == "__main__":
    webull = WeBullApi()
    webull.login('qinlincn@gmail.com', '****')
    webull.get_trade_token('***')
    order_id = webull.place_order(
        'TQQQ', 90, action='SELL', orderType='LMT', enforce='DAY', quant=1)
    webull.cancel_order(order_id)
