# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
import enum

from nicegui import ui


class Status(enum.Enum):
	"""Represent the ready, computing, and error states of an operation."""

	READY = enum.auto()
	COMPUTING = enum.auto()
	ERROR = enum.auto()

	def print_ui(self):
		"""Render the icon or spinner corresponding to this status."""
		if self == Status.READY:
			ui.icon('check', color='positive', size='lg').tooltip('Ready')
		elif self == Status.COMPUTING:
			ui.spinner(color='primary', size='lg').tooltip('Computing')
		else:
			ui.icon('error', color='warning', size='lg').tooltip('Error')


@ui.refreshable
def show_name(name: str):
	"""Render a refreshable heading for an element name.

	Args:
		name: Name to display.
	"""
	ui.label(name).classes('text-h6')


@ui.refreshable
def status(status: Status):
	"""Render a refreshable indicator for a status.

	Args:
		status: State whose icon or spinner should be displayed.
	"""
	status.print_ui()
