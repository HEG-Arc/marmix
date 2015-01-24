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
from django.utils import timezone
# Core Django imports
from django.db import models
from django.utils.translation import ugettext_lazy as _

# Third-party app imports
from django_extensions.db.models import TimeStampedModel

# MarMix imports
from simulations.models import Simulation, Team
from .tasks import match_orders


class Stock(TimeStampedModel):
    """
    Stocks are shares of a company that are automatically generated during the simulation setup.
    """
    simulation = models.ForeignKey(Simulation, verbose_name=_("simulation"), related_name="stocks", help_text=_("Related simulation"))
    symbol = models.CharField(verbose_name=_("symbol"), max_length=4, help_text=_("Symbol of the stock (4 chars)"))
    name = models.CharField(verbose_name=_("name"), max_length=100, help_text=_("Full name of the stock"))
    description = models.TextField(verbose_name=_("description"), blank=True, help_text=_("Description of the stock (HTML)"))
    quantity = models.IntegerField(verbose_name=_("quantity"), default=1, help_text=_("Total quantity of stocks in circulation"))

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

    def __str__(self):
        return self.symbol


class Quote(models.Model):
    """
    Quotes are the price of a given stock at a certain time.
    """
    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="quotes", help_text=_("Related stock"))
    price = models.DecimalField(verbose_name=_("stock price"), max_digits=14, decimal_places=4,
                                          default='0.0000', help_text=_("Current stock price"))
    timestamp = models.DateTimeField(verbose_name=_("timestamp"), auto_now_add=True, help_text=_("Timestamp of the quote"))

    class Meta:
        verbose_name = _('quote')
        verbose_name_plural = _('quotes')
        ordering = ['-timestamp']

    def __str__(self):
        return "%s - %s (%s)" % (self.stock, self.price, self.timestamp)


class Order(models.Model):
    """
    Orders are made by teams and posted in the order book. They are then processed by the order manager.
    BID is the highest price that a buyer is willing to pay for a stock.
    ASK is the lowest price that a seller is willing to accept for a stock.
    """
    BID = 'BID'
    ASK = 'ASK'
    SIMULATION_TYPE_CHOICES = (
        (BID, _('bid')),
        (ASK, _('ask')),
    )

    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="orders", help_text=_("Related stock"))
    team = models.ForeignKey(Team, verbose_name=_("team"), related_name="orders", help_text=_("Team which placed the order"))
    order_type = models.CharField(verbose_name=_("type of order"), max_length=5, choices=SIMULATION_TYPE_CHOICES,
                                  default=BID, help_text=_("The type of order (bid/ask)"))
    quantity = models.IntegerField(verbose_name=_("quantity ordered"), default=0, help_text=_("Quantity ordered. If the total quantity can not be provided, a new order will be created with the balance"))
    price = models.DecimalField(verbose_name=_("price tag"), max_digits=14, decimal_places=4,
                                blank=True, null=True, help_text=_("Price tag for one stock. If NULL, best available price"))
    created_at = models.DateTimeField(verbose_name=_("created"), auto_now_add=True, help_text=_("Creation of the order"))
    transaction = models.ForeignKey('Transaction', verbose_name=_("transaction"), related_name="orders", null=True,
                                    blank=True, help_text=_("Related transaction"))

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
        if self.transaction is None:
            match_orders.apply_async([self.stock.simulation])
        models.Model.save(self, force_insert, force_update, using, update_fields)


class Transaction(models.Model):
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
    """
    Transactions are the result of order placed that are fulfilled.
    """
    simulation = models.ForeignKey(Simulation, verbose_name=_("simulation"), related_name="transactions",
                                   help_text=_("Related simulation"))
    fulfilled_at = models.DateTimeField(verbose_name=_("fulfilled"), auto_now_add=True, help_text=_("Fulfillment date"))
    transaction_type = models.CharField(verbose_name=_("type of transaction"), max_length=20,
                                        choices=TRANSACTION_TYPE_CHOICES, default=ORDER,
                                        help_text=_("The type of transaction"))

    class Meta:
        verbose_name = _('transaction')
        verbose_name_plural = _('transactions')
        ordering = ['-fulfilled_at']

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
        (CASH, _('cash deposit')),
    )
    transaction = models.ForeignKey('Transaction', verbose_name=_("transaction"), related_name="lines",
                                    help_text=_("Related transaction"))
    stock = models.ForeignKey('Stock', verbose_name=_("stock"), related_name="transactions", null=True, blank=True,
                              help_text=_("Related stock"))
    team = models.ForeignKey(Team, verbose_name=_("team"), related_name="transactions", help_text=_("Team"))
    quantity = models.IntegerField(verbose_name=_("quantity"), default=0, help_text=_("Quantity"))
    price = models.DecimalField(verbose_name=_("price tag"), max_digits=14, decimal_places=4,
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


def create_generic_stocks(simulation):
    char_shift = 65
    stocks_created = 0
    for i in range(0, simulation.ticker.nb_companies):
        symbol = 2*chr(i+char_shift)
        stock = Stock(simulation=simulation, symbol=symbol, name='Company %s' % symbol, quantity=10000)
        stock.save()
        stocks_created += 1
    return stocks_created


def process_opening_transactions(simulation):
    # deposit cash
    cash_deposit = Transaction(simulation=simulation, transaction_type=Transaction.INITIAL)
    cash_deposit.save()
    for team in simulation.teams.all():
        if team.team_type == Team.PLAYERS:
            amount = simulation.capital
        elif team.team_type == Team.LIQUIDITY_MANAGER:
            amount = 10000*simulation.capital
        else:
            amount = 0
        deposit = TransactionLine(transaction=cash_deposit, team=team, quantity=1, price=amount,
                                  amount=amount, asset_type=TransactionLine.CASH)
        deposit.save()
    # deposit stocks
    # TODO: Calculate opening price!
    for stock in simulation.stocks.all():
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
            deposit = TransactionLine(transaction=stocks_deposit, team=team, quantity=quantity, price=0, stock=stock,
                                      amount=0, asset_type=TransactionLine.STOCKS)
            deposit.save()
    return True