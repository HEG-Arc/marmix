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

# Core Django imports

# Third-party app imports

# MarMix imports
from stocks.models import Stock
from simulation.models import Simulation

# Mostly copied from
# https://spring.io/blog/2010/08/19/building-rabbitmq-apps-using-python


class Ticker(object):
    def __init__(self, publisher, qname, simulation_id):
        self.publisher = publisher

        # This quickly creates four random stock symbols
        simulation = Simulation.objects.get(pk=simulation_id)
        stocks = Stock.objects.all().filter(simulation=simulation)

        # self.stock_symbols = [random_letter()+random_letter()+random_letter() for i in range(4)]
        self.stocks = stocks
        self.last_quote = False
        self.counter = 0
        self.time_format = "%a, %d %b %Y %H:%M:%S +0000"
        self.qname = qname

    def get_quote(self):
        symbol = random.choice(self.stocks)
        if symbol in self.last_quote:
            previous_quote = self.last_quote[symbol]
            new_quote = random.uniform(0.9*previous_quote, 1.1*previous_quote)
            if abs(new_quote) - 0 < 1.0:
                new_quote = 1.0
            self.last_quote[symbol] = new_quote
        else:
            new_quote = random.uniform(10.0, 250.0)
            self.last_quote[symbol] = new_quote
        self.counter += 1
        return (symbol, self.last_quote[symbol], time.gmtime(), self.counter)

        stock = random.choice(self.stocks)
        if stock in self.last_quote:
            pass


    def monitor(self):
        while True:
            quote = self.get_quote()
            print("New quote is %s" % str(quote))
            self.publisher.publish(pickle.dumps((quote[0], quote[1], time.strftime(self.time_format, quote[2]), quote[3])), routing_key="")
            secs = random.uniform(0.1, 0.5)
            #print("Sleeping %s seconds..." % secs)
            time.sleep(secs)