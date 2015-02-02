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
import random
import uuid
import decimal

# Core Django imports
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache
from django.db.models import Sum
from django.db import connection
from django.utils import timezone


# Third-party app imports
from django_extensions.db.models import TimeStampedModel
from shorturls import baseconv

# MarMix imports
from customers.models import Customer
from users.models import User


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


def short_code_encode(sim_id, cust_code):
    encoded_id = baseconv.base32.from_decimal(sim_id)
    return "%s-%s" % (cust_code.upper(), encoded_id)


def generate_uuid(length):
    # TODO: Add a test of unicity in the DB...
    return str(uuid.uuid4().hex.upper()[0:length])


def current_sim_day(simulation_id):
    cached = cache.get('sim-day-%s' % simulation_id)
    if not cached:
        try:
            current_day = SimDay.objects.filter(simulation_id=simulation_id)[0]
        except IndexError:
            current_day = None
        if current_day:
            cached = {'sim_round': current_day.sim_round, 'sim_day': current_day.sim_day, 'timestamp': current_day.timestamp}
        else:
            cached = {'sim_round': 0, 'sim_day': 0, 'timestamp': timezone.now()}
        cache.set('sim-day-%s' % simulation_id, cached)
    return cached


def current_holdings(team_id, simulation_id):
    from stocks.models import TransactionLine
    cursor = connection.cursor()
    cursor.execute('SELECT SUM(CASE WHEN tl.asset_type=%s THEN s.price*tl.quantity ELSE tl.amount END) as balance '
                   'FROM stocks_transactionline tl '
                   'LEFT JOIN stocks_stock s ON tl.stock_id=s.id '
                   'LEFT JOIN stocks_transaction st ON tl.transaction_id=st.id '
                   'WHERE tl.team_id=%s AND st.simulation_id=%s', [TransactionLine.STOCKS, team_id, simulation_id])
    row = cursor.fetchone()
    try:
        return row[0]
    except IndexError:
        return None


def rank_list(simulation_id):
    from stocks.models import TransactionLine
    cursor = connection.cursor()
    cursor.execute('SELECT tl.team_id, t.name, SUM(CASE WHEN tl.asset_type=%s THEN s.price*tl.quantity ELSE tl.amount END) '
                   'as balance FROM stocks_transactionline tl LEFT JOIN stocks_stock s ON tl.stock_id=s.id '
                   'LEFT JOIN simulations_team t ON t.id=tl.team_id L'
                   'EFT JOIN simulations_team_simulations si ON si.team_id=tl.team_id '
                   'WHERE t.team_type=%s AND si.simulation_id=%s '
                   'GROUP BY tl.team_id, t.name '
                   'ORDER BY balance DESC', [TransactionLine.STOCKS, Team.PLAYERS, simulation_id])
    rank_list = dictfetchall(cursor)
    return rank_list


def stocks_list(simulation_id):
    # TODO: Set right timestamp for intra-day values
    cursor = connection.cursor()
    cursor.execute('SELECT s.symbol, s.price, s1.min AS min_day, s1.max AS max_day, s2.min AS min_life, s2.max AS max_life FROM stocks_stock s '
                   'LEFT JOIN (SELECT stock_id, MIN(price) AS min, MAX(price) AS max FROM stocks_quote '
                   'WHERE timestamp>%s AND timestamp<%s GROUP BY stock_id) s1 '
                   'ON s.id=s1.stock_id '
                   'LEFT JOIN (SELECT stock_id, MIN(price) AS min, MAX(price) AS max FROM stocks_quote '
                   'GROUP BY stock_id) s2 '
                   'ON s.id=s2.stock_id '
                   'WHERE s.simulation_id=%s ORDER BY s.symbol', ['2015-01-31', '2015-02-01', simulation_id])
    stocks_list = dictfetchall(cursor)
    return stocks_list


