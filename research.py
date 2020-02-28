import pdb

import random

import pandas as pd
from sklearn.linear_model import LinearRegression
import yfinance

TICKER = 'TQQQ'
STRATEGY = 'random'


def calculate_pnl(row):
    TAKE_PROFIT = 0.02
    STOP_LOSS = 0.05
    # STOP_LOSS = 0.1
    if row['Direction'] == 1:  # long
        if row['Open/Low'] >= STOP_LOSS:  # 止损
            return -STOP_LOSS
        elif row['High/Open'] >= TAKE_PROFIT:  # 止盈
            return TAKE_PROFIT
        else:
            return (row['Close'] - row['Open']) / row['Open']  # 收盘平仓
    else:  # short
        if row['High/Open'] >= STOP_LOSS:
            return -STOP_LOSS
        elif row['Open/Low'] >= TAKE_PROFIT:
            return TAKE_PROFIT
        else:
            return (row['Open'] - row['Close']) / row['Open']  # 收盘平仓


def estimate_dev(row):
    x, y, z = 0.41, 0.48, 0.29
    return x * row['Open_jump'] + y * row['Deviation_d1'] + z * row['Deviation_d2']


def get_hist_and_preprocess():
    stock = yfinance.Ticker(TICKER)
    pv = stock.history(period='max', actions=False)
    pv.reset_index(level=0, inplace=True)
    pv['Year'] = pv.apply(lambda row: row['Date'].year, axis=1)
    return pv
    pv_d1 = pv.copy()  # delay 1 pv
    pv_d1['Date'] = pv_d1['Date'].shift(-1)
    pv_d1.columns = [
        'Date', 'Open_d1', 'High_d1', 'Low_d1', 'Close_d1', 'Volume_d1'
    ]
    pv_d2 = pv.copy()  # delay 2 pv
    pv_d2['Date'] = pv_d2['Date'].shift(-2)
    pv_d2.columns = [
        'Date', 'Open_d2', 'High_d2', 'Low_d2', 'Close_d2', 'Volume_d2'
    ]
    pv = pd.merge(pv, pv_d1, how='inner', on='Date')
    pv = pd.merge(pv, pv_d2, how='inner', on='Date')

    pv['High/Open'] = pv.apply(
        lambda row: (row['High'] - row['Open']) / row['Open'], axis=1)
    pv['Open/Low'] = pv.apply(
        lambda row: (row['Open'] - row['Low']) / row['Open'], axis=1)

    pv['Deviation'] = pv.apply(
        lambda row: (row['High'] - row['Low']) / row['Open'], axis=1)
    pv['Deviation_d1'] = pv.apply(
        lambda row: (row['High_d1'] - row['Low_d1']) / row['Open_d1'], axis=1)
    pv['Deviation_d2'] = pv.apply(
        lambda row: (row['High_d2'] - row['Low_d2']) / row['Open_d2'], axis=1)
    pv['Open_jump'] = pv.apply(
        lambda row: abs(row['Open'] - row['Close_d1']) / row['Close_d1'],
        axis=1)
    pv['estimated_dev'] = pv.apply(estimate_dev, axis=1)
    pv['ret_d1'] = pv.apply(
        lambda row: (row['Close_d1'] - row['Open_d1']) / row['Open_d1'],
        axis=1)
    pv = pv[[
        'Date', 'Open', 'High', 'Low', 'Close', 'estimated_dev', 'ret_d1',
        'Deviation', 'Open/Low', 'High/Open', 'Close_d1'
    ]]
    # X = pv[['Open_jump', 'Deviation_d1', 'Deviation_d2']]
    # y = pv['Deviation']
    # reg = LinearRegression(fit_intercept=False).fit(X, y)
    # print(TICKER, reg.score(X, y))
    # pdb.set_trace()
    # apply strategy, o for short, 1 for long
    pv['Direction'] = pv.apply(
        lambda row: 1 if row['Open'] >= row['Close_d1'] else 0, axis=1)
    pv['PnL'] = pv.apply(calculate_pnl, axis=1)
    print(pv['PnL'].describe())
    # pdb.set_trace()


if __name__ == "__main__":
    pv = get_hist_and_preprocess()
    threshold = 0.003
    pv['Yes'] = pv.apply(
        lambda row: ((row['Open'] - row['Low']) / row['Open'] >= threshold) & ((row['High'] - row['Open']) / row['Open'] >= threshold),
        axis=1)
    # pdb.set_trace()
    for year, group in pv.groupby(['Year']):
        print(year, group['Yes'].value_counts())