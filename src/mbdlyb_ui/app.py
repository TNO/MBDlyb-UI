# -*- coding: utf-8 -*-
"""
	Copyright (c) 2026 TNO-ESI
	All rights reserved.
"""
import logging
from argparse import ArgumentParser, Namespace
from typing import Any, Union, Callable, Optional

from nicegui import ui, app, APIRouter

from mbdlyb.gdb import GMBDIdentifiable, GMBDElement, GMBDNet, set_config


MBDLYB_MODES: list[str] = []
MBDLYB_MENU_CLASS: type[GMBDNet] = GMBDNet
MBDLYB_URL_RESOLVER: dict[Union[type[GMBDIdentifiable], str], Union[str, Callable[[GMBDIdentifiable], str]]] = {}


class App:
	"""Configure database access, routing, and shared UI settings for a NiceGUI app."""

	MODES = ['Editor']
	DEFAULT_SETTINGS: dict[str, Any] = {
		'mode': MODES[0]
	}
	URL_RESOLVER: dict[Union[type[GMBDIdentifiable], str], Union[str, Callable[[GMBDIdentifiable], str]]] = dict()
	MENU_CLASS: type[GMBDNet]

	name: str
	routers: list[APIRouter]
	_args: Namespace
	_argparser: ArgumentParser

	def __init__(self, name: str, routers: Optional[list[APIRouter]] = None):
		"""Prepare an app with its display name and optional initial routers.

		Args:
			name: Title used when starting the UI.
			routers: Routers to register with NiceGUI immediately.
		"""
		self.name = name
		self.routers = []
		if routers:
			self.add_router(*routers)
		self._argparser = ArgumentParser()

	def run(self):
		"""Initialize configuration and start the NiceGUI server."""
		self._init()
		ui.run(title=self.name, show=False, reload=False, reconnect_timeout=600)

	def add_router(self, *routers: APIRouter):
		"""Register routers with both this app and NiceGUI.

		Args:
			*routers: Routers containing pages served by this app.
		"""
		for router in routers:
			self.routers.append(router)
			app.include_router(router)

	def _init(self):
		"""Parse database options and publish app-wide UI configuration."""
		logging.basicConfig(format='%(asctime)s Level %(levelno)s %(pathname)s: %(message)s', level="ERROR")
		self._add_arguments()
		self._args = self._argparser.parse_args()
		set_config(self._args.protocol, self._args.username, self._args.password, self._args.host, self._args.port,
				   self._args.database)
		self._load_settings()
		self._set_globals()

	def _add_arguments(self):
		"""Add Neo4j connection options to the command-line parser."""
		self._argparser.add_argument('--host', help='Hostname of your neo4j database.', required=False,
									 default='localhost')
		self._argparser.add_argument('--port', help='Port on which your neo4j database listens.', required=False,
									 default=7687, type=int)
		self._argparser.add_argument('--protocol', help='Protocol to use to connect to neo4j database.', required=False,
									 default='bolt')
		self._argparser.add_argument('--username', help='Username for neo4j authentication.', required=False,
									 default='neo4j')
		self._argparser.add_argument('--password', help='Password for neo4j authentication.', required=False,
									 default='password')
		self._argparser.add_argument('--database', help='Name of the neo4j database to use.', required=False,
									 default=None)

	def _load_settings(self):
		"""Populate missing persistent settings with this app's defaults."""
		for setting, default in self.DEFAULT_SETTINGS.items():
			app.storage.general[setting] = app.storage.general.get(setting, default)

	def _set_globals(self):
		"""Expose modes, menu class, and URL resolvers to UI helpers."""
		global MBDLYB_URL_RESOLVER, MBDLYB_MODES, MBDLYB_MENU_CLASS
		MBDLYB_MODES = self.MODES
		MBDLYB_MENU_CLASS = self.MENU_CLASS
		for clazz, url in self.URL_RESOLVER.items():
			MBDLYB_URL_RESOLVER[clazz] = url
			MBDLYB_URL_RESOLVER[clazz.__name__] = url


# TODO: Could this method be removed?
def config_mapper(mappers: list[dict], mappings: list[tuple[type[GMBDElement], type[GMBDElement]]]):
	"""Copy target-class entries to corresponding source-class keys.

	Args:
		mappers: Mutable mapping dictionaries to update in place.
		mappings: Pairs of source and target element classes.
	"""
	for mapping_from, mapping_to in mappings:
		for mapping in mappers:
			if mapping_to in mapping:
				mapping[mapping_from] = mapping[mapping_to]
