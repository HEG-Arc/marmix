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

# Core Django imports
from django.utils.translation import ugettext as _

# Third-party app imports
from async_messages import messages

# MarMix imports
from config.celery import app
from simulations.models import Simulation, Team, create_liquidity_manager
from tickers.tasks import create_company_simulation, create_company_live, clock_erpsim, create_mssql_simulation
from stocks.models import create_generic_stocks, process_opening_transactions, Stock


@app.task
def initialize_simulation(simulation_id):
    """
    Initialize the simulation (async Celery task).

    -Creates stocks
    -Creates a liquidity manager
    -Initialize the ticker
    -Creates opening transactions

    :param simulation: Simulation object
    :return: None
    """
    simulation = Simulation.objects.get(pk=simulation_id)
    msg_info = ""
    msg_error = ""
    if simulation.teams.count() == 0:
        messages.error(simulation.user, _("You need to select at least one team for the simulation!"))
    else:
        if simulation.simulation_type == Simulation.INTRO or simulation.simulation_type == Simulation.ADVANCED:
            msg_info += _("Initialization of simulation running...") + "<br />"
            # stocks creation
            print("Initialization of simulation running...")
            print("Create generic stocks")
            stocks = create_generic_stocks(simulation.id)
            if stocks > 0:
                msg_info += _("%s stocks were created..." % stocks) + "<br />"
                print("%s stocks created" % stocks)
            else:
                msg_error += _("No stocks were created!") + "<br />"

        elif simulation.simulation_type == Simulation.LIVE or simulation.simulation_type == Simulation.INDEXED:
            if simulation.simulation_type == Simulation.LIVE:
                full_clock = clock_erpsim(simulation.id, full=True)
                ticker = simulation.ticker
                ticker.nb_companies = full_clock['nb_teams']
                ticker.nb_rounds = full_clock['max_rounds']
                ticker.nb_days = full_clock['max_days']
                ticker.save()
                create_generic_stocks(simulation.id)
            else:
                game = create_mssql_simulation(simulation.id)
                ticker = simulation.ticker
                ticker.nb_companies = game['nb_teams']
                ticker.nb_rounds = game['max_rounds']
                ticker.nb_days = game['max_days']
                ticker.save()
                create_generic_stocks(simulation_id, symbols=game['list_of_teams'])

        if simulation.simulation_type in (Simulation.INTRO, Simulation.ADVANCED, Simulation.LIVE, Simulation.INDEXED):
            liquidity_manager = create_liquidity_manager(simulation.id)
            if liquidity_manager:
                msg_info += _("%s was created..." % liquidity_manager.name) + "<br />"
            else:
                msg_error += _("No liquidity manager was created!") + "<br />"

            # initialize ticker
            if simulation.simulation_type == Simulation.INTRO or simulation.simulation_type == Simulation.ADVANCED:
                for stock in simulation.stocks.all():
                    create_company_simulation(simulation.id, stock.id)

            elif simulation.simulation_type == Simulation.LIVE or simulation.simulation_type == Simulation.INDEXED:
                for stock in simulation.stocks.all():
                    create_company_live(simulation.id, stock.id)

            # opening transactions (gives cash and stock to each team)
            print("Process openings...............")
            process_opening_transactions(simulation.id)

            if msg_info != "":
                msg_info += _("Initialization succeeded! You can start running the simulation.")
                messages.info(simulation.user, msg_info)
            if msg_error != "":
                msg_error += _("There were errors during the initialization process!")
                messages.error(simulation.user, msg_error)

        else:
            messages.error(simulation.user, _("Initialization of simulation failed!"))
