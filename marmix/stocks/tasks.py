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
    from .models import Stock, Order, process_order
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
                    if qty_sold > 0 and buy_order.team != sell_order.team:
                        if buy_order.quantity >= qty_sold:
                            #  We can fulfill the whole order
                            qty_traded = qty_sold
                        else:
                            #  We fulfill a partial order and look for the next one
                            qty_traded = buy_order.quantity
                        qty_sold -= qty_traded
                        process_order(simulation, sell_order, buy_order, qty_traded)
                        print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (stock, qty_traded, sell_order.team, buy_order.team))
        else:
            print("No available market_sell_orders")
        if market_buy_orders and sell_orders:
            print("market_buy_orders")
            for buy_order in market_buy_orders:
                qty_bought = buy_order.quantity
                for sell_order in sell_orders:
                    if qty_bought > 0 and buy_order.team != sell_order.team:
                        if sell_order.quantity >= qty_bought:
                            #  We can fulfill the whole order
                            qty_traded = qty_bought
                        else:
                            #  We fulfill a partial order and look for the next one
                            qty_traded = sell_order.quantity
                        qty_bought -= qty_traded
                        process_order(simulation, sell_order, buy_order, qty_traded)
                        print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (stock, qty_traded, sell_order.team, buy_order.team))
        else:
            print("No available market_buy_orders")
        if sell_orders and buy_orders:
            print("sell_orders")
            for sell_order in sell_orders:
                qty_sold = sell_order.quantity
                for buy_order in buy_orders:
                    if sell_order.price <= buy_order.price and buy_order.team != sell_order.team:
                        if qty_sold > 0:
                            if buy_order.quantity >= qty_sold:
                                #  We can fulfill the whole order
                                qty_traded = qty_sold
                            else:
                                #  We fulfill a partial order and look for the next one
                                qty_traded = buy_order.quantity
                            qty_sold -= qty_traded
                            process_order(simulation, sell_order, buy_order, qty_traded)
                            print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (stock, qty_traded, sell_order.team, buy_order.team))
        else:
            print("No available sell_orders")
        if buy_orders and sell_orders:
            print("buy_orders")
            for buy_order in buy_orders:
                qty_bought = buy_order.quantity
                for sell_order in sell_orders:
                    if sell_order.price <= buy_order.price and buy_order.team != sell_order.team:
                        if qty_bought > 0:
                            if sell_order.quantity >= qty_bought:
                                #  We can fulfill the whole order
                                qty_traded = qty_bought
                            else:
                                #  We fulfill a partial order and look for the next one
                                qty_traded = sell_order.quantity
                            qty_bought -= qty_traded
                            process_order(simulation, sell_order, buy_order, qty_traded)
                            print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (stock, qty_traded, sell_order.team, buy_order.team))
        else:
            print("No available buy_orders")
    return "Processed!"


@app.task
def check_matching_orders(order):
    """
    Looks for matching orders in the order book.

    :param order: An order object
    :return : None
    """
    from .models import Stock, Order, process_order
    if order.order_type == Order.ASK:
        book_order_type = Order.BID
    else:
        book_order_type = Order.ASK
    if not order.price:
        # This is a market order
        order_book = Order.objects.filter(stock=order.stock).filter(transaction__isnull=True).filter(order_type=book_order_type).filter(price__isnull=False)
        if order_book:
            qty = order.quantity
            for match_order in order_book:
                if match_order.team != order.team:
                    if match_order.quantity >= qty:
                        #  We can fulfill the whole order
                        qty_traded = qty
                    else:
                        #  We fulfill a partial order and look for the next one
                        qty_traded = match_order.quantity
                    if order.order_type == Order.ASK:
                        sell_order = order
                        buy_order = match_order
                    else:
                        sell_order = match_order
                        buy_order = order
                    process_order(order.stock.simulation, sell_order, buy_order, qty_traded)
                    print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (order.stock, qty_traded, sell_order.team, buy_order.team))
                    break
    else:
        # This is a limit order
        order_book = Order.objects.filter(stock=order.stock).filter(transaction__isnull=True).filter(order_type=book_order_type).filter(price__isnull=True)
        if order_book:
            qty = order.quantity
            for match_order in order_book:
                if match_order.team != order.team:
                    if match_order.quantity >= qty:
                        #  We can fulfill the whole order
                        qty_traded = qty
                    else:
                        #  We fulfill a partial order and look for the next one
                        qty_traded = match_order.quantity
                    if order.order_type == Order.ASK:
                        sell_order = order
                        buy_order = match_order
                    else:
                        sell_order = match_order
                        buy_order = order
                    process_order(order.stock.simulation, sell_order, buy_order, qty_traded)
                    print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (order.stock, qty_traded, sell_order.team, buy_order.team))
                    break
        else:
            order_book = Order.objects.filter(stock=order.stock).filter(transaction__isnull=True).filter(order_type=book_order_type).filter(price__isnull=False)
            if order_book:
                qty = order.quantity
                for match_order in order_book:
                    if order.order_type == Order.ASK:
                        sell_order = order
                        buy_order = match_order
                    else:
                        sell_order = match_order
                        buy_order = order
                    if match_order.team != order.team and sell_order.price <= buy_order.price:
                        if match_order.quantity >= qty:
                            #  We can fulfill the whole order
                            qty_traded = qty
                        else:
                            #  We fulfill a partial order and look for the next one
                            qty_traded = match_order.quantity
                        process_order(order.stock.simulation, sell_order, buy_order, qty_traded)
                        print("New transaction: STOCK: %s QTY: %s SELLER: %s BUYER: %s" % (order.stock, qty_traded, sell_order.team, buy_order.team))
                        break