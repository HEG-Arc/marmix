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
from decimal import Decimal, getcontext
from random import randint
import time

# Core Django imports
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Sum

# Third-party app imports
import numpy as np

# MarMix imports
from config.celery import app
from simulations.models import Simulation, SimDay, Team, current_sim_day
from stocks.models import Stock, Order, TransactionLine, Transaction
from tickers.models import Ticker, TickerCompany, CompanyFinancial, CompanyShare
from .utils import geometric_brownian


@app.task
def main_ticker_task():
    running_simulations = Simulation.objects.all().filter(state=Simulation.RUNNING)
    for simulation in running_simulations:
        next_tick(simulation.id)
    print(running_simulations)
    return 'Tick-tack'


@app.task
def next_tick(simulation_id):
    simulation = Simulation.objects.get(pk=simulation_id)
    current = current_sim_day(simulation.id)
    if current['sim_round'] != 0:
        if current['timestamp'] < timezone.now()-datetime.timedelta(seconds=simulation.ticker.day_duration):
            # Simulation was already started, we continue
            current_day = current['sim_day']
            current_round = current['sim_round']
            cleanup_open_orders.apply_async(args=[simulation.id, current_round, current_day])
            if current_day == simulation.ticker.nb_days:
                if current_round == simulation.ticker.nb_rounds:
                    simulation.state = Simulation.FINISHED
                    if simulation.simulation_type == Simulation.INTRO or simulation.simulation_type == Simulation.ADVANCED:
                        prepare_dividends_payments.apply_async([simulation.id, current_round])
                    sim_day = SimDay(simulation=simulation, sim_round=current_round, sim_day=current_day+1, state=Simulation.FINISHED)
                    sim_day.save()
                else:
                    simulation.state = Simulation.PAUSED
                    if simulation.simulation_type == Simulation.INTRO or simulation.simulation_type == Simulation.ADVANCED:
                        prepare_dividends_payments.apply_async([simulation.id, current_round])
                    sim_day = SimDay(simulation=simulation, sim_round=current_round+1, sim_day=0, state=simulation.state)
                    sim_day.save()
                simulation.save()
            else:
                sim_day = SimDay(simulation=simulation, sim_round=current_round, sim_day=current_day+1, state=simulation.state)
                sim_day.save()
                stocks = Stock.objects.all().filter(simulation_id=simulation.id)
                for stock in stocks:
                    liquidity_trader_order.apply_async(args=[simulation.id, stock.id])
            print("Next tick processed: SIM: %s - R%sD%s @ %s" %
                  (sim_day.simulation_id, sim_day.sim_round, sim_day.sim_day, sim_day.timestamp))
        else:
            print("Not yet time...")
    else:
        # First start of the simulation
        sim_day = SimDay(simulation=simulation, sim_round=1, sim_day=1, state=simulation.state)
        sim_day.save()
        stocks = Stock.objects.all().filter(simulation_id=simulation.id)
        for stock in stocks:
            liquidity_trader_order.apply_async(args=[simulation.id, stock.id])


@app.task
def create_company_live(simulation_id, stock_id):
    simulation = Simulation.objects.get(pk=simulation_id)
    stock = Stock.objects.get(pk=stock_id)
    ticker = Ticker.objects.get(simulation=simulation)
    company = TickerCompany(ticker=ticker, stock=stock, symbol=stock.symbol, name="Company blue %s" % stock.symbol)
    company.save()


