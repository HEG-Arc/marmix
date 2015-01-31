MarMix documentation
====================

.. image:: /medias/marmix_200.png
   :width: 200 px
   :alt: MarMix logo

**MarMix** is a serious game for higher education based on a stock market simulation. Various game designs are built in the
simulation in order to stepwise increase the difficulty of the game. The most advanced scenarios are developed to be
run in parallel of an `ERPsim <http://erpsim.hec.ca/>`_ simulation.

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

Contents
--------

.. toctree::
   :maxdepth: 2

   install
   deploy
   applications
   tests
   database


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`