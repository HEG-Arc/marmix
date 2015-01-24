# -*- coding: UTF-8 -*-
# tasks.py
#
# Copyright (C) 2014 HES-SO//HEG Arc
#
# Author(s): Cédric Gaspoz <cedric.gaspoz@he-arc.ch>
#
# This file is part of MarMix.
#
# MarMix is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MarMix is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MarMix. If not, see <http://www.gnu.org/licenses/>.

# Stdlib imports

# Core Django imports
from django.utils.translation import ugettext as _

# Third-party app imports
from async_messages import messages

# MarMix imports
from config.celery import app
from simulations.models import Simulation, Team, create_liquidity_manager
from tickers.models import TickerTick

@app.task
def match_orders(simulation):
    """
    Looks for matching orders in the order book.
    :param simulation:
    :return None:
    """
    from .models import Stock, Order
    available_stocks = Stock.objects.filter(simulation=simulation)
    for stock in available_stocks:
        print("Stock: %s" % stock.symbol)
        market_sell_orders = Order.objects.filter(stock=stock).filter(transaction__isnull=True).filter(order_type=Order.ASK).filter(price__isnull=True)
        sell_orders = Order.objects.filter(stock=stock).filter(transaction__isnull=True).filter(order_type=Order.ASK).filter(price__isnull=False)
        market_buy_orders = Order.objects.filter(stock=stock).filter(transaction__isnull=True).filter(order_type=Order.BID).filter(price__isnull=True)
        buy_orders = Order.objects.filter(stock=stock).filter(transaction__isnull=True).filter(order_type=Order.BID).filter(price__isnull=False)
        if market_sell_orders and buy_orders:
            print("market_sell_orders")
            for sell_order in market_sell_orders:
                qty_sold = sell_order.quantity
                for buy_order in buy_orders:
                    if qty_sold > 0:
                        if buy_order.quantity >= qty_sold:
                            #  We can fulfill the whole order
                            qty_traded = qty_sold
                        else:
                            #  We fulfill a partial order and look for the next one
                            qty_traded = buy_order.quantity
                        qty_sold -= qty_traded
                        print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (stock, qty_traded, sell_order.team, buy_order.team))
        else:
            print("No available market_sell_orders")
        if market_buy_orders and sell_orders:
            print("market_buy_orders")
            for buy_order in market_buy_orders:
                qty_bought = buy_order.quantity
                for sell_order in sell_orders:
                    if qty_bought > 0:
                        if sell_order.quantity >= qty_bought:
                            #  We can fulfill the whole order
                            qty_traded = qty_bought
                        else:
                            #  We fulfill a partial order and look for the next one
                            qty_traded = sell_order.quantity
                        qty_bought -= qty_traded
                        print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (stock, qty_traded, sell_order.team, buy_order.team))
        else:
            print("No available market_buy_orders")
        if sell_orders and buy_orders:
            print("sell_orders")
            for sell_order in sell_orders:
                qty_sold = sell_order.quantity
                for buy_order in buy_orders:
                    if sell_order.price <= buy_order.price:
                        if qty_sold > 0:
                            if buy_order.quantity >= qty_sold:
                                #  We can fulfill the whole order
                                qty_traded = qty_sold
                            else:
                                #  We fulfill a partial order and look for the next one
                                qty_traded = buy_order.quantity
                            qty_sold -= qty_traded
                            print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (stock, qty_traded, sell_order.team, buy_order.team))
        else:
            print("No available sell_orders")
        if buy_orders and sell_orders:
            print("buy_orders")
            for buy_order in buy_orders:
                qty_bought = buy_order.quantity
                for sell_order in sell_orders:
                    if sell_order.price <= buy_order.price:
                        if qty_bought > 0:
                            if sell_order.quantity >= qty_bought:
                                #  We can fulfill the whole order
                                qty_traded = qty_bought
                            else:
                                #  We fulfill a partial order and look for the next one
                                qty_traded = sell_order.quantity
                            qty_bought -= qty_traded
                            print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (stock, qty_traded, sell_order.team, buy_order.team))
        else:
            print("No available buy_orders")