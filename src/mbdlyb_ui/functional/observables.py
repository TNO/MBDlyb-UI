# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
from typing import Type, Optional

from nicegui import ui
from neomodel import db
from mbdlyb.gdb import cls
from mbdlyb.functional import DirectObservable
from mbdlyb.functional.gdb import GCluster, GFunction, GHardware, GDirectObservable, GFunctionalNode
from mbdlyb_ui import Button, Table, TableColumn
from mbdlyb_ui.dialogs import confirm, confirm_delete, confirm_delete_relation
from mbdlyb_ui.helpers import goto, get_object_or_404, get_relation_or_404, save_object, get_url

from .base import FunctionalPage, CPTPage
from .helpers import save_new_object, ObservesRelation, StateTable, state_table
from .validation import base_name_validation


def observable_form(observable: GDirectObservable, states: StateTable, cluster: GCluster, update: bool = True):
	"""Render the observable name and state editing controls.

	Args:
	    observable: Observable node whose properties are edited.
	    states: Editable state names for the direct observable.
	    cluster: Parent cluster used to validate the observable name.
	    update: Whether the observable already exists for name validation.
	"""
	ui.input('Name', validation=base_name_validation(cluster, observable if update else None)) \
		.bind_value(observable, 'name').props('hide-bottom-space')
	ui.number('False positive rate', min=0., max=1., step=.001).bind_value(observable, 'fp_rate')
	ui.number('False negative rate', min=0., max=1., step=.001).bind_value(observable, 'fn_rate')
	state_table(states, DirectObservable.DEFAULT_STATES)


class ObservableCreatePage(FunctionalPage):
	"""Display the observable create editing page."""

	observable: GDirectObservable
	states: StateTable

	def __init__(self, cluster_id: str):
		"""Prepare a new observable and configure its editing actions.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		cluster = get_object_or_404(GCluster, uid=cluster_id)
		self.observable = cls(GDirectObservable)(name='')
		self.states = StateTable.from_list(self.observable.states_)
		super().__init__(f'New observable in {cluster.name}', cluster, [
			Button('Discard', None, 'warning', lambda: goto(cluster)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable observable create fields and available actions."""
		observable_form(self.observable, self.states, self.element, False)

	def _save(self):
		"""Save the observable create changes to the model."""
		self.observable.states = self.states.to_list()
		save_new_object(self.observable, self.element)


