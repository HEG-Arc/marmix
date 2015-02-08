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
from decimal import Decimal

# Core Django imports
from django.core.cache import cache
from django.utils import timezone

# Third-party app imports
import numpy as np

# MarMix imports
from config.celery import app
from simulations.models import Simulation, SimDay, current_sim_day
from stocks.models import Stock
from tickers.models import Ticker, TickerCompany, CompanyFinancial, CompanyShare
from .utils import geometric_brownian


@app.task
def main_ticker_task():
    running_simulations = Simulation.objects.all().filter(state=Simulation.RUNNING)
    for simulation in running_simulations:
        next_tick(simulation.id)
    print(running_simulations)
    return 'Hello'


@app.task
def next_tick(simulation_id):
    simulation = Simulation.objects.get(pk=simulation_id)
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


@app.task
def create_company_simulation(simulation_id, stock_id):
    mu = 0.02
    sigma = 0.1
    simulation = Simulation.objects.get(pk=simulation_id)
    stock = Stock.objects.get(pk=stock_id)
    ticker = Ticker.objects.get(simulation=simulation)
    company = TickerCompany(ticker=ticker, stock=stock, symbol=stock.symbol, name="Company %s" % stock.symbol)
    company.save()
    rounds = ticker.nb_rounds + 1
    brownian_motion = geometric_brownian(rounds, mu, sigma, ticker.initial_value, rounds/(ticker.nb_days*rounds), stock_id)
    i = 0
    simulation_dividends = []
    simulation_net_income = []
    for sim_round in range(0, rounds):
        round_dividend = 0
        round_net_income = 0
        for sim_day in range(1, ticker.nb_days+1):
            # We have each round/day and the corresponding dividend
            daily_dividend = brownian_motion[i]
            daily_net_income = Decimal(brownian_motion[i]) / ticker.dividend_payoff_rate * 100 * stock.quantity
            c = CompanyFinancial(company=company, daily_dividend=daily_dividend, daily_net_income=daily_net_income,
                                 sim_round=sim_round, sim_day=sim_day, sim_date=sim_round*100+sim_day)
            c.save()
            round_dividend += daily_dividend
            round_net_income += daily_net_income
            i += 1
        simulation_dividends.append(round_dividend)
        simulation_net_income.append(round_net_income)

    # Share price estimation
    G = simulation_dividends[-1]/simulation_dividends[-2]-1
    R = 0.1
    g = R
    drift = 0
    simulation_stock_price = []
    previous_company_share = None
    for sim_round in range(0, rounds):
        stock_price = np.npv(0.1, simulation_dividends[sim_round:rounds]) + (simulation_dividends[-1]*(1+g)/(R-G))/np.power(1+R, rounds-sim_round)
        simulation_stock_price.append(stock_price)
        if previous_company_share:
            drift = stock_price / previous_company_share.share_value - 1
            previous_company_share.drift = drift
            previous_company_share.save()
        company_share = CompanyShare(company=company, share_value=stock_price, dividends=simulation_dividends[sim_round],
                                     net_income=simulation_net_income[sim_round], drift=drift, sim_round=sim_round)
        company_share.save()
        previous_company_share = company_share
        if sim_round == 0:
            stock.opening_price = stock_price
            stock.price = stock_price
            stock.save()
    return company