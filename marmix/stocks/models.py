# -*- coding: UTF-8 -*-
# models.py
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
from decimal import Decimal, getcontext

# Core Django imports
from django.db import models, transaction
from django.utils.translation import ugettext_lazy as _
from django.db import connection

# Third-party app imports
from django_extensions.db.models import TimeStampedModel
import django_filters

# MarMix imports
from simulations.models import Simulation, Team, current_sim_day, stock_historical_prices, current_cash, current_shares
from .tasks import check_matching_orders, set_stock_quote, set_opening_price


class Stock(TimeStampedModel):
    """
    Stocks are shares of a company that are automatically generated during the simulation setup.
    """
    simulation = models.ForeignKey(Simulation, verbose_name=_("simulation"), related_name="stocks", help_text=_("Related simulation"))
    symbol = models.CharField(verbose_name=_("symbol"), max_length=4, help_text=_("Symbol of the stock (4 chars)"))
    name = models.CharField(verbose_name=_("name"), max_length=100, help_text=_("Full name of the stock"))
    description = models.TextField(verbose_name=_("description"), blank=True, help_text=_("Description of the stock (HTML)"))
    quantity = models.IntegerField(verbose_name=_("quantity"), default=1, help_text=_("Total quantity of stocks in circulation"))
    price = models.DecimalField(verbose_name=_("stock price"), max_digits=24, decimal_places=4,
                                default='0.0000', help_text=_("Current stock price"))
    opening_price = models.DecimalField(verbose_name=_("opening price"), max_digits=24, decimal_places=4,
                                        null=True, blank=True, help_text=_("Opening price"))

    class Meta:
        verbose_name = _('stock')
        verbose_name_plural = _('stocks')
        ordering = ['symbol']

    def _last_quote(self):
        try:
            last_quote = self.quotes.all()[0]
        except IndexError:
            last_quote = None
        return last_quote
    last_quote = property(_last_quote)

    def _historical_prices(self):
        return stock_historical_prices(self.id)
    historical_prices = property(_historical_prices)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.price != 0 and not self.opening_price:
            print("Preparing opening: STOCK %s @ %s" % (self.symbol, self.price))
            # It's an update and we have the first quotation for this stock
            self.opening_price = self.price
            models.Model.save(self, force_insert, force_update, using, update_fields)
            set_opening_price.apply_async([self.id, self.price])
        else:
            models.Model.save(self, force_insert, force_update, using, update_fields)

    def __str__(self):
        return self.symbol


class Quote(models.Model):
    """
    Quotes are the price of a given stock at a certain time.
    """
    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="quotes", help_text=_("Related stock"))
    price = models.DecimalField(verbose_name=_("stock price"), max_digits=24, decimal_places=4,
                                default='0.0000', help_text=_("Current stock price"))
    timestamp = models.DateTimeField(verbose_name=_("timestamp"), auto_now_add=True, help_text=_("Timestamp of the quote"))
    sim_round = models.IntegerField(verbose_name=_("round"), default=0, help_text=_("Current round"))
    sim_day = models.IntegerField(verbose_name=_("day"), default=0, help_text=_("Current day"))

    class Meta:
        verbose_name = _('quote')
        verbose_name_plural = _('quotes')
        ordering = ['-timestamp']

    def __str__(self):
        return "%s@%s R%sD%s (%s)" % (self.stock, self.price, self.sim_round, self.sim_day, self.timestamp)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        current = current_sim_day(self.stock.simulation_id)
        self.sim_round = current['sim_round']
        self.sim_day = current['sim_day']
        models.Model.save(self, force_insert, force_update, using, update_fields)


