# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
from typing import Optional

from nicegui import ui
from neomodel import db

from mbdlyb.gdb import cls
from mbdlyb.functional import DiagnosticTestResult
from mbdlyb.functional.gdb import GDiagnosticTest, GDiagnosticTestResult, GFunction, GHardware
from mbdlyb_ui import Button
from mbdlyb_ui.helpers import get_object_or_404, goto, save_object

from .base import FunctionalPage, CPTPage
from .helpers import save_new_object, IndicatesRelation, StateTable, state_table
from .validation import base_name_validation


TEST_RESULT_RELATION_MAP = {
	GFunction: 'indicated_functions',
	GHardware: 'indicated_hardware'
}

TEST_RESULT_NODE_TYPE_MAP = {
	GFunction: 'Function',
	GHardware: 'Hardware'
}


class TestResultUpdatePage(FunctionalPage):
	"""Display the test result update editing page."""

	update: bool
	test: GDiagnosticTest
	test_result: GDiagnosticTestResult
	states: StateTable

	def __init__(self, result_id: Optional[str] = None, test_id: Optional[str] = None):
		"""Load the test result and configure its editing actions.

		Args:
		    result_id: Identifier of the test result to load.
		    test_id: Identifier of the diagnostic test to load.
		"""
		if result_id:
			self.update = True
			self.test_result = get_object_or_404(GDiagnosticTestResult, uid=result_id)
			self.test = self.test_result.results_from.single()
			title = f'Update diagnostic test result {self.test_result}'
		else:
			self.update = False
			self.test = get_object_or_404(GDiagnosticTest, uid=test_id)
			self.test_result = cls(GDiagnosticTestResult)(name='')
			title = f'New diagnostic test result in {self.test}'
		self.states = StateTable.from_list(self.test_result.states_)
		super().__init__(title, self.test, [
			Button('Discard', None, 'warning', lambda: goto(self.test)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable test result update fields and available actions."""
		ui.input('Name', validation=base_name_validation(self.test.get_net(),
														 self.test_result if self.update else None)).bind_value(
			self.test_result, 'name').props('hide-bottom-space')
		ui.number('False positive rate', min=0., max=1., step=.0001).bind_value(self.test_result, 'fp_rate')
		ui.number('False negative rate', min=0., max=1., step=.0001).bind_value(self.test_result, 'fn_rate')
		state_table(self.states, DiagnosticTestResult.DEFAULT_STATES)

	def _save(self):
		"""Save the test result update changes to the model."""
		self.test_result.states = self.states.to_list()
		if self.update:
			save_object(self.test_result)
		else:
			save_new_object(self.test_result, self.test.get_net())
			self.test_result.results_from.connect(self.test)
		goto(self.test)


class TestResultRelationPage(FunctionalPage):
	"""Display the test result relation editing page."""

	test_result: GDiagnosticTestResult
	test: GDiagnosticTest
	indicates: dict

	def __init__(self, result_id: str):
		"""Load the test result relation and configure its available actions.

		Args:
		    result_id: Identifier of the test result to load.
		"""
		self.test_result = get_object_or_404(GDiagnosticTestResult, uid=result_id)
		self.test = self.test_result.results_from.single()
		self._set_indicates()
		super().__init__(f'Tested items of {self.test_result}', self.test_result, [
			Button('Discard', None, 'warning', lambda: goto(self.test)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable test result relation fields and available actions."""
		with ui.grid(columns=2).classes('gap-0'):
			for c, node_types in self.indicates.items():
				ui.label(str(c.fqn)).classes('col-span-full text-h6 border p-2')
				for node_type, nodes in node_types.items():
					ui.label(node_type).classes('col-span-full text-weight-bold border p-1')
					for n_uid, n in nodes.items():
						cb = ui.checkbox(str(n['n'].fqn)).bind_value(n, 'checked').props('size=xs')
						ui.slider(min=.0, max=1., step=.01).bind_enabled_from(cb, 'value').bind_value(n,
																									  'weight').props(
							'label-always').classes('p-2')

	def _set_indicates(self):
		"""Load selectable function and hardware indications and their weights."""
		qr, _ = db.cypher_query(f'''MATCH
			(:DiagnosticTestResult {{uid: '{self.test_result.uid}'}})-[:PART_OF]->(:Cluster)<-[:PART_OF*0..]-(c:Cluster)
		RETURN c,
			COLLECT {{ MATCH (c)<-[:PART_OF]-(f:Function) RETURN f ORDER BY f.fqn }} as functions,
			COLLECT {{ MATCH (c)<-[:PART_OF]-(h:Hardware) RETURN h ORDER BY h.fqn }} as hardware
		ORDER BY c.fqn''', resolve_objects=True)
		self.indicates = {
			r[0]: {
				ntype: {
					n.uid: {
						'n': n, 'checked': False, 'weight': 1.0
					} for n in r[elem]
				} for ntype, elem in [(TEST_RESULT_NODE_TYPE_MAP[GFunction], 1), (TEST_RESULT_NODE_TYPE_MAP[GHardware], 2)]
			} for r in qr
		}
		for tn in self.test_result.get_observed_nodes():
			tn_r = self.test_result.__getattribute__(TEST_RESULT_RELATION_MAP[type(tn)]).relationship(tn)
			e = self.indicates[tn.get_net()][TEST_RESULT_NODE_TYPE_MAP[type(tn)]][tn.uid]
			e['checked'] = True
			e['weight'] = tn_r.weight

	def _save(self):
		"""Save the test result relation changes to the model."""
		self.test_result.indicated_functions.disconnect_all()
		self.test_result.indicated_hardware.disconnect_all()
		for node_type_groups in self.indicates.values():
			for node_type, nodes in node_type_groups.items():
				for n_uid, node in nodes.items():
					if node['checked']:
						IndicatesRelation(node['n'], self.test_result, weight=node['weight']).save()
		goto(self.test)


class TestResultCPTPage(CPTPage):
	"""Display the test result CPT probability table editor."""

	def __init__(self, result_id: str):
		"""Load the test result cpt and configure its available actions.

		Args:
		    result_id: Identifier of the test result to load.
		"""
		super().__init__(GDiagnosticTestResult, result_id, lambda r: r.test)