class Simulation(TimeStampedModel):
    """
    A simulation hold all configuration parameters used to setup and run a simulation.
    """
    INTRO = 'IN'
    ADVANCED = 'AD'
    LIVE = 'LI'
    INDEXED = 'ID'
    SIMULATION_TYPE_CHOICES = (
        (INTRO, _('Introduction')),
        (ADVANCED, _('Advanced')),
        (LIVE, _('Live simulation')),
        (INDEXED, _('Indexed simulation')),
    )

    CONFIGURING = 0
    INITIALIZING = 1
    READY = 2
    RUNNING = 3
    PAUSED = 4
    FINISHED = 5
    ARCHIVED = 9
    SIMULATION_STATE_CHOICES = (
        (CONFIGURING, _('Configuring')),
        (INITIALIZING, _('Initializing')),
        (READY, _('Ready to play')),
        (RUNNING, _('Running')),
        (PAUSED, _('Paused')),
        (FINISHED, _('Finished')),
        (ARCHIVED, _('Archived (closed)')),
    )
    SIMULATION_STATE_DICT = {
        'CONFIGURING': CONFIGURING,
        'INITIALIZING': INITIALIZING,
        'READY': READY,
        'RUNNING': RUNNING,
        'PAUSED': PAUSED,
        'FINISHED': FINISHED,
        'ARCHIVED': ARCHIVED,
        }
    code = models.CharField(verbose_name=_("code"), max_length=15, unique=True, blank=True,
                            help_text=_("The code of the simulation (for the user interface)"))
    customer = models.ForeignKey(Customer, verbose_name=_('customer'), related_name=_('simulations'),
                                 help_text=_("The customer account running this simulation"))
    user = models.ForeignKey(User, verbose_name=_('user'), related_name=_('simulations'),
                             help_text=_("The user account running this simulation"))
    simulation_type = models.CharField(verbose_name=_("type of simulation"), max_length=2,
                                       choices=SIMULATION_TYPE_CHOICES, default=INTRO,
                                       help_text=_("The type of this simulation"))
    capital = models.DecimalField(verbose_name=_("initial capital"), max_digits=14, decimal_places=4,
                                  default='0.0000', help_text=_("Initial capital paid to each team"))
    currency = models.ForeignKey('Currency', verbose_name=_("currency"),
                                 help_text=_("The currency symbol displayed in the interface (has no impact on the simulation)"))
    state = models.IntegerField(verbose_name=_("state of the simulation"),
                                choices=SIMULATION_STATE_CHOICES, default=CONFIGURING,
                                help_text=_("The current state of this simulation"))

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = 'MM-99999999'
            super(Simulation, self).save(*args, **kwargs)
            self.code = short_code_encode(self.id, self.customer.short_code)
        if self.id:
            cache.delete('simulation-%s' % self.id)
        super(Simulation, self).save(*args, **kwargs)

    def _nb_teams(self):
        teams = self.teams.all().count()
        return teams
    nb_teams = property(_nb_teams)

    def _get_rank_list(self):
        return rank_list(self.id)
    get_rank_list = property(_get_rank_list)

    def _get_stocks_list(self):
        return stocks_list(self.id)
    get_stocks_list = property(_get_stocks_list)

    def _get_sim_day(self):
        return current_sim_day(self.id)
    get_sim_day = property(_get_sim_day)

    class Meta:
        verbose_name = _("simulation")
        verbose_name_plural = _("simulations")
        ordering = ['code']

    def __str__(self):
        return self.code


class Currency(models.Model):
    """
    A currency, used for display purpose in each views. It has no incidence on the core of the simulation.
    """
    code = models.CharField(verbose_name=_("code of currency"), max_length=3,
                            help_text=_("The ISO code of the currency"))
    symbol = models.CharField(verbose_name=_("symbol of currency"), max_length=3, blank=True, null=True,
                              help_text=_("The symbol of the currency"))

    class Meta:
        verbose_name = _("currency")
        verbose_name_plural = _("currencies")
        ordering = ['code']

    def __str__(self):
        if self.symbol:
            return self.symbol
        else:
            return self.code