class ObservableUpdatePage(FunctionalPage):
	"""Display the observable update editing page."""

	observable: GDirectObservable
	states: StateTable

	def __init__(self, observable_id: str):
		"""Load the observable and configure its editing actions.

		Args:
		    observable_id: Identifier of the observable to load.
		"""
		self.observable = get_object_or_404(GDirectObservable, uid=observable_id)
		self.states = StateTable.from_list(self.observable.states_)
		super().__init__(f'Update {self.observable.fqn}', self.observable, [
			Button('Discard', None, 'warning', lambda: goto(self.observable.get_net())),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable observable update fields and available actions."""
		observable_form(self.observable, self.states, self.observable.get_net())

	def _save(self):
		"""Save the observable update changes to the model."""
		self.observable.states = self.states.to_list()
		save_object(self.observable, self.observable.get_net())


class ObservableDetailsPage(FunctionalPage):
	"""Display the observable details properties and relations."""

	observable: GDirectObservable

	def __init__(self, observable_id: str):
		"""Load the observable details and configure its available actions.

		Args:
		    observable_id: Identifier of the observable to load.
		"""
		self.observable = get_object_or_404(GDirectObservable, uid=observable_id)
		cluster = self.observable.get_net()
		buttons = [
			Button(None, 'border_all', 'secondary', lambda: goto(f'{get_url(self.observable)}/cpt'), 'Modify CPT'),
			Button(None, 'edit', None, lambda: goto(f'{get_url(self.observable)}/update'), 'Edit observable'),
			Button(None, 'delete', 'negative', lambda: confirm_delete(self.observable, cluster), 'Delete observable')]
		if not (self.observable.at_root or cluster.at_root):
			buttons = [Button(None, 'move_up', 'secondary', lambda: confirm('Move up observable',
																			f'Are you sure to move {self.observable.name} up to {cluster.get_net().fqn}?',
																			'I am sure', self._move_up),
							  'Move observable up')] + buttons
		super().__init__(f'Observable {self.observable.name}', self.observable, buttons)

	def _show_content(self):
		"""Display observable details properties, relations, and navigation actions."""
		base_url = get_url(self.observable)
		with ui.row():
			ui.label('False positive/negative rate').classes('font-bold')
			ui.label(f'{self.observable.fp_rate} / {self.observable.fn_rate}')
		with ui.grid(columns='1fr 1fr').classes('w-full'):
			with ui.card():
				Table('Observed functions', self.observable.observed_functions.order_by('fqn_'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableColumn('Weight', lambda f: self.observable.observed_functions.relationship(f).weight)
				], self.observable, [
						  Button(icon='add', color='positive', tooltip='Add observed function',
								 handler=f'{base_url}/observes_fn/new')
					  ], [
						  Button(icon='edit', tooltip='Edit observed function',
								 handler=lambda x: goto(f'{base_url}/observes_fn/{x.uid}/update')),
						  Button(icon='delete', color='negative', tooltip='Delete observed function',
								 handler=lambda x: confirm_delete_relation('observed_functions', self.observable, x,
																		   self.observable))
					  ]).show()
			with ui.card():
				Table('Observed hardware', self.observable.observed_hardware.order_by('fqn_'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableColumn('Weight', lambda f: self.observable.observed_hardware.relationship(f).weight)
				], self.observable, [
						  Button(icon='add', color='positive', tooltip='Add observed hardware',
								 handler=f'{base_url}/observes_hw/new')
					  ], [
						  Button(icon='edit', tooltip='Edit observed hardware',
								 handler=lambda x: goto(f'{base_url}/observes_hw/{x.uid}/update')),
						  Button(icon='delete', color='negative', tooltip='Delete observed hardware',
								 handler=lambda x: confirm_delete_relation('observed_hardware', self.observable, x,
																		   self.observable))
					  ]).show()

	def _move_up(self):
		"""Move the selected item earlier in its ordering."""
		self.observable.set_net(self.observable.get_net().get_net())
		goto(self.observable)


# OBSERVES RELATIONS

class ObservesRelationPage(FunctionalPage):
	"""Display the observes relation editing page."""

	observable: GDirectObservable
	observed: GFunctionalNode
	relation: ObservesRelation
	node_type: Type[GFunctionalNode]
	node_type_name: str

	_REL_MAP = {
		GFunction: 'observed_functions',
		GHardware: 'observed_hardware'
	}

	def __init__(self, observable_id: str, node_type: Type[GFunctionalNode], observed_id: Optional[str] = None):
		"""Load the observes relation and configure its available actions.

		Args:
		    observable_id: Identifier of the observable to load.
		    node_type: Model class of the observed node.
		    observed_id: Identifier of the observed node.
		"""
		self.observable = get_object_or_404(GDirectObservable, uid=observable_id)
		self.node_type = node_type
		self.node_type_name = node_type.__label__
		if observed_id:
			self.observed = get_object_or_404(node_type, uid=observed_id)
			relation = get_relation_or_404(self.observable, self.observed, self._REL_MAP[self.node_type])
			self.relation = ObservesRelation(self.observed, self.observable, weight=relation.weight)
		else:
			self.relation = ObservesRelation(end_node=self.observable, start_node_type=self.node_type)
		super().__init__(f'Add observed {self.node_type_name} to {self.observable}', self.observable, [
			Button('Discard', None, 'warning', lambda: goto(self.observable)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable observes relation fields and available actions."""
		options, _ = db.cypher_query(
			f'''MATCH
				(o:DirectObservable {{uid: '{self.relation.end_uid}'}})-[r:PART_OF*]->(:Cluster)<-[:PART_OF]-(x:{self.node_type_name})
			WHERE
				NOT (x)-[:OBSERVED_BY]->(o)
			RETURN x
			ORDER BY size(r), x.fqn''', resolve_objects=True)
		options_dict = dict() if self.relation.start_uid is None else {
			self.relation.start_uid: str(self.relation.get_start_node().fqn)}
		ui.select({**options_dict, **{sf[0].uid: str(sf[0].fqn) for sf in options}}, label=self.node_type_name,
				  with_input=True).bind_value(
			self.relation, 'start_uid')
		ui.number('Weight', min=0., max=1., precision=2, step=.01).bind_value(self.relation, 'weight')

	def _save(self):
		"""Save the observes relation changes to the model."""
		self.relation.save(self.observable)


class ObservesFunctionRelationPage(ObservesRelationPage):
	"""Display the observes function relation editing page."""

	def __init__(self, observable_id: str, function_id: Optional[str] = None):
		"""Load the observes function relation and configure its available actions.

		Args:
		    observable_id: Identifier of the observable to load.
		    function_id: Identifier of the function to load.
		"""
		super().__init__(observable_id, GFunction, function_id)


class ObservesHardwareRelationPage(ObservesRelationPage):
	"""Display the observes hardware relation editing page."""

	def __init__(self, observable_id: str, hardware_id: Optional[str] = None):
		"""Load the observes hardware relation and configure its available actions.

		Args:
		    observable_id: Identifier of the observable to load.
		    hardware_id: Identifier of the hardware to load.
		"""
		super().__init__(observable_id, GHardware, hardware_id)


class ObservableCPTPage(CPTPage):
	"""Display the observable CPT probability table editor."""

	def __init__(self, observable_id: str):
		"""Load the observable cpt and configure its available actions.

		Args:
		    observable_id: Identifier of the observable to load.
		"""
		super().__init__(GDirectObservable, observable_id, get_url)
