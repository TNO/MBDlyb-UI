# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
from nicegui import ui
from neomodel import db
from mbdlyb.gdb import cls
from mbdlyb.functional.gdb import GCluster, GFunction, GHardware, GDirectObservable, GDiagnosticTest
from mbdlyb_ui import Button, Table, TableColumn
from mbdlyb_ui.dialogs import confirm_delete, confirm_delete_relation
from mbdlyb_ui.helpers import goto, get_object_or_404, get_relation_or_404, save_object, get_url

from .base import FunctionalPage
from .helpers import save_new_object, RealizesRelation, AffectsRelation, ObservesRelation, TestsRelation
from .validation import base_name_validation


class Fault:
	"""Represent an editable hardware fault."""

	def __init__(self, name: str, prior: float):
		"""Initialize fault with its editable state.

		Args:
		    name: Name of this entry.
		    prior: Prior probability assigned to the fault.
		"""
		self.name = name
		self.prior = prior

	def __eq__(self, other):
		"""Compare this editable value with another value or name.

		Args:
		    other: Value to compare with this object.

		Returns:
		    Whether the compared values match.
		"""
		if isinstance(other, Fault):
			return self.name == other
		return False

	@classmethod
	def to_list(cls, d: dict[str, float]) -> list['Fault']:
		"""Convert stored fault rates to editable fault entries.

		Args:
		    d: Stored name-to-value pairs to convert into editable entries.

		Returns:
		    Editable entries created from the stored name-to-value mapping.
		"""
		return [Fault(k, v) for k, v in d.items()]

	@classmethod
	def from_list(cls, l: list['Fault']):
		"""Convert editable fault entries to stored prior probabilities.

		Args:
		    l: Editable cost or fault entries to convert into a stored mapping.

		Returns:
		    Mapping of entry names to their configured numeric values.
		"""
		return {f.name: f.prior for f in l}


def add_fault(fault_rates: list[Fault]):
	"""Append a hardware fault and refresh the fault table.

	Args:
	    fault_rates: Editable hardware faults and their rates.
	"""
	name = 'Fault_'
	for i in range(1, 100):
		if name + str(i) not in Fault.from_list(fault_rates):
			name = name + str(i)
			break
	fault_rates.append(Fault(name, 0.01))
	fault_table.refresh()


def drop_fault(fault_rates: list[Fault], fault: Fault):
	"""Remove a hardware fault and refresh the fault table.

	Args:
	    fault_rates: Editable hardware faults and their rates.
	    fault: Fault or cost entry selected for removal.
	"""
	fault_rates.remove(fault)
	fault_table.refresh()


@ui.refreshable
def fault_table(fault_rates: list[Fault]):
	"""Render editable hardware fault rows.

	Args:
	    fault_rates: Editable hardware faults and their rates.
	"""
	with ui.grid(columns=3).classes('vertical-bottom'):
		for col in ('Fault', 'Prior'):
			ui.label(col).classes('font-bold')
		ui.icon('add', color='primary').on('click', lambda: add_fault(fault_rates)).classes('cursor-pointer')
		for fault in fault_rates:
			ui.input('Fault').bind_value(fault, 'name')
			ui.number('Prior', min=0., max=1., step=.001).bind_value(fault, 'prior')
			ui.icon('delete', color='negative').on('click', lambda f=fault: drop_fault(fault_rates, f)).classes(
				'self-end cursor-pointer')


def hardware_form(hardware: GHardware, fault_rates: list[Fault], cluster: GCluster, update: bool = True):
	"""Render the hardware name, states, and fault controls.

	Args:
	    hardware: Hardware node whose properties are edited.
	    fault_rates: Editable hardware faults and their rates.
	    cluster: Parent cluster used to validate the hardware name.
	    update: Whether the hardware already exists for name validation.
	"""
	ui.input('Name', validation=base_name_validation(cluster, hardware if update else None)) \
		.bind_value(hardware, 'name').props('hide-bottom-space')
	fault_table(fault_rates)


