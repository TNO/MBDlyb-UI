# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
from typing import Optional

from nicegui import ui

from mbdlyb.gdb import cls
from mbdlyb.functional.gdb import GCluster, GOperatingMode
from mbdlyb_ui import Button
from mbdlyb_ui.dialogs import confirm_delete
from mbdlyb_ui.helpers import get_object_or_404, goto, save_object, get_url

from .base import FunctionalPage
from .helpers import save_new_object
from .validation import base_name_validation


class FormOperatingMode:
	"""Represent an editable operating mode."""

	name: str
	old_name: str
	added: bool
	dropped: bool

	def __init__(self, name: str, new=False):
		"""Initialize form operating mode with its editable state.

		Args:
		    name: Name of this entry.
		    new: Whether this operating mode was newly added.
		"""
		self.name = name
		self.old_name = name
		self.added = new
		self.dropped = False

	def __eq__(self, other):
		"""Compare this editable value with another value or name.

		Args:
		    other: Value to compare with this object.

		Returns:
		    Whether the compared values match.
		"""
		if isinstance(other, FormOperatingMode):
			return self.name == other.name
		return False

	def drop(self):
		"""Remove this operating mode from its parent list."""
		self.dropped = True

	@staticmethod
	def from_list(l: list[str]) -> list['FormOperatingMode']:
		"""Create editable operating modes from stored names.

		Args:
		    l: Stored state or operating mode names to turn into entries.

		Returns:
		    Editable collection initialized from the stored values.
		"""
		return [FormOperatingMode(i) for i in l]

	@staticmethod
	def to_list(l: list['FormOperatingMode']) -> list[str]:
		"""List the names of operating modes not marked for removal.

		Args:
		    l: Editable operating modes, including entries marked for removal.

		Returns:
		    Stored values represented by the editable entries.
		"""
		return [i.name for i in l if i.dropped == False]

	@staticmethod
	def updates_list(l: list['FormOperatingMode']) -> dict[str,Optional[str]]:
		"""Collect renames and removals of existing operating modes.

		Args:
		    l: Editable operating modes to inspect for renames and removals.

		Returns:
		    Mapping of old operating mode names to new names or removal markers.
		"""
		updates = {}
		for opm in l:
			if opm.added:
				continue
			elif opm.dropped:
				updates[opm.old_name] = None
			elif opm.name != opm.old_name:
				updates[opm.old_name] = opm.name
		return updates


def add_opm(form_operating_modes: list[FormOperatingMode]):
	"""Append an operating mode and refresh the list.

	Args:
	    form_operating_modes: Editable operating mode entries.
	"""
	operating_modes = FormOperatingMode.to_list(form_operating_modes)
	name = 'OperatingMode_'
	for i in range(1, 100):
		if name + str(i) not in operating_modes:
			form_operating_modes.append(FormOperatingMode(name + str(i), new=True))
			break
	operating_mode_list.refresh()


def drop_opm(opm: FormOperatingMode):
	"""Remove an operating mode and refresh the list.

	Args:
	    opm: Operating mode selected for editing.
	"""
	opm.drop()
	operating_mode_list.refresh()


def move_opm(operating_modes: list[FormOperatingMode], opm: FormOperatingMode, direction: int):
	"""Change the position of an operating mode in the list.

	Args:
	    operating_modes: Editable list of operating mode entries.
	    opm: Operating mode selected for editing.
	    direction: Direction in which to move the item.
	"""
	index = operating_modes.index(opm)
	operating_modes.remove(opm)
	operating_modes.insert(index + direction, opm)
	operating_mode_list.refresh()


@ui.refreshable
def operating_mode_list(operating_modes: list[FormOperatingMode]):
	"""Render the operating mode list and its editing actions.

	Args:
	    operating_modes: Editable list of operating mode entries.
	"""
	with ui.grid(columns='auto 15px 15px').classes('vertical-top gap-x-0'):
		for col in ('Operating modes',):
			ui.label(col).classes('font-bold w-64')
		ui.icon('add', color='primary').on('click', lambda: add_opm(operating_modes)).classes('cursor-pointer')
		ui.space()
		operating_modes_active = [opm for opm in operating_modes if opm.dropped == False]
		opm_inputs = []
		for i, opm in enumerate(operating_modes_active):
			opm_inputs.append(ui.input('Name', validation=base_name_validation()).bind_value(opm, 'name').classes('w-64').props('hide-bottom-space'))
			ui.icon('delete', color='negative').on('click', lambda f=opm: drop_opm(f)).classes('self-center pt-3 cursor-pointer')
			with ui.column().classes('self-center pt-2 gap-x-0 gap-y-0'):
				if i > 0:
					ui.icon('arrow_upward').classes('cursor-pointer').on('click', lambda f=opm: move_opm(operating_modes, f, -1))
				else:
					ui.icon('arrow_upward').classes('opacity-25')
				if i < len(operating_modes_active) - 1:
					ui.icon('arrow_downward').classes('cursor-pointer').on('click', lambda f=opm: move_opm(operating_modes, f, 1))
				else:
					ui.icon('arrow_downward').classes('opacity-25')
	for input in opm_inputs:
		input.validation['Operating modes must be unique'] = \
			lambda s: sum([i.value == s for i in opm_inputs]) == 1
		for i in opm_inputs:
			if i is not input:
				input.on_value_change(i.validate)


