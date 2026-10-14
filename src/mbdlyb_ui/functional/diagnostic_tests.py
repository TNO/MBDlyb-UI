# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
from typing import Optional

from nicegui import ui
from mbdlyb.gdb import cls
from mbdlyb.functional.gdb import GCluster, GDiagnosticTest, GDiagnosticTestResult
from mbdlyb_ui import Button, Table, TableColumn, TableMultiColumn
from mbdlyb_ui.dialogs import confirm, confirm_delete
from mbdlyb_ui.helpers import get_object_or_404, goto, save_object, get_url

from .base import FunctionalPage
from .helpers import save_new_object
from .validation import base_name_validation


class TestCost:
	"""Represent an editable diagnostic test cost."""

	def __init__(self, name: str, cost: float):
		"""Initialize test cost with its editable state.

		Args:
		    name: Name of this entry.
		    cost: Numeric cost assigned to the test.
		"""
		self.name = name
		self.cost = cost

	def __eq__(self, other):
		"""Compare this editable value with another value or name.

		Args:
		    other: Value to compare with this object.

		Returns:
		    Whether the compared values match.
		"""
		if isinstance(other, TestCost):
			return self.name == other
		return False

	@classmethod
	def to_list(cls, d: dict[str, float]) -> list['TestCost']:
		"""Convert stored cost values to editable test cost entries.

		Args:
		    d: Stored name-to-value pairs to convert into editable entries.

		Returns:
		    Editable entries created from the stored name-to-value mapping.
		"""
		return [TestCost(k, v) for k, v in d.items()]

	@classmethod
	def from_list(cls, l: list['TestCost']) -> dict[str, float]:
		"""Convert editable test costs to their stored mapping.

		Args:
		    l: Editable cost or fault entries to convert into a stored mapping.

		Returns:
		    Mapping of entry names to their configured numeric values.
		"""
		return {f.name: f.cost for f in l}


def add_cost(test_costs: list[TestCost]):
	"""Append a diagnostic test cost and refresh the cost table.

	Args:
	    test_costs: Editable diagnostic test cost entries.
	"""
	name = 'Cost_'
	for i in range(1, 100):
		if name + str(i) not in TestCost.from_list(test_costs):
			name = name + str(i)
			break
	test_costs.append(TestCost(name, 1.))
	cost_table.refresh()


def drop_cost(test_costs: list[TestCost], fault: TestCost):
	"""Remove a diagnostic test cost and refresh the cost table.

	Args:
	    test_costs: Editable diagnostic test cost entries.
	    fault: Fault or cost entry selected for removal.
	"""
	test_costs.remove(fault)
	cost_table.refresh()


@ui.refreshable
def cost_table(test_costs: list[TestCost], cost_names: list[str]):
	"""Render editable diagnostic test cost rows.

	Args:
	    test_costs: Editable diagnostic test cost entries.
	    cost_names: Available names for diagnostic test costs.
	"""
	with ui.grid(columns=3).classes('vertical-bottom'):
		for col in ('Name', 'Cost'):
			ui.label(col).classes('font-bold')
		ui.icon('add', color='primary').on('click', lambda: add_cost(test_costs)).classes('cursor-pointer')
		for cost in test_costs:
			ui.select(cost_names, label='Name', new_value_mode='add-unique').bind_value(cost, 'name')
			ui.number('Cost', min=0., step=1.).bind_value(cost, 'cost')
			ui.icon('delete', color='negative').on('click', lambda f=cost: drop_cost(test_costs, f)).classes(
				'self-end cursor-pointer')


class TestProps:
	"""Hold editable test form state."""

	def __init__(self, add_result: bool = False, result_name: str = ''):
		"""Initialize test props with its editable state.

		Args:
		    add_result: Whether to create a default result for the new test.
		    result_name: Name for the default test result.
		"""
		self.add_result: bool = add_result
		self.result_name: str = result_name