class HardwareCreatePage(FunctionalPage):
	"""Display the hardware create editing page."""

	hardware: GHardware
	fault_rates = list[Fault]

	def __init__(self, cluster_id: str):
		"""Prepare a new hardware and configure its editing actions.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		cluster = get_object_or_404(GCluster, uid=cluster_id)
		self.hardware = cls(GHardware)(name='')
		self.fault_rates = Fault.to_list(self.hardware.fault_rates)
		super().__init__(f'New hardware in {cluster.name}', cluster, [
			Button('Discard', None, 'warning', lambda: goto(cluster)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable hardware create fields and available actions."""
		hardware_form(self.hardware, self.fault_rates, self.element, False)

	def _save(self):
		"""Save the hardware create changes to the model."""
		self.hardware.fault_rates = Fault.from_list(self.fault_rates)
		save_new_object(self.hardware, self.element)


class HardwareUpdatePage(FunctionalPage):
	"""Display the hardware update editing page."""

	hardware: GHardware
	fault_rates: list[Fault]

	def __init__(self, hardware_id):
		"""Load the hardware and configure its editing actions.

		Args:
		    hardware_id: Identifier of the hardware to load.
		"""
		self.hardware = get_object_or_404(GHardware, uid=hardware_id)
		self.fault_rates = Fault.to_list(self.hardware.fault_rates)
		super().__init__(f'Update {self.hardware}', self.hardware, [
			Button('Discard', None, 'warning', lambda: goto(self.hardware.get_net())),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable hardware update fields and available actions."""
		hardware_form(self.hardware, self.fault_rates, self.hardware.get_net())

	def _save(self):
		"""Save the hardware update changes to the model."""
		self.hardware.fault_rates = Fault.from_list(self.fault_rates)
		save_object(self.hardware, self.hardware.get_net())


class HardwareDetailsPage(FunctionalPage):
	"""Display the hardware details properties and relations."""

	hardware: GHardware

	def __init__(self, hardware_id: str):
		"""Load the hardware details and configure its available actions.

		Args:
		    hardware_id: Identifier of the hardware to load.
		"""
		self.hardware = get_object_or_404(GHardware, uid=hardware_id)
		super().__init__(f'Hardware {self.hardware.name}', self.hardware, [
			Button(None, 'edit', None, lambda: goto(f'{get_url(self.hardware)}/update'), 'Edit hardware'),
			Button(None, 'delete', 'negative',
				   lambda: confirm_delete(self.hardware, self.hardware.get_net()),
				   'Delete hardware')
		])

	def _show_content(self):
		"""Display hardware details properties, relations, and navigation actions."""
		base_url = get_url(self.hardware)
		with ui.row():
			ui.label('Indicated by')
			for test_result in self.hardware.indicated_by.order_by('name'):
				ui.link(test_result.name, get_url(test_result)).tooltip(str(test_result.fqn))
		with ui.grid(columns='1fr 1fr').classes('w-full'):
			with ui.card():
				Table('Realizes', self.hardware.realizes.order_by('name'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableColumn('Weight', lambda f: f.realized_by.relationship(self.hardware).weight)
				], self.hardware, [
						  Button(icon='add', tooltip='Add hardware realization',
								 handler=f'{base_url}/realizes/new')
					  ], [
						  Button(icon='edit', tooltip='Edit realization',
								 handler=lambda x: goto(f'{base_url}/realizes/{x.uid}/update')),
						  Button(icon='delete', color='negative', tooltip='Delete realization',
								 handler=lambda x: confirm_delete_relation('realizes', self.hardware, x, self.hardware))
					  ]).show()
			with ui.card():
				Table('Affects', self.hardware.affects.order_by('fqn_'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableColumn('Weight', lambda f: f.affected_by.relationship(self.hardware).weight)
				], self.hardware, [
						  Button(icon='add', tooltip='Add hardware side-effect',
								 handler=f'{base_url}/affects/new')
					  ], [
						  Button(icon='edit', tooltip='Edit side-effect',
								 handler=lambda x: goto(f'{base_url}/affects/{x.uid}/update')),
						  Button(icon='delete', color='negative', tooltip='Delete side-effect',
								 handler=lambda x: confirm_delete_relation('affects', self.hardware, x, self.hardware))
					  ]).show()
			with ui.card():
				Table('Observed by', self.hardware.observed_by.order_by('name'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableColumn('Weight', lambda o: o.observed_self.hardware.relationship(self.hardware).weight)
				], self.hardware, [
						  Button(icon='add', tooltip='Add observable',
								 handler=f'{base_url}/observedby/new')
					  ], [
						  Button(icon='edit', tooltip='Edit observable',
								 handler=lambda x: goto(f'{base_url}/observedby/{x.uid}/update')),
						  Button(icon='delete', color='negative', tooltip='Delete observable',
								 handler=lambda x: confirm_delete_relation('observed_by', self.hardware, x,
																		   self.hardware))
					  ]).show()


# REALIZES RELATION

def realizes_relation_form(relation: RealizesRelation):
	"""Render the realized function and relation weight controls.

	Args:
	    relation: Relation whose endpoints and weight are edited.
	"""
	options, _ = db.cypher_query(
		f'''MATCH
    (h:Hardware {{uid: '{relation.start_uid}'}})-[:PART_OF]->(:Cluster)<-[:PART_OF]-(f:Function)
WHERE
    NOT (h)-[:REALIZES]->(f)
RETURN f
ORDER BY f.name''', resolve_objects=True)
	options_dict = dict() if relation.end_uid is None else {relation.end_uid: relation.get_end_node().name}
	ui.select({**options_dict, **{sf[0].uid: sf[0].name for sf in options}}, label='Function',
			  with_input=True).bind_value(relation, 'end_uid')
	ui.number('Weight', min=0., max=1., precision=2, step=.01).bind_value(relation, 'weight')


class RealizesRelationCreatePage(FunctionalPage):
	"""Display the realizes relation create editing page."""

	hardware: GHardware
	relation: RealizesRelation

	def __init__(self, hardware_id: str):
		"""Prepare a new realizes relation and configure its editing actions.

		Args:
		    hardware_id: Identifier of the hardware to load.
		"""
		self.hardware = get_object_or_404(GHardware, uid=hardware_id)
		self.relation = RealizesRelation(self.hardware, end_node_type=GFunction)
		super().__init__(f'Add realizes to {self.hardware}', self.hardware, [
			Button('Discard', None, 'warning', lambda: goto(self.hardware)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable realizes relation create fields and available actions."""
		realizes_relation_form(self.relation)

	def _save(self):
		"""Save the realizes relation create changes to the model."""
		self.relation.save(self.hardware)


class RealizesRelationUpdatePage(FunctionalPage):
	"""Display the realizes relation update editing page."""

	hardware: GHardware
	relation: RealizesRelation

	def __init__(self, hardware_id: str, function_id: str):
		"""Load the realizes relation and configure its editing actions.

		Args:
		    hardware_id: Identifier of the hardware to load.
		    function_id: Identifier of the function to load.
		"""
		self.hardware = get_object_or_404(GHardware, uid=hardware_id)
		function = get_object_or_404(GFunction, uid=function_id)
		relation = get_relation_or_404(self.hardware, function, 'realizes')
		self.relation = RealizesRelation(self.hardware, function, weight=relation.weight)
		super().__init__(f'Update {relation}', self.hardware, [
			Button('Discard', None, 'warning', lambda: goto(self.hardware)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable realizes relation update fields and available actions."""
		realizes_relation_form(self.relation)

	def _save(self):
		"""Save the realizes relation update changes to the model."""
		self.relation.save(self.hardware)


# AFFECTS RELATION

def affects_relation_form(relation: AffectsRelation, root: GCluster):
	"""Render the affected node and relation weight controls.

	Args:
	    relation: Relation whose endpoints and weight are edited.
	    root: Root cluster used to list eligible relation targets.
	"""
	options, _ = db.cypher_query(
		f'''MATCH
    (h:Hardware {{uid: '{relation.start_uid}'}})-[:PART_OF]->(c:Cluster),
    (f:Function)-[:PART_OF*]->(:Cluster {{uid: '{root.uid}'}})
WHERE
    NOT (h)-[:AFFECTS]->(f) AND NOT (f)-[:PART_OF]->(c)
 RETURN f''', resolve_objects=True)
	options_dict = dict() if relation.end_uid is None else {relation.end_uid: relation.get_end_node().name}
	ui.select({**options_dict, **{sf[0].uid: sf[0].name for sf in options}}, label='Function').bind_value(
		relation, 'end_uid')
	ui.number('Weight', min=0., max=1., precision=2, step=.01).bind_value(relation, 'weight')


class AffectsRelationCreatePage(FunctionalPage):
	"""Display the affects relation create editing page."""

	hardware: GHardware
	relation: AffectsRelation

	def __init__(self, hardware_id: str):
		"""Prepare a new affects relation and configure its editing actions.

		Args:
		    hardware_id: Identifier of the hardware to load.
		"""
		self.hardware = get_object_or_404(GHardware, uid=hardware_id)
		self.relation = AffectsRelation(self.hardware, end_node_type=GFunction)
		super().__init__(f'Add affects to {self.hardware}', self.hardware, [
			Button('Discard', None, 'warning', lambda: goto(self.hardware)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable affects relation create fields and available actions."""
		affects_relation_form(self.relation, self.hardware.get_root())

	def _save(self):
		"""Save the affects relation create changes to the model."""
		self.relation.save(self.hardware)


class AffectsRelationUpdatePage(FunctionalPage):
	"""Display the affects relation update editing page."""

	hardware: GHardware
	relation: AffectsRelation

	def __init__(self, hardware_id: str, function_id: str):
		"""Load the affects relation and configure its editing actions.

		Args:
		    hardware_id: Identifier of the hardware to load.
		    function_id: Identifier of the function to load.
		"""
		self.hardware = get_object_or_404(GHardware, uid=hardware_id)
		function = get_object_or_404(GFunction, uid=function_id)
		relation = get_relation_or_404(self.hardware, function, 'affects')
		self.relation = AffectsRelation(self.hardware, function, weight=relation.weight)
		super().__init__(f'Update {relation}', self.hardware, [
			Button('Discard', None, 'warning', lambda: goto(self.hardware)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable affects relation update fields and available actions."""
		affects_relation_form(self.relation, self.hardware.get_root())

	def _save(self):
		"""Save the affects relation update changes to the model."""
		self.relation.save(self.hardware)


# OBSERVED BY RELATION

def observes_relation_form(o_relation: ObservesRelation):
	"""Render the observed node and relation weight controls.

	Args:
	    o_relation: Observes relation being edited.
	"""
	options, _ = db.cypher_query(
		f'''MATCH
    (h:Hardware {{uid: '{o_relation.start_uid}'}})-[:PART_OF]->(:Cluster)(()-[:PART_OF]->()){{0,99}}(:Cluster)<-[PART_OF]-(o:DirectObservable)
WHERE
    NOT (h)-[:OBSERVED_BY]->(o)
 RETURN o''', resolve_objects=True)
	options_dict = dict() if o_relation.end_uid is None else {o_relation.end_uid: o_relation.get_end_node().fqn}
	ui.select({**options_dict, **{sf[0].uid: sf[0].fqn for sf in options}}, label='Observer',
			  with_input=True).bind_value(o_relation, 'end_uid')
	ui.number('Weight', min=0., max=1., precision=2, step=.01).bind_value(o_relation, 'weight')


class ObservesRelationCreatePage(FunctionalPage):
	"""Display the observes relation create editing page."""

	hardware: GHardware
	relation: ObservesRelation

	def __init__(self, hardware_id: str):
		"""Prepare a new observes relation and configure its editing actions.

		Args:
		    hardware_id: Identifier of the hardware to load.
		"""
		self.hardware = get_object_or_404(GHardware, uid=hardware_id)
		self.relation = ObservesRelation(self.hardware, end_node_type=GDirectObservable)
		super().__init__(f'Add observed_by to {self.hardware}', self.hardware, [
			Button('Discard', None, 'warning', lambda: goto(self.hardware)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable observes relation create fields and available actions."""
		observes_relation_form(self.relation)

	def _save(self):
		"""Save the observes relation create changes to the model."""
		self.relation.save(self.hardware)


class ObservesRelationUpdatePage(FunctionalPage):
	"""Display the observes relation update editing page."""

	hardware: GHardware
	relation: ObservesRelation

	def __init__(self, hardware_id: str, observable_id: str):
		"""Load the observes relation and configure its editing actions.

		Args:
		    hardware_id: Identifier of the hardware to load.
		    observable_id: Identifier of the observable to load.
		"""
		self.hardware = get_object_or_404(GHardware, uid=hardware_id)
		observable = get_object_or_404(GDirectObservable, uid=observable_id)
		relation = get_relation_or_404(self.hardware, observable, 'observed_by')
		self.relation = ObservesRelation(self.hardware, observable, weight=relation.weight)
		super().__init__(f'Update {relation}', self.hardware, [
			Button('Discard', None, 'warning', lambda: goto(self.hardware)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable observes relation update fields and available actions."""
		observes_relation_form(self.relation)

	def _save(self):
		"""Save the observes relation update changes to the model."""
		self.relation.save(self.hardware)


# TESTED BY RELATION

def tests_relation_form(t_relation: TestsRelation):
	"""Render the tested node and relation weight controls.

	Args:
	    t_relation: Tests relation being edited.
	"""
	options, _ = db.cypher_query(
		f'''MATCH
    (h:Hardware {{uid: '{t_relation.start_uid}'}})-[:PART_OF]->(:Cluster)(()-[:PART_OF]->()){{0,99}}(:Cluster)<-[PART_OF]-(t:DiagnosticTest)
WHERE
    NOT (h)-[:TESTED_BY]->(t)
 RETURN t''', resolve_objects=True)
	options_dict = dict() if t_relation.end_uid is None else {t_relation.end_uid: str(t_relation.get_end_node().fqn)}
	ui.select({**options_dict, **{sf[0].uid: str(sf[0].fqn) for sf in options}}, label='Diagnostic test',
			  with_input=True).bind_value(t_relation, 'end_uid')
	ui.number('Weight', min=0., max=1., precision=2, step=.01).bind_value(t_relation, 'weight')


class TestsRelationCreatePage(FunctionalPage):
	"""Display the tests relation create editing page."""

	hardware: GHardware
	relation: TestsRelation

	def __init__(self, hardware_id: str):
		"""Prepare a new tests relation and configure its editing actions.

		Args:
		    hardware_id: Identifier of the hardware to load.
		"""
		self.hardware = get_object_or_404(GHardware, uid=hardware_id)
		self.relation = TestsRelation(self.hardware, end_node_type=GDiagnosticTest)
		super().__init__(f'Add tested_by to {self.hardware}', self.hardware, [
			Button('Discard', None, 'warning', lambda: goto(self.hardware)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable tests relation create fields and available actions."""
		tests_relation_form(self.relation)

	def _save(self):
		"""Save the tests relation create changes to the model."""
		self.relation.save(self.hardware)


class TestsRelationUpdatePage(FunctionalPage):
	"""Display the tests relation update editing page."""

	hardware: GHardware
	relation: TestsRelation

	def __init__(self, hardware_id: str, test_id: str):
		"""Load the tests relation and configure its editing actions.

		Args:
		    hardware_id: Identifier of the hardware to load.
		    test_id: Identifier of the diagnostic test to load.
		"""
		self.hardware = get_object_or_404(GHardware, uid=hardware_id)
		test = get_object_or_404(GDiagnosticTest, uid=test_id)
		relation = get_relation_or_404(self.hardware, test, 'tested_by')
		self.relation = TestsRelation(self.hardware, test, weight=relation.weight)
		super().__init__(f'Update {relation}', self.hardware, [
			Button('Discard', None, 'warning', lambda: goto(self.hardware)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable tests relation update fields and available actions."""
		tests_relation_form(self.relation)

	def _save(self):
		"""Save the tests relation update changes to the model."""
		self.relation.save(self.hardware)
