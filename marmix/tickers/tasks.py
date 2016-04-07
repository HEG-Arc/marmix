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
import re
import xml.etree.ElementTree as ET

# Core Django imports
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Sum
from django.db import connection
from django.conf import settings

# Third-party app imports
import numpy as np
import requests
from bs4 import BeautifulSoup
import pymssql

# MarMix imports
from config.celery import app
from simulations.models import Simulation, SimDay, Team, current_sim_day, current_shares
from stocks.models import Stock, Order, TransactionLine, Transaction, process_order
from tickers.models import Ticker, TickerCompany, CompanyFinancial, CompanyShare
from .utils import geometric_brownian


def dictfetchall(cursor):
    """
    Returns all rows from a cursor as a dict

    :param cursor:
    :return:
    """
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


def format_soap_request(simulation):
    host = simulation.ticker.host
    port = simulation.ticker.port
    application = simulation.ticker.application
    system = simulation.ticker.system
    client = simulation.ticker.client
    url = 'http://%s:%s/%s/WS' % (host, port, application)
    xmldata = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://ws.erpsim.hec.ca/">
           <soapenv:Header/>
           <soapenv:Body>
              <ws:getSimState>
                 <arg0>
                     <displayingAllNews>false</displayingAllNews>
                     <erpClient>%s</erpClient>
                     <erpSystem>%s</erpSystem>
                     <loggedOut>false</loggedOut>
                     <password>ERPSIM</password>
                     <role>TEAM_MEMBER</role>
                     <simulationNumber>01</simulationNumber>
                     <teamId>0</teamId>
                     <updated>false</updated>
                     <username>A1</username>
                 </arg0>
                 <arg1>-1</arg1>
                 <arg2>0</arg2>
              </ws:getSimState>
           </soapenv:Body>
        </soapenv:Envelope>""" % (client, system)
    return url, xmldata


def clock_erpsim(simulation_id, full=False):
    # int(soup.nbRounds.string)
    # int(float(soup.roundDurationInMinutes.string))
    simulation = Simulation.objects.select_related('ticker').get(pk=simulation_id)
    current_round = False
    current_day = False
    url, xmldata = format_soap_request(simulation)
    headers = {'Content-Type': 'text/xml'}
    try:
        r = requests.post(url, data=xmldata, headers=headers)
    except:
        # TODO check to limit the scope...
        r = None
    if r and r.status_code == requests.codes.ok:
        soup = BeautifulSoup(r.text, 'lxml-xml')

        m = re.findall('(\d+)', soup.date.string)
        if len(m) == 1:
            # We received a ##quarterDayEndShort('2')
            current_round = int(m[0])
            current_day = simulation.ticker.nb_days+1
        elif len(m) == 2:
            # We received a ##quarterDayShort('3', '1')
            current_round = int(m[0])
            current_day = int(m[1])
    print("ERPsim clock: %s/%s" % (current_round, current_day))
    if not full:
        return current_round, current_day
    else:
        full_clock = {'current_round': current_round, 'current_day': current_day, 'nb_teams': int(soup.nbTeams.string),
                      'max_rounds': int(soup.nbRounds.string),
                      'max_days': int(float(soup.roundDurationInMinutes.string))}
        return full_clock


def create_mssql_simulation(simulation_id):
    simulation = Simulation.objects.select_related('ticker').get(pk=simulation_id)
    conn = pymssql.connect(settings.MSSQL_HOST, settings.MSSQL_USER, settings.MSSQL_PASSWORD, settings.MSSQL_DATABASE)
    cursor = conn.cursor()
    # TODO get ride of the 2-steps construction of the sql requests
    sql = "CREATE LOGIN %s WITH PASSWORD='MARMIX', CHECK_EXPIRATION=OFF, CHECK_POLICY=OFF" % simulation.ticker.userkey
    cursor.execute(sql)
    conn.commit()
    sql = "CREATE USER %s FOR LOGIN %s" % (simulation.ticker.userkey, simulation.ticker.userkey)
    cursor.execute(sql)
    conn.commit()
    sql = "GRANT SELECT TO %s" % simulation.ticker.userkey
    cursor.execute(sql)
    conn.commit()
    cursor.execute("INSERT INTO MARMIX_SIMULATION (USERKEY, GAMEID, CURRENT_DAY, CURRENT_ROUND, SIMULATIONID) VALUES (%s, %d, 0, 0, %d)",
                   (simulation.ticker.userkey, simulation.ticker.gameid, simulation_id))
    conn.commit()

    # List of teams
    list_of_teams = []
    cursor.execute("SELECT DISTINCT COMPANYCODE FROM MUESLI_SALES_T WHERE GAMEID=%d ORDER BY COMPANYCODE", simulation.ticker.gameid)
    row = cursor.fetchone()
    while row:
        list_of_teams.append(row[0])
        row = cursor.fetchone()
    nb_teams = len(list_of_teams)

    # Duration
    cursor.execute("SELECT MAX(SIM_ROUND) FROM MUESLI_SALES_T WHERE GAMEID=%d", simulation.ticker.gameid)
    row = cursor.fetchone()
    max_rounds = row[0]
    cursor.execute("SELECT MAX(VDAY) FROM MUESLI_SALES_T WHERE GAMEID=%d", simulation.ticker.gameid)
    row = cursor.fetchone()
    max_days = row[0]
    conn.close()
    return {'nb_teams': nb_teams, 'max_rounds': max_rounds, 'max_days': max_days, 'list_of_teams': list_of_teams}


def update_mssql_time(simulation_id):
    current = current_sim_day(simulation_id)
    conn = pymssql.connect(settings.MSSQL_HOST, settings.MSSQL_USER, settings.MSSQL_PASSWORD, settings.MSSQL_DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE MARMIX_SIMULATION SET CURRENT_DAY=%d, CURRENT_ROUND=%d WHERE SIMULATIONID=%d",
                   (current['sim_day'], current['sim_round'], simulation_id))
    conn.commit()
    conn.close()


@app.task
def main_ticker_task():
    # Called every X seconds by Celery-BEAT (value fixed in config/common.py)
    running_simulations = Simulation.objects.all().filter(state=Simulation.RUNNING)
    for simulation in running_simulations:
        next_tick(simulation.id)
    print(running_simulations)
    return 'Tick-tack'


@app.task
def next_tick(simulation_id):
    simulation = Simulation.objects.select_related('ticker').get(pk=simulation_id)
    last_clock = current_sim_day(simulation_id)
    clock = True
    # We have two sorts of clocks: internal or external
    if simulation.simulation_type == Simulation.LIVE:
        # The clock is external
        current_round, current_day = clock_erpsim(simulation_id)
        if not current_round or not current_day:
            clock = False
    else:
        # The clock is internal
        if last_clock['timestamp'] < timezone.now()-datetime.timedelta(seconds=simulation.ticker.day_duration):
            current_round = last_clock['sim_round']
            current_day = last_clock['sim_day']+1
        else:
            current_round = last_clock['sim_round']
            current_day = last_clock['sim_day']
    if clock:
        if last_clock['sim_round'] != 0:
            # We push the clock
            if last_clock['sim_day'] != current_day:
                cleanup_open_orders.apply_async(args=[simulation_id, last_clock['sim_round'], last_clock['sim_day']])
                if last_clock['sim_day'] == simulation.ticker.nb_days:
                    if last_clock['sim_round'] == simulation.ticker.nb_rounds:
                        simulation.state = Simulation.FINISHED
                        if simulation.simulation_type == Simulation.INTRO or simulation.simulation_type == Simulation.ADVANCED:
                            prepare_dividends_payments.apply_async([simulation.id, current_round])
                        sim_day = SimDay(simulation=simulation, sim_round=last_clock['sim_round'], sim_day=last_clock['sim_day'], state=Simulation.FINISHED)
                        sim_day.save()
                    else:
                        simulation.state = Simulation.PAUSED
                        if simulation.simulation_type == Simulation.INTRO or simulation.simulation_type == Simulation.ADVANCED:
                            prepare_dividends_payments.apply_async([simulation.id, current_round])
                        sim_day = SimDay(simulation=simulation, sim_round=last_clock['sim_round']+1, sim_day=0, state=simulation.state)
                        sim_day.save()
                    simulation.save()
                else:
                    sim_day = SimDay(simulation=simulation, sim_round=current_round, sim_day=current_day, state=simulation.state)
                    sim_day.save()
                    stocks = Stock.objects.all().filter(simulation_id=simulation.id)
                    for stock in stocks:
                        liquidity_trader_order.apply_async(args=[simulation.id, stock.id])
                    market_maker.apply_async(args=[simulation.id])
                if simulation.simulation_type == Simulation.INDEXED:
                    update_mssql_time(simulation.id)
                print("Next tick processed: SIM: %s - R%sD%s @ %s" %
                      (sim_day.simulation_id, sim_day.sim_round, sim_day.sim_day, sim_day.timestamp))
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
    company = TickerCompany(ticker=ticker, stock=stock, symbol=stock.symbol, name="Company %s" % stock.symbol)
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
    R = 0.15
    g = R
    drift = 0
    simulation_stock_price = []
    previous_company_income = None
    for sim_round in range(0, rounds):
        stock_price = np.npv(0.15, simulation_dividends[sim_round:rounds]) + (simulation_dividends[-1]*(1+g)/(R-G))/np.power(1+R, rounds-sim_round)
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
    shares = current_shares(team.id, stock.id)
    day_duration = simulation.ticker.day_duration
    first_order_type = [Order.BID, Order.ASK]
    second_order_type = first_order_type.pop(randint(0, 1))
    first_order_type = first_order_type[0]
    first_order_time = randint(0, int(day_duration/4*3/2))
    second_order_time = int(day_duration/4*3/2) - first_order_time + randint(0, int(day_duration/4*3/2))

    #open_quantity = Order.objects.all().filter(stock_id=stock.id, order_type=second_order_type, price__isnull=False, quantity__lt=200).aggregate(Sum('quantity'))['quantity__sum']
    #if open_quantity:
    quantity = randint(0, int(shares*0.05))
    if quantity > 0:
        create_order.apply_async(args=[stock.id, team.id, first_order_type, quantity], countdown=first_order_time)
    #open_quantity = Order.objects.all().filter(stock_id=stock.id, order_type=first_order_type, price__isnull=False, quantity__lt=200).aggregate(Sum('quantity'))['quantity__sum']
    #if open_quantity:
    quantity = randint(0, int(shares*0.05))
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
    orders = Order.objects.filter(team_id=team.id, transaction__isnull=True, sim_round=current_round, sim_day=current_day)
    for order in orders:
        order.state = Order.FAILED
        order.save()


@app.task
def prepare_dividends_payments(simulation_id, current_round):
    simulation = Simulation.objects.get(pk=simulation_id)
    if simulation.simulation_type == Simulation.INTRO or simulation.simulation_type == Simulation.ADVANCED or simulation.simulation_type == Simulation.INDEXED or simulation.simulation_type == Simulation.LIVE:
        companies = TickerCompany.objects.filter(ticker__simulation_id=simulation.id)
        for company in companies:
            stock_id = company.stock_id
            share = CompanyShare.objects.get(company_id=company.id, sim_round=current_round)
            dividend = share.dividends
            tl = TransactionLine.objects.filter(stock_id=stock_id).filter(asset_type=TransactionLine.STOCKS).filter(transaction__sim_round__lte=current_round).values('team').annotate(quantity=Sum('quantity')).order_by('team')
            if tl:
                execute_dividends_payments.apply_async(args=[simulation.id, stock_id, tl, dividend])
    else:
        # TODO Calculate the dividends based on the MSSQL server data
        pass


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


def retrieve_open_market_orders(simulation_id):
    for stock in Stock.objects.filter(simulation_id=simulation_id):
        open_bid_orders = Order.objects.filter(stock_id=stock.id).filter(order_type=Order.BID).filter(state=Order.SUBMITTED).filter(price__isnull=True).order_by('timestamp')
        if open_bid_orders:
            limit_ask_orders = Order.objects.filter(stock_id=stock.id).filter(order_type=Order.ASK).filter(state=Order.SUBMITTED).filter(price__isnull=False).order_by('price')
            bid_qty = 0
            ask_qty = 0
            ask_order = 0
            for order in open_bid_orders:
                bid_qty = order.quantity
                ask_qty = limit_ask_orders[ask_order].quantity
    pass


@app.task
def market_maker(simulation_id):
    simulation = Simulation.objects.get(pk=simulation_id)
    # We process all matching orders
    # TODO We do not match market orders. We need to match NULL price on one side
    cursor = connection.cursor()
    cursor.execute('SELECT s.symbol as symbol, a.id as ask_id, b.id as bid_id, a.quantity as ask_qty, b.quantity as bid_qty '
                   'FROM stocks_order a '
                   'LEFT OUTER JOIN stocks_order b ON a.stock_id = b.stock_id AND round(a.price,2) = round(b.price,2) '
                   'LEFT JOIN stocks_stock s ON a.stock_id = s.id '
                   'WHERE a.order_type=%s AND b.order_type=%s AND a.state=%s AND b.state=%s AND a.team_id != b.team_id AND s.simulation_id=%s',
                   [Order.ASK, Order.BID, Order.SUBMITTED, Order.SUBMITTED, simulation.id])
    orders_list = dictfetchall(cursor)
    for order in orders_list:
        print("Matching order for stock %s" % order['symbol'])
        if order['ask_qty'] > order['bid_qty']:
            quantity = order['bid_qty']
        elif order['ask_qty'] < order['bid_qty']:
            quantity = order['ask_qty']
        else:
            quantity = order['bid_qty']
        sell_order = Order.objects.get(pk=order['ask_id'])
        buy_order = Order.objects.get(pk=order['bid_id'])
        process_order(simulation, sell_order, buy_order, quantity, force=True)

    # TODO Really?
    stocks = simulation.stocks.all()
    for stock in stocks:
        # Make market liquid
        try:
            max_bid = Order.objects.filter(state=Order.SUBMITTED, stock=stock, order_type=Order.BID).order_by('-price')[0]
            bid = max_bid.price
        except IndexError:
            bid = False
        try:
            min_ask = Order.objects.filter(state=Order.SUBMITTED, stock=stock, order_type=Order.ASK).order_by('price')[0]
            ask = min_ask.price
            # TODO Implement better check!
            if ask:
                if ask > Decimal(999):
                    ask = False
        except IndexError:
            ask = False

        if bid and ask:
            nb_bid = Order.objects.filter(state=Order.SUBMITTED, stock=stock, order_type=Order.BID).count()
            nb_ask = Order.objects.filter(state=Order.SUBMITTED, stock=stock, order_type=Order.ASK).count()
            spread = ask - bid
            best_price = bid + spread * Decimal(nb_ask / (nb_bid+nb_ask))
            stock.price = best_price
            stock.save()
            print("New price for %s: %s" % (stock.symbol, best_price))
        elif bid:
            # We only have bid orders, so the market price is the max_bid
            best_price = bid
            stock.price = best_price
            stock.save()
            print("New price for %s [BID]: %s" % (stock.symbol, best_price))
        elif ask:
            # We only have bid orders, so the market price is the max_bid
            best_price = ask
            stock.price = best_price
            stock.save()
            print("New price for %s [ASK]: %s" % (stock.symbol, best_price))
