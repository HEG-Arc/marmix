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
from tickers.tasks import create_company_simulation
from stocks.models import create_generic_stocks, process_opening_transactions, Stock


@app.task
def initialize_simulation(simulation):
    """
    Initialize the simulation (async Celery task).

    -Creates stocks
    -Creates a liquidity manager
    -Initialize the ticker
    -Creates opening transactions

    :param simulation: Simulation object
    :return: None
    """
    msg_info = ""
    msg_error = ""
    if simulation.simulation_type == Simulation.INTRO:
        msg_info += _("Initialization of introductory simulation running...") + "<br />"
        # stocks creation
        stocks = create_generic_stocks(simulation)
        if stocks > 0:
            msg_info += _("%s stocks were created..." % stocks) + "<br />"
        else:
            msg_error += _("No stocks were created!") + "<br />"
        # liquidity traders creation
        liquidity_manager = create_liquidity_manager(simulation)
        if liquidity_manager:
            msg_info += _("%s was created..." % liquidity_manager.name) + "<br />"
        else:
            msg_error += _("No liquidity manager was created!") + "<br />"
        # initialize ticker
        for stock in simulation.stocks.all():
            create_company_simulation.apply_async([simulation.id, stock.id])
        # opening transactions
        openings = process_opening_transactions(simulation)
        if openings:
            msg_info += _("Openings transactions were processed...") + "<br />"
        else:
            msg_error += _("Unable to process opening transactions!") + "<br />"
        if msg_info != "":
            msg_info += _("Initialization succeeded! You can start running the simulation.")
            messages.info(simulation.user, msg_info)
        if msg_error != "":
            msg_error += _("There were errors during the initialization process!")
            messages.error(simulation.user, msg_error)
    elif simulation.simulation_type == Simulation.ADVANCED:
        messages.info(simulation.user, _("Initialization of advanced simulation running..."))
    elif simulation.simulation_type == Simulation.LIVE or simulation.simulation_type == Simulation.INDEXED:
        messages.warning(simulation.user, _("Initialization of live or indexed simulations is not yet implemented! Sorry."))
    else:
        messages.error(simulation.user, _("Initialization of simulation failed!"))