class HistoricalPrice(models.Model):
    """
    A summary of the quotes, updated each sim_day.
    """
    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="history", help_text=_("Related stock"))
    price_open = models.DecimalField(verbose_name=_("open"), max_digits=24, decimal_places=4,
                                     default='0.0000', help_text=_("Current stock price"))
    price_high = models.DecimalField(verbose_name=_("high"), max_digits=24, decimal_places=4,
                                     default='0.0000', help_text=_("Current stock price"))
    price_low = models.DecimalField(verbose_name=_("low"), max_digits=24, decimal_places=4,
                                    default='0.0000', help_text=_("Current stock price"))
    price_close = models.DecimalField(verbose_name=_("close"), max_digits=24, decimal_places=4,
                                      default='0.0000', help_text=_("Current stock price"))
    volume = models.IntegerField(verbose_name=_("volume"), help_text=_("Day volume"))
    sim_round = models.IntegerField(verbose_name=_("round"), default=0, help_text=_("Current round"))
    sim_day = models.IntegerField(verbose_name=_("day"), default=0, help_text=_("Current day"))
    timestamp = models.DateTimeField(verbose_name=_("timestamp"), auto_now_add=True, help_text=_("Timestamp of the historical price"))

    class Meta:
        verbose_name = _('historical price')
        verbose_name_plural = _('historical prices')
        ordering = ['-sim_round', '-sim_day']

    def __str__(self):
        return "%s R%sD%s O:%s | H:%s | L:%s | C:%s | V:%s" % (self.stock, self.sim_round, self.sim_day, self.price_open, self.price_high, self.price_low, self.price_close, self.volume)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.sim_round = current_sim_day(self.stock.simulation_id)['sim_round']
        self.sim_day = current_sim_day(self.stock.simulation_id)['sim_day']
        models.Model.save(self, force_insert, force_update, using, update_fields)


class Order(models.Model):
    """
    Orders are made by teams and posted in the order book. They are then processed by the order manager.
    BID is the highest price that a buyer is willing to pay for a stock.
    ASK is the lowest price that a seller is willing to accept for a stock.
    """
    BID = 'BID'
    ASK = 'ASK'
    ORDER_TYPE_CHOICES = (
        (BID, _('bid')),
        (ASK, _('ask')),
    )

    SUBMITTED = 'SUBMITTED'
    PROCESSED = 'PROCESSED'
    FAILED = 'FAILED'
    ORDER_STATE_CHOICES = (
        (SUBMITTED, _('submitted')),
        (PROCESSED, _('processed')),
        (FAILED, _('failed')),
    )

    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="orders", help_text=_("Related stock"))
    team = models.ForeignKey(Team, verbose_name=_("team"), related_name="orders", help_text=_("Team which placed the order"))
    order_type = models.CharField(verbose_name=_("type of order"), max_length=5, choices=ORDER_TYPE_CHOICES,
                                  default=BID, help_text=_("The type of order (bid/ask)"))
    quantity = models.IntegerField(verbose_name=_("quantity ordered"), default=0, help_text=_("Quantity ordered. If the total quantity can not be provided, a new order will be created with the balance"))
    price = models.DecimalField(verbose_name=_("price tag"), max_digits=24, decimal_places=4,
                                blank=True, null=True, help_text=_("Price tag for one stock. If NULL, best available price"))
    created_at = models.DateTimeField(verbose_name=_("created"), auto_now_add=True, help_text=_("Creation of the order"))
    transaction = models.ForeignKey('Transaction', verbose_name=_("transaction"), related_name="orders", null=True,
                                    blank=True, help_text=_("Related transaction"))
    state = models.CharField(verbose_name=_("state of the order"), max_length=25, choices=ORDER_STATE_CHOICES,
                             default=SUBMITTED, help_text=_("The state of the order (submitted/processed/failed)"))
    sim_round = models.IntegerField(verbose_name=_("round"), default=0, help_text=_("Current round"))
    sim_day = models.IntegerField(verbose_name=_("day"), default=0, help_text=_("Current day"))
    timestamp = models.DateTimeField(verbose_name=_("updated"), auto_now=True, help_text=_("Last update of the order"))

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')
        ordering = ['price', 'created_at']

    def __str__(self):
        if self.order_type == self.BID:
            quantity = self.quantity
        else:
            quantity = -1 * self.quantity
        return "%s: %s@%s" % (self.stock, quantity, self.price)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.sim_round = current_sim_day(self.stock.simulation_id)['sim_round']
        self.sim_day = current_sim_day(self.stock.simulation_id)['sim_day']
        if self.pk is None:
            self.state = self.SUBMITTED
        if self.state == self.SUBMITTED:
            models.Model.save(self, force_insert, force_update, using, update_fields)
            check_matching_orders.apply_async([self.id])
        else:
            models.Model.save(self, force_insert, force_update, using, update_fields)


