# -*- coding: utf-8 -*-
"""
	Copyright (c) 2025 - 2026 TNO-ESI
	All rights reserved.
"""
from nicegui import ui, run

from mbdlyb.functional.gdb import GCluster
from mbdlyb.messages import ValidationMessage
from mbdlyb_ui import Button
from mbdlyb_ui.helpers import get_object_or_404, goto, get_url
from mbdlyb_ui.utils import Status, status

from .base import FunctionalPage


class UIValidatorData:
	"""Hold the validator analysis and UI state."""

	cluster: GCluster

	messages: list[ValidationMessage]

	def __init__(self, cluster: GCluster):
		"""Initialize ui validator data state for the selected cluster.

		Args:
		    cluster: Cluster whose validation messages are managed.
		"""
		self.cluster = cluster
		self.messages = []

	def reset(self):
		"""Clear previously reported validation messages."""
		self.messages = []

	async def validate(self):
		"""Run model validation and store the reported results."""
		status.refresh(Status.COMPUTING)
		self.reset()
		self.cluster.refresh()
		show_validation_results.refresh([], False)
		self.messages = sorted(await run.io_bound(self.cluster.validate))
		show_validation_results.refresh(self.messages)
		status.refresh(Status.READY)


class ValidatorPage(FunctionalPage):
	"""Display the validator editing page."""

	cluster: GCluster
	data: UIValidatorData

	def __init__(self, cluster_id: str):
		"""Load the validator and configure its available actions.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		self.cluster = get_object_or_404(GCluster, uid=cluster_id)
		self.data = UIValidatorData(self.cluster)
		super().__init__(f'Validator for {self.cluster}', self.cluster, [
			Button('Validate', 'refresh', 'primary', self.data.validate),
			Button('Close', 'arrow_back', 'secondary', lambda: goto(self.cluster))
		], status=Status.READY, force_hide_nav=True)

	def _show_content(self):
		"""Show validation results and trigger the initial validation."""
		show_validation_results(self.data.messages, False)

		self.data.reset()
		self._ui_buttons[0].run_method('click')

@ui.refreshable
def show_validation_results(messages: list[ValidationMessage], validated: bool = True):
	"""Render the model validation results.

	Args:
	    messages: Validation messages to display.
	    validated: Whether the model has completed validation.
	"""
	if messages:
		highest_prio = 9
		text_class = None
		for m in messages:
			if m.priority < highest_prio:
				highest_prio = m.priority
				text_class = m.color
		ui.label(f'{len(messages)} validation rule{"s were" if len(messages) > 1 else " was"} violated:').classes(
			f'text-{text_class}')
		with ui.grid(columns=2).classes('gap-0'):
			for message in messages:
				if message.has_object_to_fix:
					ui.link(message.fix_label, get_url(message.object_to_fix), True).classes(f'text-{message.color} border p-1')

				else:
					ui.label('').classes('border p-1')
				ui.label(message.message).classes(f'text-{message.color}').classes('border p-1')
	elif validated:
		ui.label('No issues were found.').classes('text-positive')