class TestUpdatePage(FunctionalPage):
	"""Display the test update editing page."""

	update: bool
	cluster: GCluster
	test: GDiagnosticTest
	props: TestProps
	test_costs: list[TestCost]
	defined_costs: list[str]

	def __init__(self, test_id: Optional[str] = None, cluster_id: Optional[str] = None):
		"""Load the test and configure its editing actions.

		Args:
		    test_id: Identifier of the diagnostic test to load.
		    cluster_id: Identifier of the cluster to load.
		"""
		self.defined_costs = self._get_defined_costs()
		if test_id:
			self.update = True
			self.test = get_object_or_404(GDiagnosticTest, uid=test_id)
			self.cluster = self.test.get_net()
			title = f'Update diagnostic test {self.test}'
			element = self.test
		else:
			self.update = False
			self.cluster = get_object_or_404(GCluster, uid=cluster_id)
			self.test = cls(GDiagnosticTest)(name='', fixed_cost={n: 0. for n in self.defined_costs})
			title = f'New diagnostic test in {self.cluster.name}'
			element = self.cluster
		self.test_costs = TestCost.to_list(self.test.fixed_cost)
		self.props = TestProps()
		super().__init__(title, element, [
			Button('Discard', None, 'warning', lambda: goto(self.cluster)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable test update fields and available actions."""
		test_name_input = ui.input('Name',
								   validation=base_name_validation(self.cluster, self.test if self.update else None)) \
			.bind_value(self.test, 'name').props('hide-bottom-space')
		if not self.update:
			ui.checkbox('Add default test result?').bind_value(self.props, 'add_result')
			test_result_input = ui.input('Result name',
										 placeholder='Leave empty to append \'_Result\' to the test name',
										 validation=base_name_validation(self.cluster,
																		 allow_empty=True)).bind_visibility_from(
				self.props, 'add_result').bind_value(self.props, 'result_name').props('hide-bottom-space')
			test_name_input.validation['Test and Result must have different names'] = lambda \
					s: s != test_result_input.value
			test_result_input.validation['Test and Result must have different names'] = lambda \
					s: s != test_name_input.value
			test_name_input.on_value_change(test_result_input.validate)
			test_result_input.on_value_change(test_name_input.validate)
		cost_table(self.test_costs, self.defined_costs)

	def _save(self):
		"""Save the test update changes to the model."""
		self.test.fixed_cost = TestCost.from_list(self.test_costs)
		if self.update:
			save_object(self.test, self.test.get_net())
		else:
			save_new_object(self.test, self.cluster, disable_redirect=self.props.add_result)
			if self.props.add_result:
				result = cls(GDiagnosticTestResult)(name=self.props.result_name or f'{self.test.name}_Result')
				save_new_object(result, self.cluster, True)
				result.results_from.connect(self.test)
				goto(self.test)

	@staticmethod
	def _get_defined_costs() -> list[str]:
		"""Collect the diagnostic test's configured costs.

		Returns:
		    Configured model entries used to populate the editor.
		"""
		return list(sorted({n for t in GDiagnosticTest.nodes.all() for n, c in t.fixed_cost.items()}))


class TestDetailsPage(FunctionalPage):
	"""Display the test details properties and relations."""

	test: GDiagnosticTest

	def __init__(self, test_id: str):
		"""Load the test details and configure its available actions.

		Args:
		    test_id: Identifier of the diagnostic test to load.
		"""
		self.test = get_object_or_404(GDiagnosticTest, uid=test_id)
		cluster = self.test.get_net()
		buttons = [
			Button(None, 'edit', 'primary', f'{get_url(self.test)}/update', 'Edit diagnostic test'),
			Button(None, 'delete', 'negative', lambda: confirm_delete(self.test, cluster), 'Delete diagnostic test')]
		if not (self.test.at_root or cluster.at_root):
			buttons = [Button(None, 'move_up', 'secondary', lambda: confirm('Move up test',
																			f'Are you sure to move {self.test.name} up to {cluster.get_net().fqn}?',
																			'I am sure', self._move_up),
							  'Move diagnostic test up')] + buttons
		super().__init__(f'Diagnostic test {self.test.name}', self.test, buttons)

	def _show_content(self):
		"""Display test details properties, relations, and navigation actions."""
		with ui.row():
			ui.label('Costs').classes('font-bold')
			ui.label(', '.join(f'{n}({c})' for n, c in self.test.fixed_cost.items()))
		with ui.grid(columns='1fr 1fr').classes('w-full'):
			with ui.card().classes('col-span-full'):
				Table('Test results', self.test.test_results.order_by('name'), [
					TableColumn('Name', 'name', None, 'fqn'),
					TableColumn('FPR', 'fp_rate', None, None),
					TableColumn('FNR', 'fn_rate', None, None),
					TableMultiColumn('Tested functions', 'name', None, 'fqn', 'indicated_functions'),
					TableMultiColumn('Tested hardware', 'name', None, 'fqn', 'indicated_hardware')
				], self.test, [Button(icon='add', color='positive', tooltip='Add test result',
									  handler=f'{get_url(self.test)}/results/new')], [
						  Button(icon='border_all', color='secondary', tooltip='Update CPT of {}',
								 handler=lambda x: goto(f'/test_result/{x.uid}/cpt/')),
						  Button(icon='table_view', color='primary', tooltip='Edit tested items of {}',
								 handler=lambda x: goto(f'/test_result/{x.uid}/tests/')),
						  Button(icon='edit', tooltip='Edit {}',
								 handler=lambda x: goto(f'/test_result/{x.uid}/update/')),
						  Button(icon='delete', color='negative', tooltip='Delete {}',
								 handler=lambda x: confirm_delete(x, self.test))
					  ]).show()

	def _move_up(self):
		"""Move the selected item earlier in its ordering."""
		self.test.set_net(self.test.get_net().get_net())
		goto(self.test)