class Team(TimeStampedModel):
    """
    A team participating in a simulation.
    """
    PLAYERS = 'P'
    LIQUIDITY_MANAGER = 'L'
    TEAM_TYPE_CHOICES = (
        (PLAYERS, _('Players')),
        (LIQUIDITY_MANAGER, _('Liquidity manager')),
    )

    customer = models.ForeignKey(Customer, verbose_name=_('organization'), related_name=_('teams'),
                                 help_text=_("The organization the team belongs to"))
    simulations = models.ManyToManyField('Simulation', verbose_name=_('simulations'), related_name=_('teams'), null=True,
                                         blank=True, help_text=_("The simulation(s) the team belongs to"))
    name = models.CharField(verbose_name=_("name"), max_length=50,
                            help_text=_("A name that can be attributed to the team"))
    team_type = models.CharField(verbose_name=_("type of team"), max_length=10, choices=TEAM_TYPE_CHOICES,
                                 default=PLAYERS,
                                 help_text=_("Indicates if it is a team of players or a liquidity manager"))
    locked = models.BooleanField(verbose_name=_("locked"), default=False,
                                 help_text=_("Locked teams can not log in the simulation"))
    users = models.ManyToManyField(User, verbose_name=_('members'), related_name=_('teams'), null=True, blank=True,
                                   help_text=_("The users belonging to the team"))
    uuid = models.CharField(verbose_name=_("registration key"), max_length=8, blank=True, null=True, unique=True,
                            help_text=_("A unique registration key that is automatically created"))
    current_simulation = models.ForeignKey('Simulation', verbose_name=_('current simulation'),
                                           related_name=_('current_teams'), null=True, blank=True,
                                           help_text=_("The current simulation the team belongs to"))

    def _get_holdings(self):
        return current_holdings(self.id, self.current_simulation_id)
    get_holdings = property(_get_holdings)

    def _get_members(self):
        return self.users.all().count()
    get_members = property(_get_members)

    def _get_stocks_list(self):
        from stocks.models import TransactionLine
        stocks_list = {'stocks': [], 'cash': [], 'balance': {'market_value': 0, 'purchase_value': 0, 'gain': 0, 'gain_p': 0}}
        tl = TransactionLine.objects.filter(team=self).values('stock__symbol', 'stock__price', 'asset_type', 'stock__id').annotate(
            quantity=Sum('quantity'), amount=Sum('amount')).order_by('stock__symbol')
        for stock in tl:
            asset = dict(TransactionLine.ASSET_TYPE_CHOICES).get(stock['asset_type'])
            if stock['asset_type'] == TransactionLine.STOCKS:
                price = stock['stock__price']
                value = stock['quantity']*price
                gain = value-stock['amount']
                try:
                    gain_p = (value/stock['amount']-1)*100
                except:
                    gain_p = 0

                stocks_list['stocks'].append({'symbol': stock['stock__symbol'], 'asset_type': stock['asset_type'],
                                             'quantity': stock['quantity'], 'amount': stock['amount'], 'asset': asset,
                                             'gain': gain, 'gain_p': gain_p, 'value': value,
                                             'price': price, 'stock': stock['stock__id']})
                stocks_list['balance']['market_value'] += value
                stocks_list['balance']['purchase_value'] += stock['amount']
            else:
                stocks_list['cash'].append({'asset_type': stock['asset_type'], 'quantity': stock['quantity'],
                                            'amount': stock['amount'], 'asset': asset, 'value': stock['amount']})
                stocks_list['balance']['market_value'] += stock['amount']
                stocks_list['balance']['purchase_value'] += stock['amount']
        stocks_list['balance']['gain'] = stocks_list['balance']['market_value'] - stocks_list['balance']['purchase_value']
        try:
            stocks_list['balance']['gain_p'] = (stocks_list['balance']['market_value']/stocks_list['balance']['purchase_value']-1)*100
        except:
            stocks_list['balance']['gain_p'] = 0
        return stocks_list
    get_stocks_list = property(_get_stocks_list)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.uuid is None:
            self.uuid = generate_uuid(8)
        models.Model.save(self, force_insert, force_update, using, update_fields)

    class Meta:
        verbose_name = _('team')
        verbose_name_plural = _('teams')
        unique_together = ('customer', 'name')
        ordering = ['customer', 'name']

    def __str__(self):
        return self.name


class SimDay(models.Model):
    """
    A simulation day matched to a real-time timestamp.
    """
    simulation = models.ForeignKey(Simulation, verbose_name=_('simulation'), related_name=_('sim_days'),
                                   help_text=_("The simulation the sim day belongs to"))
    sim_round = models.IntegerField(verbose_name=_("round"), default=0, help_text=_("Current round"))
    sim_day = models.IntegerField(verbose_name=_("day"), default=0, help_text=_("Current day"))
    timestamp = models.DateTimeField(verbose_name=_("timestamp"), auto_now_add=True,
                                     help_text=_("Timestamp of the tick"))

    class Meta:
        verbose_name = _("simulation day")
        verbose_name_plural = _("simulations days")
        ordering = ['-sim_round', '-sim_day']

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        models.Model.save(self, force_insert, force_update, using, update_fields)
        cached = {'sim_round': self.sim_round, 'sim_day': self.sim_day, 'timestamp': self.timestamp}
        cache.set('sim-day-%s' % self.simulation_id, cached)

    def __str__(self):
        return "R%s/D%s" % (self.sim_round, self.sim_day)


def create_liquidity_manager(simulation):
    """
    Create a new team to host the liquidity manager.

    :param simulation: Simulation object in which to add a new team
    :return: Team object created
    """
    trader = Team(customer=simulation.customer, name=_("Liquidity trader %s" % simulation.code),
                  team_type=Team.LIQUIDITY_MANAGER)
    trader.save()
    trader.simulations.add(simulation)
    return trader