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
import datetime

# Core Django imports
from django.core.cache import cache
from django.utils import timezone

# Third-party app imports

# MarMix imports
from config.celery import app
from simulations.models import Simulation, SimDay, current_sim_day
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
    current = current_sim_day(simulation.id)
    if current['sim_round'] != 0:
        if current['timestamp'] < timezone.now()-datetime.timedelta(seconds=simulation.ticker.day_duration):
            # Simulation was already started, we continue
            current_day = current['sim_day']
            current_round = current['sim_round']
            if current_day == simulation.ticker.nb_days:
                if current_round == simulation.ticker.nb_rounds:
                    simulation.state = Simulation.FINISHED
                    sim_day = SimDay.objects.filter(simulation_id=simulation.id)[0]
                    sim_day.state = Simulation.FINISHED
                    sim_day.save()
                else:
                    simulation.state = Simulation.PAUSED
                    sim_day = SimDay(simulation=simulation, sim_round=current_round+1, sim_day=0, state=simulation.state)
                    sim_day.save()
                simulation.save()
            else:
                sim_day = SimDay(simulation=simulation, sim_round=current_round, sim_day=current_day+1, state=simulation.state)
                sim_day.save()
            print("Next tick processed: SIM: %s - R%sD%s @ %s" %
                  (sim_day.simulation_id, sim_day.sim_round, sim_day.sim_day, sim_day.timestamp))
        else:
            print("Not yet time...")
    else:
        # First start of the simulation
        sim_day = SimDay(simulation=simulation, sim_round=1, sim_day=1, state=simulation.state)
        sim_day.save()