class Transaction(models.Model):
    """
    Transactions are the result of order placed that are fulfilled.
    """
    ORDER = 'ORDER'
    EOR = 'EOR'
    INITIAL = 'INITIAL'
    EOS = 'EOS'
    TRANSACTION_TYPE_CHOICES = (
        (ORDER, _('stocks order fulfillment')),
        (EOR, _('end of round transactions')),
        (INITIAL, _('initial transactions')),
        (EOS, _('end of simulation transactions')),
    )

    simulation = models.ForeignKey(Simulation, verbose_name=_("simulation"), related_name="transactions",
                                   help_text=_("Related simulation"))
    fulfilled_at = models.DateTimeField(verbose_name=_("fulfilled"), auto_now_add=True, help_text=_("Fulfillment date"))
    transaction_type = models.CharField(verbose_name=_("type of transaction"), max_length=20,
                                        choices=TRANSACTION_TYPE_CHOICES, default=ORDER,
                                        help_text=_("The type of transaction"))
    sim_round = models.IntegerField(verbose_name=_("round"), default=0, null=True, help_text=_("Current round"))
    sim_day = models.IntegerField(verbose_name=_("day"), default=0, null=True, help_text=_("Current day"))

    class Meta:
        verbose_name = _('transaction')
        verbose_name_plural = _('transactions')
        ordering = ['-fulfilled_at']

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.sim_round = current_sim_day(self.simulation_id)['sim_round']
        self.sim_day = current_sim_day(self.simulation_id)['sim_day']
        models.Model.save(self, force_insert, force_update, using, update_fields)

    def __str__(self):
        return "%s" % self.id


class TransactionLine(models.Model):
    STOCKS = 'STOCKS'
    DIVIDENDS = 'DIVIDENDS'
    TRANSACTIONS = 'TRANSACTIONS'
    INTERESTS = 'INTERESTS'
    CASH = 'CASH'
    ASSET_TYPE_CHOICES = (
        (STOCKS, _('stocks')),
        (DIVIDENDS, _('dividends payment')),
        (TRANSACTIONS, _('costs of transaction')),
        (INTERESTS, _('interests payment')),
        (CASH, _('cash')),
    )
    transaction = models.ForeignKey('Transaction', verbose_name=_("transaction"), related_name="lines",
                                    help_text=_("Related transaction"))
    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="transactions", null=True, blank=True,
                              help_text=_("Related stock"))
    team = models.ForeignKey(Team, verbose_name=_("team"), related_name="transactions", help_text=_("Team"))
    quantity = models.IntegerField(verbose_name=_("quantity"), default=0, help_text=_("Quantity"))
    price = models.DecimalField(verbose_name=_("price tag"), max_digits=24, decimal_places=4,
                                blank=True, null=True, help_text=_("Price tag for one stock"))
    amount = models.DecimalField(verbose_name=_("amount"), max_digits=14, decimal_places=4,
                                 blank=True, null=True, help_text=_("Total amount (signed)"))
    asset_type = models.CharField(verbose_name=_("type of asset"), max_length=20, choices=ASSET_TYPE_CHOICES,
                                  default=STOCKS, help_text=_("The type of asset"))

    class Meta:
        verbose_name = _('transaction line')
        verbose_name_plural = _('transaction lines')
        ordering = ['-transaction_id']

    def __str__(self):
        return "%s-%s" % (self.transaction_id, self.id)


def create_generic_stocks(simulation_id):
    simulation = Simulation.objects.get(pk=simulation_id)
    char_shift = 65
    stocks_created = 0
    for i in range(0, simulation.ticker.nb_companies):
        symbol = 2*chr(i+char_shift)
        stock = Stock(simulation=simulation, symbol=symbol, name='Company %s' % symbol, quantity=simulation.nb_shares)
        stock.save()
        stocks_created += 1
    return stocks_created


