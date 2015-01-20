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
from __future__ import absolute_import

# Core Django imports
from django.core.cache import cache

# Third-party app imports

# MarMix imports
from config.celery import app
from simulation.models import Simulation
from tickers.models import TickerTick


@app.task
def main_ticker_task():
    running_simulations = Simulation.objects.all().filter(state=Simulation.RUNNING)
    for simulation in running_simulations:
        next_tick(simulation)
    print(running_simulations)
    return 'Hello'


@app.task
def next_tick(simulation):
    if simulation.ticker.last_tick:
        current_day = simulation.ticker.last_tick.sim_day
        current_round = simulation.ticker.last_tick.sim_round
        if current_day == simulation.ticker.nb_days:
            if current_round == simulation.ticker.nb_rounds:
                simulation.state = Simulation.FINISHED
            else:
                simulation.state = Simulation.PAUSED
                ticker = TickerTick(ticker=simulation.ticker, sim_round=current_round+1, sim_day=0)
                ticker.save()
            simulation.save()
        else:
            ticker = TickerTick(ticker=simulation.ticker, sim_round=current_round, sim_day=current_day+1)
            ticker.save()
    else:
        ticker = TickerTick(ticker=simulation.ticker, sim_round=1, sim_day=1)
        ticker.save()
    return ticker