@app.task
def create_company_simulation(simulation_id, stock_id):
    getcontext().prec = 4
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
            daily_net_income = brownian_motion[i] / float(ticker.dividend_payoff_rate) * 100 * stock.quantity
            c = CompanyFinancial(company=company, daily_dividend=Decimal(daily_dividend), daily_net_income=Decimal(daily_net_income),
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
    previous_company_income = None
    for sim_round in range(0, rounds):
        stock_price = np.npv(0.1, simulation_dividends[sim_round:rounds]) + (simulation_dividends[-1]*(1+g)/(R-G))/np.power(1+R, rounds-sim_round)
        simulation_stock_price.append(stock_price)
        if previous_company_income:
            drift = simulation_net_income[sim_round] / float(previous_company_income.net_income) - 1
            previous_company_income.drift = Decimal(drift)
            previous_company_income.save()
        company_share = CompanyShare(company=company, share_value=Decimal(stock_price), dividends=Decimal(simulation_dividends[sim_round]),
                                     net_income=Decimal(simulation_net_income[sim_round]), drift=Decimal(drift), sim_round=sim_round)
        company_share.save()
        previous_company_income = company_share
        if sim_round == 0:
            stock.price = Decimal(stock_price)
            stock.save()
    return company.id


@app.task
def liquidity_trader_order(simulation_id, stock_id):
    simulation = Simulation.objects.get(pk=simulation_id)
    stock = Stock.objects.get(pk=stock_id)
    team = Team.objects.get(current_simulation_id=simulation_id, team_type=Team.LIQUIDITY_MANAGER)
    day_duration = simulation.ticker.day_duration
    first_order_type = [Order.BID, Order.ASK]
    second_order_type = first_order_type.pop(randint(0, 1))
    first_order_type = first_order_type[0]
    first_order_time = randint(0, int(day_duration/4*3/2))
    second_order_time = int(day_duration/4*3/2) - first_order_time + randint(0, int(day_duration/4*3/2))

    open_quantity = Order.objects.all().filter(stock_id=stock.id, order_type=second_order_type, price__isnull=False).aggregate(Sum('quantity'))['quantity__sum']
    if open_quantity:
        quantity = randint(0, int(open_quantity*0.15))
        if quantity > 0:
            create_order.apply_async(args=[stock.id, team.id, first_order_type, quantity], countdown=first_order_time)
    open_quantity = Order.objects.all().filter(stock_id=stock.id, order_type=first_order_type, price__isnull=False).aggregate(Sum('quantity'))['quantity__sum']
    if open_quantity:
        quantity = randint(0, int(open_quantity*0.15))
        if quantity > 0:
            create_order.apply_async(args=[stock.id, team.id, second_order_type, quantity], countdown=second_order_time)


@app.task
def create_order(stock_id, team_id, order_type, quantity):
    stock = Stock.objects.get(pk=stock_id)
    team = Team.objects.get(pk=team_id)
    new_order = Order(stock=stock, team=team, order_type=order_type, quantity=quantity)
    new_order.save()
    print("New order created: %s %s %s" % (stock.symbol, order_type, quantity))


@app.task
def cleanup_open_orders(simulation_id, current_round, current_day):
    team = Team.objects.get(current_simulation_id=simulation_id, team_type=Team.LIQUIDITY_MANAGER)
    print("Time to cleanup old liquidity trader orders for trader %s" % team)
    Order.objects.filter(team_id=team.id, transaction__isnull=True, sim_round=current_round, sim_day=current_day).delete()


@app.task
def prepare_dividends_payments(simulation_id, current_round):
    simulation = Simulation.objects.get(pk=simulation_id)
    companies = TickerCompany.objects.filter(ticker__simulation_id=simulation.id)
    for company in companies:
        stock_id = company.stock_id
        share = CompanyShare.objects.get(company_id=company.id, sim_round=current_round)
        dividend = share.dividends
        tl = TransactionLine.objects.filter(stock_id=stock_id).values('team').annotate(quantity=Sum('quantity')).order_by('team')
        if tl:
            execute_dividends_payments.apply_async(args=[simulation.id, stock_id, tl, dividend])


@app.task
def execute_dividends_payments(simulation_id, stock_id, tl, dividend):
    simulation = Simulation.objects.get(pk=simulation_id)
    stock = Stock.objects.get(pk=stock_id)
    transaction = Transaction(simulation=simulation, transaction_type=Transaction.EOR)
    transaction.save()
    for line in tl:
        team = Team.objects.get(pk=line['team'])
        transaction_line = TransactionLine(transaction=transaction, stock=stock, team=team, quantity=line['quantity'], price=dividend, amount=line['quantity']*dividend, asset_type=TransactionLine.DIVIDENDS)
        transaction_line.save()


@app.task
def set_closing_price(simulation_id):
    simulation = Simulation.objects.get(pk=simulation_id)
    stocks = simulation.stocks.all()
    for stock in stocks:
        share = CompanyShare.objects.get(company__stock=stock, sim_round=simulation.get_sim_day['sim_round'])
        stock.price = share.share_value
        stock.save()