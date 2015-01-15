# -*- coding: UTF-8 -*-
# ticker.py
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
import pickle
import random
import time
from decimal import Decimal
from math import exp, sqrt, log
from random import gauss

# Core Django imports

# Third-party app imports
import pika

# MarMix imports
from .models import Ticker, TickerStock, TickerQuote
from simulation.models import Simulation

# Mostly copied from
# https://spring.io/blog/2010/08/19/building-rabbitmq-apps-using-python


class TickerRun(object):
    def __init__(self, publisher, qname, ticker_id):
        self.publisher = publisher

        # This quickly creates four random stock symbols
        ticker = Ticker.objects.get(pk=ticker_id)
        stocks = TickerStock.objects.all().filter(ticker=ticker)

        # self.stock_symbols = [random_letter()+random_letter()+random_letter() for i in range(4)]
        self.stocks = stocks
        self.counter = 0
        self.qname = qname
        self.S0 = 100
        self.r = 0.05
        self.sigma = 0.2
        self.T = 1.0
        self.M = 50
        self.dt = self.T / self.M

    def get_quote(self):
        stock = random.choice(self.stocks)
        if stock.last_quote:
            last_quote = float(stock.last_quote.price)
        else:
            last_quote = float(self.S0)
        z = gauss(0.0, 1.0)
        new_quote = last_quote * exp((self.r - 0.5 * self.sigma ** 2) * self.dt + self.sigma * sqrt(self.dt) * z)
            # previous_quote = float(stock.last_quote.price)
            # new_quote = random.uniform(0.9*previous_quote, 1.1*previous_quote)
            # if abs(new_quote) - 0 < 1.0:
            #     new_quote = 1.0
        quote = TickerQuote(price=Decimal(new_quote), stock=stock)
        quote.save()
        # else:
        #     new_quote = random.uniform(10.0, 250.0)
        #     quote = TickerQuote(price=Decimal(new_quote), stock=stock)
        #     quote.save()
        # self.counter += 1
        return quote

    def monitor(self):
        while True:
            quote = self.get_quote()
            print("New quote is %s @ %s [tick: %s]" % (quote.stock.name, quote.price, self.counter))
            #self.publisher.publish(pickle.dumps(quote), routing_key="")
            secs = random.uniform(1, 5)
            print("Sleeping %s seconds..." % secs)
            time.sleep(secs)


class PikaPublisher(object):
    def __init__(self, exchange_name):
        self.exchange_name = exchange_name
        self.queue_exists = False

    def publish(self, message, routing_key):
        conn = pika.AsyncoreConnection(pika.ConnectionParameters(
                '127.0.0.1',
                credentials=pika.PlainCredentials('marmix', 'marmix')))

        ch = conn.channel("")

        ch.exchange_declare(exchange=self.exchange_name, type="fanout", durable=False, auto_delete=False)

        ch.basic_publish(exchange=self.exchange_name,
                         routing_key=routing_key,
                         body=message,
                         properties=pika.BasicProperties(
                                content_type = "text/plain",
                                delivery_mode = 2, # persistent
                                ),
                         block_on_flow_control = True)
        ch.close()
        conn.close()

    def monitor(self, qname, callback):
        conn = pika.AsyncoreConnection(pika.ConnectionParameters(
                '127.0.0.1',
                credentials=pika.PlainCredentials('marmix', 'marmix')))

        ch = conn.channel("")

        if not self.queue_exists:
            ch.queue_declare(queue=qname, durable=False, exclusive=False, auto_delete=False)
            ch.queue_bind(queue=qname, exchange=self.exchange_name)
            print("Binding queue %s to exchange %s" % (qname, self.exchange_name))
            #ch.queue_bind(queue=qname, exchange=self.exchange_name, routing_key=qname)
            self.queue_exists = True

        ch.basic_consume(callback, queue=qname)

        pika.asyncore_loop()
        print('Close reason:', conn.connection_close)