def process_opening_transactions(simulation_id):
    getcontext().prec = 4
    simulation = Simulation.objects.get(pk=simulation_id)
    # deposit cash
    print("starting cash deposit....")
    cash_deposit = Transaction(simulation=simulation, transaction_type=Transaction.INITIAL)
    cash_deposit.save()
    for team in simulation.teams.all():
        if team.team_type == Team.PLAYERS:
            amount = simulation.capital
        elif team.team_type == Team.LIQUIDITY_MANAGER:
            amount = simulation.capital * simulation.nb_teams * 9
        else:
            amount = 0
        team.current_simulation = simulation
        team.save()
        deposit = TransactionLine(transaction=cash_deposit, team=team, quantity=1, price=amount,
                                  amount=amount, asset_type=TransactionLine.CASH)
        deposit.save()
    print("End cash deposit...")
    # deposit stocks
    print("starting stocks deposit....")
    for stock in simulation.stocks.all():
        print("Stock deposit %s" % stock.symbol)
        stocks_deposit = Transaction(simulation=simulation, transaction_type=Transaction.INITIAL)
        stocks_deposit.save()
        stock_quantity = stock.quantity
        allocation = int(stock_quantity*.1/(simulation.teams.count()-1))
        for team in simulation.teams.all():
            if team.team_type == Team.PLAYERS:
                quantity = allocation
            elif team.team_type == Team.LIQUIDITY_MANAGER:
                quantity = stock_quantity - ((simulation.teams.count()-1) * allocation)
            else:
                quantity = 0
            print("Stock deposit %s -> %s" % (stock.symbol, team.name))
            deposit = TransactionLine(transaction=stocks_deposit, team=team, quantity=quantity, price=Decimal(stock.price), stock=stock,
                                      amount=Decimal(quantity*stock.price), asset_type=TransactionLine.STOCKS)
            deposit.save()
    return True


