MarMix
======

**MarMix** is a serious game for higher education based on a stock market simulation. Various game designs are built in the
simulation in order to stepwise increase the difficulty of the game. The most advanced scenarios are developed to be
run in parallel of an `ERPsim <http://erpsim.hec.ca/>`_ simulation.


.. image:: https://travis-ci.org/HEG-Arc/marmix.svg
    :target: https://travis-ci.org/HEG-Arc/marmix
    :alt: Build Status

.. image:: https://coveralls.io/repos/HEG-Arc/marmix/badge.png
    :target: https://coveralls.io/r/HEG-Arc/marmix
    :alt: Coverage Status

.. image:: https://requires.io/github/HEG-Arc/marmix/requirements.svg?branch=master
    :target: https://requires.io/github/HEG-Arc/marmix/requirements/?branch=master
    :alt: Requirements Status

.. image:: https://img.shields.io/badge/licence-GPLv3-brightgreen.svg
    :target: http://www.gnu.org/licenses/gpl-3.0.html
    :alt: GNU General Public License

Game design
-----------

Currently, **MarMix** support 4 game designs:

- Introduction
- Advanced
- Live
- Indexed

Introduction
************

The *introduction game* is designed to introduce the players to the platform. A certain number of companies' profits is
simulated, whose stocks are available on the stock market. Players are asked to place orders (ASK/BID) based on the
variations of the profit. Optional transaction costs or payment of dividends can be added to the game.

Advanced
********

The *advanced game* is the same as the *`introduction`_* one but with more information revealed concerning the variations
of the companies profits. In this games players are asked to develop a strategy based on the information they get from
the market. Optional transaction costs or payment of dividends can be added to the game.

Live
****

The *live game* is specifically designed to be run in parallel of an `ERPsim <http://erpsim.hec.ca/>`_ simulation. The
stock market hosts stocks for all companies active in the `ERPsim <http://erpsim.hec.ca/>`_ simulation. Players are the
asked to place their orders based on their own valuation of the `ERPsim <http://erpsim.hec.ca/>`_ simulation companies.
There are some simple interfaces that are built in **MarMix** in order to ease running each simulation in parallel.
Integration is planned but not yet implemented.

Indexed
*******

The *indexed game* is based on data from historic `ERPsim <http://erpsim.hec.ca/>`_ simulations. This is still under
development.

Documentation
-------------

The **MarMix** documentation is available `online <http://heg-arc.github.io/marmix/>`_ or as a
`PDF document <https://github.com/HEG-Arc/marmix/blob/master/MarMix3-Manual.pdf?raw=true>`_. You can also build the
documentation by yourself from the `docs <https://github.com/HEG-Arc/marmix/tree/master/docs>`_ directory.

Installation
------------

There is currently no installer for **MarMix** but you can install it following these steps:

- Install Python 3 on your system
- Create a virtualenv
- Checkout from GitHub
- Install the requirements: ``$ pip install -r requirements/local.txt``
- Configure your database (Postgresql is recommended)
- Start the server: ``$ manage.py runserver``

You can find more information on the initial setup in the `wiki <https://github.com/HEG-Arc/marmix/wiki/Developper%27s-setup>`_.