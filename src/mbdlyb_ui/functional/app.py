# -*- coding: utf-8 -*-
"""
	Copyright (c) 2026 TNO-ESI
	All rights reserved.
"""
from mbdlyb_ui.app import App
from nicegui import ui

from mbdlyb.functional.gdb import GCluster
from .config import URL_RESOLVER
from .base import LandingPage
from .router import (cluster_router, function_router, hardware_router, observable_router, diagnostic_test_router,
					 operating_mode_router, diagnostic_test_result_router)


class FunctionalDiagnosticsApp(App):
	"""Configure the functional diagnostics application and its routes."""

	URL_RESOLVER = URL_RESOLVER
	MODES = ['Editor', 'Tree']
	MENU_CLASS = GCluster
	DEFAULT_SETTINGS = {
		**App.DEFAULT_SETTINGS,
		'mode': MODES[1],
		'show_diagrams': True,
		'auto_compute': False,
		'reasoner': 'BayesNetReasoner'
	}

	def __init__(self):
		"""Register functional model routes and configure the application."""
		super().__init__('Model Editor', [
			cluster_router, function_router, hardware_router, observable_router, diagnostic_test_router,
			operating_mode_router, diagnostic_test_result_router
		])


@ui.page('/')
def landing_page():
	"""Display the cluster landing page."""
	LandingPage().show()


def main():
	"""Start the functional diagnostics application."""
	FunctionalDiagnosticsApp().run()