@transaction.atomic
def process_order(simulation, sell_order, buy_order, quantity):
    """
    Fulfill two matching orders.

    .. note:: This is called by :func:`check_matching_orders`

    :param simulation: A simulation object.
    :param sell_order: An order object (sell).
    :param buy_order: An order object (buy).
    :param quantity: The quantity to exchange (could be a partial fulfillment).
    :return: Nothing.
    """
    stock = Stock.objects.get(pk=sell_order.stock.id)
    ready_to_process = True
    new_transaction = Transaction(simulation=simulation, transaction_type=Transaction.ORDER)
    new_transaction.save()
    price = 0
    new_sell_order = None
    new_buy_order = None
    if sell_order.price and not buy_order.price:
        price = sell_order.price
    elif buy_order.price and not sell_order.price:
        price = buy_order.price
    elif buy_order.price == sell_order.price:
        price = sell_order.price
    else:
        #  Should not happens
        #  TODO: How to choose the price?
        if buy_order.created_at <= sell_order.created_at:
            price = buy_order.price
        else:
            price = sell_order.price
    #if sell_order.team.team_type == Team.LIQUIDITY_MANAGER or buy_order.team.team_type == Team.LIQUIDITY_MANAGER:
    # TODO: Quick fix
    if stock.price == 0 and stock.opening_price == 0:
        # We open the market
        cursor = connection.cursor()
        cursor.execute('SELECT SUM(price * abs(quantity)) as price, SUM(abs(quantity)) as qty '
                       'FROM stocks_order '
                       'WHERE stock_id=%s AND state=%s', [stock.id, Order.SUBMITTED])
        weighted_mean_price = cursor.fetchone()
    elif price > Decimal(1.5) * stock.price or price < Decimal(0.5) * stock.price:
        ready_to_process = False
    if current_shares(sell_order.team_id, sell_order.stock_id) < quantity:
        ready_to_process = False
        sell_order.state = Order.FAILED
        sell_order.save()
    if current_cash(buy_order.team_id, simulation.id) < quantity * price:
        ready_to_process = False
        buy_order.state = Order.FAILED
        buy_order.save()
    if price > 0 and ready_to_process:
        sell = TransactionLine(transaction=new_transaction, stock=stock, team=sell_order.team,
                               quantity=-1*quantity, price=price, amount=-1*quantity*price,
                               asset_type=TransactionLine.STOCKS)
        sell_revenue = TransactionLine(transaction=new_transaction, team=sell_order.team,
                                       quantity=1, price=quantity*price, amount=quantity*price,
                                       asset_type=TransactionLine.CASH)
        buy = TransactionLine(transaction=new_transaction, stock=stock, team=buy_order.team,
                              quantity=quantity, price=price, amount=quantity*price,
                              asset_type=TransactionLine.STOCKS)
        buy_cost = TransactionLine(transaction=new_transaction, team=buy_order.team,
                                   quantity=quantity, price=-1*quantity*price, amount=-1*quantity*price,
                                   asset_type=TransactionLine.CASH)
        if sell_order.quantity != quantity:
            new_sell_order = Order(stock=stock, team=sell_order.team, order_type=sell_order.order_type,
                                   quantity=sell_order.quantity-quantity, price=sell_order.price,
                                   created_at=sell_order.created_at)
            sell_order.quantity = quantity
        if buy_order.quantity != quantity:
            new_buy_order = Order(stock=stock, team=buy_order.team, order_type=buy_order.order_type,
                                  quantity=buy_order.quantity-quantity, price=buy_order.price,
                                  created_at=buy_order.created_at)
            buy_order.quantity = quantity
        sell.save()
        sell_revenue.save()
        buy.save()
        buy_cost.save()
        sell_order.transaction = new_transaction
        sell_order.state = Order.PROCESSED
        sell_order.save()
        buy_order.transaction = new_transaction
        buy_order.state = Order.PROCESSED
        buy_order.save()
        set_stock_quote.apply_async([stock.id, price])
        if new_sell_order:
            new_sell_order.save()
        if new_buy_order:
            new_buy_order.save()
        if simulation.transaction_cost > 0:
            tc_sell = TransactionLine(transaction=new_transaction, team=sell_order.team,
                                      quantity=-1, price=simulation.transaction_cost,
                                      amount=-1*simulation.transaction_cost, asset_type=TransactionLine.TRANSACTIONS)
            tc_buy = TransactionLine(transaction=new_transaction, team=buy_order.team,
                                     quantity=-1, price=simulation.transaction_cost,
                                     amount=-1*simulation.transaction_cost, asset_type=TransactionLine.TRANSACTIONS)
            tc_sell.save()
            tc_buy.save()
        if simulation.variable_transaction_cost > 0:
            transaction_price = float(price) * simulation.variable_transaction_cost / 100
            tc_sell = TransactionLine(transaction=new_transaction, team=sell_order.team,
                                      quantity=-1*quantity, price=Decimal(transaction_price),
                                      amount=Decimal(-1*quantity*transaction_price),
                                      asset_type=TransactionLine.TRANSACTIONS)
            tc_buy = TransactionLine(transaction=new_transaction, team=buy_order.team,
                                     quantity=-1*quantity, price=Decimal(transaction_price),
                                     amount=Decimal(-1*quantity*transaction_price),
                                     asset_type=TransactionLine.TRANSACTIONS)
            tc_sell.save()
            tc_buy.save()


def dividends_list(team_id):
    team = Team.objects.get(pk=team_id)
    sim_round = None
    dividends = {}
    round_list = []
    transaction_lines = TransactionLine.objects.select_related('stock', 'transaction').filter(transaction__simulation_id=team.current_simulation_id).filter(
                        team_id=team.id).filter(asset_type=TransactionLine.DIVIDENDS).order_by('transaction__sim_round', 'stock__symbol')
    for tl in transaction_lines:
        if sim_round != tl.transaction.sim_round:
            if sim_round:
                dividends[sim_round-1] = round_list
                round_list = []
            sim_round = tl.transaction.sim_round
        dividend = {'id': tl.id, 'price': tl.price, 'quantity': tl.quantity, 'amount': tl.amount, 'stock': tl.stock.symbol, 'stock_id': tl.stock.id}
        round_list.append(dividend)
    if sim_round:
        dividends[sim_round-1] = round_list
    else:
        dividends[0] = round_list
    return dividends
