# -*- coding: UTF-8 -*-
# functional_tests.py
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
from django.test import LiveServerTestCase

# Third-party app imports
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

# MarMix imports
from stocks.models import Stock


class NewVisitorTest(LiveServerTestCase):
    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.implicitly_wait(3)
        self.first_stock = Stock.objects.create(symbol='AAAA', name='Stock A', quantity=1000, description='This is a <u>good</u> company!')
        self.second_stock = Stock.objects.create(symbol='BBBB', name='Stock B', quantity=9999)

    def tearDown(self):
        self.browser.quit()

    # def test_new_visitor_discover_marmix(self):
    #     # John check out MarMix
    #     self.browser.get(self.live_server_url)
    #
    #     # He notices the page title and header mention MarMix
    #     self.assertIn('MarMix', self.browser.title)

    def test_can_access_stocks_lists_and_details(self):
        # John check out MarMix
        self.browser.get(self.live_server_url)

        # He choose the stocks list
        self.browser.find_element_by_link_text('Stocks').click()

        # She notices the page title and header mention to-do lists
        self.assertIn('Stocks', self.browser.title)

        self.browser.find_element_by_link_text('MarMix').click()
        self.assertIn('MarMix', self.browser.title)

        self.fail('Finish the test!')

        # She is invited to enter a to-do item straight away

        # She types "Buy peacock feathers" into a text box (Edith's hobby
        # is tying fly-fishing lures)

        # When she hits enter, the page updates, and now the page lists
        # "1: Buy peacock feathers" as an item in a to-do list

        # There is still a text box inviting her to add another item. She
        # enters "Use peacock feathers to make a fly" (Edith is very methodical)

        # The page updates again, and now shows both items on her list

        # Edith wonders whether the site will remember her list. Then she sees
        # that the site has generated a unique URL for her -- there is some
        # explanatory text to that effect.

        # She visits that URL - her to-do list is still there.

        # Satisfied, she goes back to sleep