def opm_form(opm: GOperatingMode, operating_modes: list[FormOperatingMode], cluster: GCluster, update: bool = True):
	"""Render the operating mode editing controls.

	Args:
	    opm: Operating mode node whose name is edited.
	    operating_modes: Editable list of operating mode entries.
	    cluster: Parent cluster used to validate the operating mode name.
	    update: Whether the operating mode already exists for name validation.
	"""
	ui.input('Name', validation=base_name_validation(cluster, opm if update else None)).bind_value(opm, 'name').classes('w-64 pb-6').props('hide-bottom-space')
	operating_mode_list(operating_modes)


class OpmUpdatePage(FunctionalPage):
	"""Display the operating mode update editing page."""

	update: bool
	operating_mode: GOperatingMode
	cluster: GCluster
	operating_modes: list[FormOperatingMode]

	def __init__(self, opm_id: str = None, cluster_id: str = None):
		"""Load the opm and configure its editing actions.

		Args:
		    opm_id: Identifier of the operating mode to load.
		    cluster_id: Identifier of the cluster to load.
		"""
		if opm_id:
			self.update = True
			self.operating_mode = get_object_or_404(GOperatingMode, uid=opm_id)
			self.operating_modes = FormOperatingMode.from_list(self.operating_mode.operating_modes)
			self.cluster = self.operating_mode.get_net()
			title = f'Update {self.operating_mode}'
		else:
			self.update = False
			self.cluster = get_object_or_404(GCluster, uid=cluster_id)
			self.operating_mode = cls(GOperatingMode)(name='', operating_modes=[])
			self.operating_modes = FormOperatingMode.from_list(['OperatingMode_1', 'OperatingMode_2'])
			title = f'New operating mode in {self.cluster.name}'
		super().__init__(title, self.cluster, [
			Button('Discard', None, 'warning', lambda: goto(self.cluster)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable opm update fields and available actions."""
		ui.input('Name', validation=base_name_validation(self.cluster,
														 self.operating_mode if self.update else None)).bind_value(
			self.operating_mode, 'name').classes('w-64 pb-6').props('hide-bottom-space')
		operating_mode_list(self.operating_modes)

	def _save(self):
		"""Save the opm update changes to the model."""
		self.operating_mode.operating_modes = FormOperatingMode.to_list(self.operating_modes)
		if self.update:
			updates = FormOperatingMode.updates_list(self.operating_modes)
			GOperatingMode.update_relations_with_operating_mode(updates)
			save_object(self.operating_mode)
			operating_modes = [opm for opm in self.operating_modes if opm.dropped == False]
			for opm in operating_modes:
				opm.old_name = opm.name
				opm.added = False
			goto(self.cluster)
		else:
			save_new_object(self.operating_mode, self.cluster)


class OpmDetailsPage(FunctionalPage):
	"""Display the operating mode details properties and relations."""

	operating_mode: GOperatingMode

	def __init__(self, opm_id: str):
		"""Load the opm details and configure its available actions.

		Args:
		    opm_id: Identifier of the operating mode to load.
		"""
		self.operating_mode = get_object_or_404(GOperatingMode, uid=opm_id)
		super().__init__(f'Operating mode {self.operating_mode.name}', self.operating_mode, [
			Button(None, 'edit', None, lambda: goto(f'{get_url(self.operating_mode)}/update'), 'Edit operating mode'),
			Button(None, 'delete', 'negative',
				   lambda: confirm_delete(self.operating_mode, self.operating_mode.get_net()), 'Delete operating mode')
		])

	def _show_content(self):
		"""Display opm details properties, relations, and navigation actions."""
		with ui.list().props('dense separator'):
			ui.separator()
			ui.item_label('Operating modes').props('header').classes('text-bold')
			ui.separator()
			for m in self.operating_mode.operating_modes:
				ui.item(m)
			ui.separator()
