import pdb
import uuid

import requests
from webull_open import WeBullApi


class PaperApi(WeBullApi):
    def __init__(self):
        super().__init__()
        self.paper_account_id = ''

    def get_account(self):
        """ Get important details of paper account """
        headers = self.build_req_headers()
        response = requests.get(
            self.urls.paper_account(self.paper_account_id), headers=headers)
        return response.json()

    def get_account_id(self):
        """
        Get paper account id: call this before paper acct actions
        """
        headers = self.build_req_headers()

        response = requests.get(self.urls.paper_account_id(), headers=headers)
        result = response.json()
        self.paper_account_id = result[0]['id']
        return True

    def get_current_orders(self):
        """
        Open paper trading orders
        """
        return self.get_account()['openOrders']

    def get_positions(self):
        """
        Current positions in paper trading account.
        """
        return self.get_account()['positions']

    def place_order(self,
                    stock=None,
                    tId=None,
                    price=0,
                    action='BUY',
                    orderType='LMT',
                    enforce='GTC',
                    quant=0):
        """
        Place a paper account order.
        """
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')

        headers = self.build_req_headers(
            include_trade_token=True, include_time=True)

        data = {
            'action': action,  #  BUY or SELL
            'lmtPrice': float(price),
            'orderType': orderType,  # "LMT","MKT"
            'outsideRegularTradingHour': True,
            'quantity': int(quant),
            'serialId': str(uuid.uuid4()),
            'tickerId': tId,
            'timeInForce': enforce
        }  # GTC or DAY

        response = requests.post(
            self.urls.paper_place_order(self.paper_account_id, tId),
            json=data,
            headers=headers)
        return response.json()

    def modify_order(self,
                     order,
                     price=0,
                     action='BUY',
                     orderType='LMT',
                     enforce='GTC',
                     quant=0):
        """
        Modify a paper account order.
        """
        headers = self.build_req_headers()

        data = {
            'action': action,  #  BUY or SELL
            'lmtPrice': float(price),
            'orderType': orderType,
            'comboType': "NORMAL",  # "LMT","MKT"
            'outsideRegularTradingHour': True,
            'serialId': str(uuid.uuid4()),
            'tickerId': order['ticker']['tickerId'],
            'timeInForce': enforce
        }  # GTC or DAY

        if quant == 0 or quant == order['totalQuantity']:
            data['quantity'] = order['totalQuantity']
        else:
            data['quantity'] = int(quant)

        response = requests.post(
            self.urls.paper_modify_order(self.paper_account_id,
                                         order['orderId']),
            json=data,
            headers=headers)
        if response:
            return True
        else:
            print("Modify didn't succeed. {} {}".format(
                response, response.json()))
            return False

    def cancel_order(self, order_id):
        """
        Cancel a paper account order.
        """
        headers = self.build_req_headers()
        response = requests.post(
            self.urls.paper_cancel_order(self.paper_account_id, order_id),
            headers=headers)
        return bool(response)


if __name__ == "__main__":
    api = PaperApi()