# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
from typing import Optional

from neomodel import db
from nicegui import ui

from mbdlyb.gdb import cls
from mbdlyb.functional import Function
from mbdlyb.functional.gdb import GCluster, GFunction, GDirectObservable, GDiagnosticTest
from mbdlyb_ui import Button, Table, TableColumn
from mbdlyb_ui.dialogs import confirm_delete, confirm_delete_relation
from mbdlyb_ui.helpers import goto, get_object_or_404, get_relation_or_404, save_object, get_url

from .base import FunctionalPage, CPTPage
from .helpers import (save_new_object, SubfunctionOfRelation, RequiredForRelation, ObservesRelation, TestsRelation,
					  StateTable, state_table)
from .validation import base_name_validation


def function_form(function: GFunction, states: StateTable, cluster: GCluster, update: bool = True):
	"""Render the function name and state editing controls.

	Args:
	    function: Function whose properties are edited.
	    states: Editable state names for the function.
	    cluster: Parent cluster used to validate the function name.
	    update: Whether the function already exists for name validation.
	"""
	ui.input('Name', validation=base_name_validation(cluster, function if update else None)) \
		.bind_value(function, 'name').props('hide-bottom-space')
	state_table(states, Function.DEFAULT_STATES)


class FunctionCreatePage(FunctionalPage):
	"""Display the function create editing page."""

	function: GFunction
	states: StateTable

	def __init__(self, cluster_id: str):
		"""Prepare a new function and configure its editing actions.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		cluster = get_object_or_404(GCluster, uid=cluster_id)
		self.function = cls(GFunction)(name='')
		self.states = StateTable.from_list(self.function.states_)
		super().__init__(f'New function in {cluster.name}', cluster, [
			Button('Discard', None, 'warning', lambda: goto(cluster)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable function create fields and available actions."""
		function_form(self.function, self.states, self.element, False)

	def _save(self):
		"""Save the function create changes to the model."""
		self.function.states = self.states.to_list()
		save_new_object(self.function, self.element)


class FunctionUpdatePage(FunctionalPage):
	"""Display the function update editing page."""

	function: GFunction
	states: StateTable

	def __init__(self, function_id: str):
		"""Load the function and configure its editing actions.

		Args:
		    function_id: Identifier of the function to load.
		"""
		self.function = get_object_or_404(GFunction, uid=function_id)
		self.states = StateTable.from_list(self.function.states_)
		super().__init__(f'Update {self.function}', self.function, [
			Button('Discard', None, 'warning', lambda: goto(self.function.get_net())),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable function update fields and available actions."""
		function_form(self.function, self.states, self.function.get_net())

	def _save(self):
		"""Save the function update changes to the model."""
		self.function.states = self.states.to_list()
		save_object(self.function, self.function.get_net())


class FunctionDetailPage(FunctionalPage):
	"""Display the function detail properties and relations."""

	function: GFunction

	def __init__(self, function_id):
		"""Load the function detail and configure its available actions.

		Args:
		    function_id: Identifier of the function to load.
		"""
		self.function = get_object_or_404(GFunction, uid=function_id)
		super().__init__(f'Function {self.function.name}', self.function, [
			Button(None, 'border_all', 'secondary', lambda: goto(f'{get_url(self.function)}/cpt'), 'Modify CPT'),
			Button(None, 'edit', None, lambda: goto(f'{get_url(self.function)}/update'), 'Edit function'),
			Button(None, 'delete', 'negative',
				   lambda: confirm_delete(self.function, self.function.get_net()), 'Delete function')
		])
	def _show_content(self):
		"""Display function detail properties, relations, and navigation actions."""
		url_base = get_url(self.function)
		if self.function.has_custom_states:
			with ui.row():
				ui.label('Custom states')
				ui.label(' | '.join(self.function.states))
		for label, rel in (('Subfunction of', 'subfunction_of'),
									   ('Realized by', 'realized_by'),
									   ('Requires', 'requires'),
									   ('Indicated by', 'indicated_by')):
			if self.function.__getattribute__(rel):
				with ui.row():
					ui.label(label)
					for sf in self.function.__getattribute__(rel).order_by('name'):
						ui.link(sf.name, get_url(sf)).tooltip(str(sf.fqn))
		with ui.grid(columns='1fr 1fr').classes('w-full'):
			with ui.card():
				Table('Subfunctions', self.function.subfunctions.order_by('name'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableColumn('Weight', lambda sf: sf.subfunction_of.relationship(self.function).weight)
				], self.function, [
						  Button(icon='add', color='primary', handler=f'{url_base}/subfunction/new',
								 tooltip='Add subfunction')
					  ], [
						  Button(icon='edit', tooltip=f'Edit subfunction relation',
								 handler=lambda x: goto(f'{url_base}/subfunction/{x.uid}/update')),
						  Button(icon='delete', color='negative', tooltip=f'Delete subfunction relation',
								 handler=lambda x: confirm_delete_relation('subfunctions', self.function, x,
																		   self.function))
					  ]).show()
			if not self.function.has_subfunctions or self.function.required_for:
				with ui.card():
					Table('Required for', self.function.required_for.order_by('name'), [
						TableColumn('Name', 'name', get_url, 'fqn'),
						TableColumn('Weight', lambda rf: rf.requires.relationship(self.function).weight)
					], self.function, [
							  Button(icon='add', color='primary',
									 handler=f'{url_base}/requiredfor/new',
									 tooltip='Add requires relation')
						  ], [
							  Button(icon='edit', tooltip=f'Edit requirement',
									 handler=lambda x: goto(
										 f'{url_base}/requiredfor/{x.uid}/update')),
							  Button(icon='delete', color='negative', tooltip=f'Delete requirement',
									 handler=lambda x: confirm_delete_relation('required_for', self.function, x,
																			   self.function))
						  ]).show()
			with ui.card():
				Table('Observed by', self.function.observed_by.order_by('name'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableColumn('Weight', lambda o: o.observed_functions.relationship(self.function).weight)
				], self.function, [
						  Button(icon='add', color='primary', handler=f'{url_base}/observedby/new',
								 tooltip='Add observer')
					  ], [
						  Button(icon='edit', tooltip=f'Edit observable relation',
								 handler=lambda x: goto(f'{url_base}/observedby/{x.uid}/update')),
						  Button(icon='delete', color='negative', tooltip=f'Delete observable relation',
								 handler=lambda x: confirm_delete_relation('observed_by', self.function, x,
																		   self.function))
					  ]).show()


# SUBFUNCTION RELATION

def subfunction_relation_form(sf_relation: SubfunctionOfRelation):
	"""Render the parent function and relation weight controls.

	Args:
	    sf_relation: Subfunction relation being edited.
	"""
	options, _ = db.cypher_query(
		f'''MATCH
    (f:Function {{uid: '{sf_relation.start_uid}'}})-[:PART_OF]->(c:Cluster),
    (g:Function)-[r:PART_OF]->{{0,99}}(c)
WHERE
    NOT (g)-[:SUBFUNCTION_OF]->(f) AND g <> f
 RETURN g
 ORDER BY size(r), g.fqn''', resolve_objects=True)
	options_dict = dict() if sf_relation.end_uid is None else {sf_relation.end_uid: sf_relation.get_end_node().name}
	ui.select({**options_dict, **{sf[0].uid: str(sf[0].fqn) for sf in options}}, label='Subfunction',
			  with_input=True).bind_value(sf_relation, 'end_uid')
	ui.number('Weight', min=0., max=1., precision=2, step=.01).bind_value(sf_relation, 'weight')


class SubfunctionRelationCreatePage(FunctionalPage):
	"""Display the subfunction relation create editing page."""

	sf_relation: SubfunctionOfRelation

	def __init__(self, function_id: str):
		"""Prepare a new subfunction relation and configure its editing actions.

		Args:
		    function_id: Identifier of the function to load.
		"""
		function = get_object_or_404(GFunction, uid=function_id)
		self.sf_relation = SubfunctionOfRelation(function, end_node_type=GFunction)
		super().__init__(f'Add subfunction to {function}', function, [
			Button('Discard', None, 'warning', lambda: goto(function)),
			Button('Save', 'save', None, lambda: self.sf_relation.save(function))
		])

	def _show_content(self):
		"""Render editable subfunction relation create fields and available actions."""
		subfunction_relation_form(self.sf_relation)


class SubfunctionRelationUpdatePage(FunctionalPage):
	"""Display the subfunction relation update editing page."""

	sf_relation: SubfunctionOfRelation

	def __init__(self, function_id: str, subfunction_id: str):
		"""Load the subfunction relation and configure its editing actions.

		Args:
		    function_id: Identifier of the function to load.
		    subfunction_id: Identifier of the subfunction to edit.
		"""
		function = get_object_or_404(GFunction, uid=function_id)
		subfunction = get_object_or_404(GFunction, uid=subfunction_id)
		relation = get_relation_or_404(function, subfunction, 'subfunctions')
		self.sf_relation = SubfunctionOfRelation(function, subfunction, weight=relation.weight)
		super().__init__(f'Update {relation}', function, [
			Button('Discard', None, 'warning', lambda: goto(function)),
			Button('Save', 'save', None, lambda: self.sf_relation.save(function))
		])

	def _show_content(self):
		"""Render editable subfunction relation update fields and available actions."""
		subfunction_relation_form(self.sf_relation)


class SubfunctionRelationTablePage(FunctionalPage):
	"""Display the subfunction relation table relation table."""

	function: GFunction
	groups: dict[str, list[str]]
	eligable_sfs: dict[str, dict]

	def __init__(self, function_id: str):
		"""Load the subfunction relation table and configure its available actions.

		Args:
		    function_id: Identifier of the function to load.
		"""
		self.function = get_object_or_404(GFunction, uid=function_id)
		self._load_functions()
		super().__init__(f'Subfunctions of {self.function}', self.function, [
			Button('Discard', None, 'warning', lambda: goto(self.function)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Display subfunction relation table rows and their editing controls."""
		with ui.grid(columns=2).classes('gap-0'):
			for c, sfs in self.groups.items():
				if not sfs:
					continue
				ui.label(c).classes('col-span-full text-h6 border p-2')
				for f_uid in sfs:
					fn = self.eligable_sfs[f_uid]
					cb = ui.checkbox(str(fn['fn'].fqn)).bind_value(fn, 'checked').props('size=xs')
					ui.slider(min=.0, max=1., step=.01).bind_enabled_from(cb, 'value').bind_value(fn, 'weight').props(
						'label-always').classes('p-2')

	def _load_functions(self):
		"""Load functions eligible for the subfunction relation table."""
		functions, _ = db.cypher_query(
			f'''MATCH
			(f:Function {{uid: '{self.function.uid}'}})-[:PART_OF]->(c:Cluster),
			(sc:Cluster)-[r:PART_OF]->{{0,99}}(c)
		RETURN sc.fqn AS cluster, COLLECT {{
			MATCH (g:Function)-[:PART_OF]->(sc)
			WHERE g <> f
			RETURN g
			ORDER BY g.fqn
		}} AS functions
		ORDER BY size(r), sc.fqn''', resolve_objects=True)
		self.groups: dict[str, list[str]] = dict()
		self.eligable_sfs: dict[str, dict] = dict()
		for r in functions:
			if r[0] not in self.groups:
				self.groups[r[0]] = []
			for fn in r[1][0]:
				self.groups[r[0]].append(fn.uid)
				self.eligable_sfs[fn.uid] = {'fn': fn, 'checked': False, 'weight': 1.0}
		for sf in self.function.subfunctions.all():
			sf_r = self.function.subfunctions.relationship(sf)
			e = self.eligable_sfs[sf.uid]
			e['checked'] = True
			e['weight'] = sf_r.weight

	def _save(self):
		"""Save the subfunction relation table changes to the model."""
		self.function.subfunctions.disconnect_all()
		for sf in self.eligable_sfs.values():
			if sf['checked']:
				SubfunctionOfRelation(self.function, sf['fn'], weight=sf['weight']).save()
		goto(self.function.get_net())


# REQUIRED_FOR RELATION

def requiredfor_relation_form(rf_relation: RequiredForRelation, root: GCluster):
	"""Render the required-for target, weight, and operating mode controls.

	Args:
	    rf_relation: Required-for relation being edited.
	    root: Root cluster used to list eligible relation targets.
	"""
	options, _ = db.cypher_query(
		f'''MATCH
    (f:Function {{uid: '{rf_relation.start_uid}'}}),
    (g:Function WHERE g.uid <> '{rf_relation.start_uid}')-[:PART_OF*]->(:Cluster {{uid: '{root.uid}'}})
WHERE
    NOT (g)<-[:SUBFUNCTION_OF]-(:Function) AND NOT (f)-[:REQUIRED_FOR]->(g)
 RETURN g''', resolve_objects=True)
	options_dict = dict() if rf_relation.end_uid is None else {rf_relation.end_uid: str(rf_relation.get_end_node().fqn)}
	ui.select({**options_dict, **{sf[0].uid: str(sf[0].fqn) for sf in options}}, label='Dependent function',
			  with_input=True).bind_value(rf_relation, 'end_uid')
	opm_values = _get_defined_opms(rf_relation.get_start_node(), rf_relation.get_end_node())
	ui.select(opm_values, label='Operating mode(s)', with_input=True, multiple=True).bind_value(rf_relation,
																								'operating_modes').props(
		'use-chips')
	ui.number('Weight', min=0., max=1., precision=2, step=.01).bind_value(rf_relation, 'weight')

def _get_defined_opms(f1: GFunction, f2: Optional[GFunction] = None) -> list[str]:
	"""Collect operating modes available for this relation.

	Args:
	    f1: First function in the required-for relation.
	    f2: Second function in the required-for relation.

	Returns:
	    Operating mode names attached to the selected functions.
	"""
	uids = [f1.uid]
	if f2 is not None:
		uids.append(f2.uid)
	result, _ = db.cypher_query(
		f'MATCH (n WHERE n.uid IN {uids})-[:PART_OF]->(:Cluster)(()-[:PART_OF]->()){{0,99}}(c:Cluster)<-[:PART_OF]-(o:OperatingMode) RETURN DISTINCT o',
		resolve_objects=True)
	return [om for r in result for om in r[0].operating_modes]


class RequiredForRelationCreatePage(FunctionalPage):
	"""Display the required for relation create editing page."""

	function: GFunction
	rf_relation: RequiredForRelation

	def __init__(self, function_id: str):
		"""Prepare a new required for relation and configure its editing actions.

		Args:
		    function_id: Identifier of the function to load.
		"""
		self.function = get_object_or_404(GFunction, uid=function_id)
		self.rf_relation = RequiredForRelation(self.function, end_node_type=GFunction)
		super().__init__(f'Add required_for to {self.function}', self.function, [
			Button('Discard', None, 'warning', lambda: goto(self.function)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable required for relation create fields and available actions."""
		requiredfor_relation_form(self.rf_relation, self.function.get_root())

	def _save(self):
		"""Save the required for relation create changes to the model."""
		self.rf_relation.save(self.function)


class RequiredForRelationUpdatePage(FunctionalPage):
	"""Display the required for relation update editing page."""

	function: GFunction
	rf_relation: RequiredForRelation

	def __init__(self, function_id: str, dep_function_id: str):
		"""Load the required for relation and configure its editing actions.

		Args:
		    function_id: Identifier of the function to load.
		    dep_function_id: Identifier of the dependent function.
		"""
		self.function = get_object_or_404(GFunction, uid=function_id)
		dep_function = get_object_or_404(GFunction, uid=dep_function_id)
		relation = get_relation_or_404(self.function, dep_function, 'required_for')
		self.rf_relation = RequiredForRelation(self.function, dep_function, weight=relation.weight,
											   operating_modes=relation.operating_modes)
		super().__init__(f'Update {relation}', self.function, [
			Button('Discard', None, 'warning', lambda: goto(self.function)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable required for relation update fields and available actions."""
		requiredfor_relation_form(self.rf_relation, self.function.get_root())

	def _save(self):
		"""Save the required for relation update changes to the model."""
		self.rf_relation.save(self.function)


# REQUIRED FOR RELATION REPAIR

class FormRequiredForRelation(RequiredForRelation):
	"""Represent an editable form required for relation."""

	def __init__(self, idx: int, start_node: GFunction, end_node: Optional[GFunction] = None,
	             weight: Optional[float] = None, operating_modes: Optional[list[str]] = None):
		"""Initialize form required for relation with its editable state.

		Args:
		    idx: Index of the relation in the editable list.
		    start_node: Source node of the relation.
		    end_node: Target node of the relation.
		    weight: Weight assigned to the relation.
		    operating_modes: Operating modes in which the relation applies.
		"""
		self.idx = idx
		super().__init__(start_node, end_node, weight=weight or 1, operating_modes=operating_modes)

	def __eq__(self, other):
		"""Compare this editable value with another value or name.

		Args:
		    other: Value to compare with this object.

		Returns:
		    Whether the compared values match.
		"""
		if isinstance(other, FormRequiredForRelation):
			return self.idx == other.idx
		return False


def add_rfr(rf_relations: list[FormRequiredForRelation], initial: FormRequiredForRelation):
	"""Append a required-for repair relation and refresh the table.

	Args:
	    rf_relations: Editable required-for repair relations.
	    initial: Whether to create the first repair relation.
	"""
	rf_relations.append(FormRequiredForRelation(max(r.idx for r in rf_relations) + 1, initial.get_original_start_node(),
												initial.get_original_end_node(), initial.weight,
												initial.operating_modes))
	repair_rfr_table.refresh()


def drop_rfr(rf_relations: list[FormRequiredForRelation], rf_relation: FormRequiredForRelation):
	"""Remove a required-for repair relation and refresh the table.

	Args:
	    rf_relations: Editable required-for repair relations.
	    rf_relation: Required-for relation being edited.
	"""
	rf_relations.remove(rf_relation)
	repair_rfr_table.refresh()


@ui.refreshable
def repair_rfr_table(rf_relations: list[FormRequiredForRelation], initial_relation: FormRequiredForRelation,
					 start_options: Optional[dict[str, str]] = None,
					 end_options: Optional[dict[str, str]] = None):
	"""Render editable required-for repair relation rows.

	Args:
	    rf_relations: Editable required-for repair relations.
	    initial_relation: Original required-for relation used for repair.
	    start_options: Available source nodes for the relation.
	    end_options: Available target nodes for the relation.
	"""
	for idx, rfr in enumerate(rf_relations):
		ui.label('Correction').classes('font-bold')
		if start_options:
			ui.select(start_options, label='Required function', with_input=True).bind_value(rfr, 'start_uid')
		else:
			ui.label(str(initial_relation.get_original_start_node().fqn))
		ui.label(' -> ')
		if end_options:
			ui.select(end_options, label='Dependent function', with_input=True).bind_value(rfr, 'end_uid')
		else:
			ui.label(str(initial_relation.get_original_end_node().fqn))
		ui.select(initial_relation.operating_modes, label='Operating mode(s)', with_input=True,
				  multiple=True).bind_value(rfr, 'operating_modes').props('use-chips')
		ui.number('Weight', min=0., max=1., step=.01).bind_value(rfr, 'weight')
		if idx > 0:
			ui.icon('delete', color='negative').on('click', lambda r=rfr: drop_rfr(rf_relations, r)).classes(
				'self-end cursor-pointer')
		else:
			ui.label()


def requiredfor_relation_repair_form(rf_relations: list[FormRequiredForRelation],
									 initial_relation: FormRequiredForRelation):
	"""Render editable repair relations and associated costs.

	Args:
	    rf_relations: Editable required-for repair relations.
	    initial_relation: Original required-for relation used for repair.
	"""
	q: str = '''MATCH (:Function {{uid: \'{}\'}})(()<-[:SUBFUNCTION_OF]-()){{1,99}}(f:Function) 
WHERE NOT (f)<-[:SUBFUNCTION_OF]-(:Function)
RETURN f'''
	start_node: GFunction = initial_relation.get_start_node()
	end_node: GFunction = initial_relation.get_end_node()
	start_options = end_options = None
	if start_node.has_subfunctions:
		start_options, _ = db.cypher_query(q.format(initial_relation.start_uid), resolve_objects=True)
		start_options = {f[0].uid: str(f[0].fqn) for f in start_options}
	if end_node.has_subfunctions:
		end_options, _ = db.cypher_query(q.format(initial_relation.end_uid), resolve_objects=True)
		end_options = {f[0].uid: str(f[0].fqn) for f in end_options}
	with ui.grid(columns='auto 1fr auto 1fr auto auto auto').classes('w-full vertical-bottom'):
		ui.label('Invalid').classes('font-bold')
		ui.label(str(start_node.fqn))
		ui.label(' -> ')
		ui.label(str(end_node.fqn))
		ui.label(' | '.join(initial_relation.operating_modes))
		ui.label(str(initial_relation.weight))
		ui.icon('add', color='primary').on('click', lambda: add_rfr(rf_relations, initial_relation)).classes(
			'cursor-pointer')
		repair_rfr_table(rf_relations, initial_relation, start_options, end_options)


class RequiredForRelationRepairPage(FunctionalPage):
	"""Display the required for relation repair editing page."""

	function: GFunction
	rf_relation: FormRequiredForRelation
	rf_relations: list[FormRequiredForRelation]

	def __init__(self, function_id: str, dep_function_id: str):
		"""Load the required for relation repair and configure its available actions.

		Args:
		    function_id: Identifier of the function to load.
		    dep_function_id: Identifier of the dependent function.
		"""
		self.function = get_object_or_404(GFunction, uid=function_id)
		dep_function = get_object_or_404(GFunction, uid=dep_function_id)
		relation: RequiredForRelation = get_relation_or_404(self.function, dep_function, 'required_for')
		self.rf_relation = FormRequiredForRelation(0, self.function, dep_function, relation.weight, relation.operating_modes)
		self.rf_relations = [self.rf_relation]
		super().__init__(f'Repair {relation}', self.function, [
			Button('Discard', None, 'warning', lambda: goto(self.function)),
			Button('Save', 'save', None, lambda: self._save)
		])

	def _show_content(self):
		"""Render editable required for relation repair fields and available actions."""
		requiredfor_relation_repair_form(self.rf_relations, self.rf_relation)

	def _save(self):
		"""Save the required for relation repair changes to the model."""
		for r in self.rf_relations:
			r.save()
		goto(self.function)


# OBSERVED BY RELATION

def observes_relation_form(o_relation: ObservesRelation):
	"""Render the observed node and relation weight controls.

	Args:
	    o_relation: Observes relation being edited.
	"""
	options, _ = db.cypher_query(
		f'''MATCH
    (f:Function {{uid: '{o_relation.start_uid}'}})-[:PART_OF]->(:Cluster)(()-[:PART_OF]->()){{0,99}}(:Cluster)<-[PART_OF]-(o:DirectObservable)
WHERE
    NOT (f)-[:OBSERVED_BY]->(o)
 RETURN o''', resolve_objects=True)
	options_dict = dict() if o_relation.end_uid is None else {o_relation.end_uid: str(o_relation.get_end_node().fqn)}
	ui.select({**options_dict, **{sf[0].uid: str(sf[0].fqn) for sf in options}}, label='Observer',
			  with_input=True).bind_value(o_relation, 'end_uid')
	ui.number('Weight', min=0., max=1., precision=2, step=.01).bind_value(o_relation, 'weight')


class ObservesRelationCreatePage(FunctionalPage):
	"""Display the observes relation create editing page."""

	function: GFunction
	o_relation: ObservesRelation
	
	def __init__(self, function_id: str):
		"""Prepare a new observes relation and configure its editing actions.

		Args:
		    function_id: Identifier of the function to load.
		"""
		self.function = get_object_or_404(GFunction, uid=function_id)
		self.o_relation = ObservesRelation(self.function, end_node_type=GDirectObservable)
		super().__init__(f'Add observed_by to {self.function}', self.function, [
			Button('Discard', None, 'warning', lambda: goto(self.function)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable observes relation create fields and available actions."""
		observes_relation_form(self.o_relation)

	def _save(self):
		"""Save the observes relation create changes to the model."""
		self.o_relation.save(self.function)
		

class ObservesRelationUpdatePage(FunctionalPage):
	"""Display the observes relation update editing page."""

	function: GFunction
	o_relation: ObservesRelation

	def __init__(self, function_id: str, observable_id: str):
		"""Load the observes relation and configure its editing actions.

		Args:
		    function_id: Identifier of the function to load.
		    observable_id: Identifier of the observable to load.
		"""
		self.function = get_object_or_404(GFunction, uid=function_id)
		observable = get_object_or_404(GDirectObservable, uid=observable_id)
		relation = get_relation_or_404(self.function, observable, 'observed_by')
		self.o_relation = ObservesRelation(self.function, observable, weight=relation.weight)
		super().__init__(f'Update {relation}', self.function, [
			Button('Discard', None, 'warning', lambda: goto(self.function)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable observes relation update fields and available actions."""
		observes_relation_form(self.o_relation)

	def _save(self):
		"""Save the observes relation update changes to the model."""
		self.o_relation.save(self.function)


# TESTED BY RELATION

def tests_relation_form(t_relation: TestsRelation):
	"""Render the tested node and relation weight controls.

	Args:
	    t_relation: Tests relation being edited.
	"""
	options, _ = db.cypher_query(
		f'''MATCH
    (f:Function {{uid: '{t_relation.start_uid}'}})-[:PART_OF]->(:Cluster)(()-[:PART_OF]->()){{0,99}}(:Cluster)<-[PART_OF]-(t:DiagnosticTest)
WHERE
    NOT (f)-[:TESTED_BY]->(t)
 RETURN t''', resolve_objects=True)
	options_dict = dict() if t_relation.end_uid is None else {t_relation.end_uid: str(t_relation.get_end_node().fqn)}
	ui.select({**options_dict, **{sf[0].uid: str(sf[0].fqn) for sf in options}}, label='Diagnostic test',
			  with_input=True).bind_value(t_relation, 'end_uid')
	ui.number('Weight', min=0., max=1., precision=2, step=.01).bind_value(t_relation, 'weight')


class TestsRelationCreatePage(FunctionalPage):
	"""Display the tests relation create editing page."""

	function: GFunction
	t_relation: TestsRelation

	def __init__(self, function_id: str):
		"""Prepare a new tests relation and configure its editing actions.

		Args:
		    function_id: Identifier of the function to load.
		"""
		self.function = get_object_or_404(GFunction, uid=function_id)
		self.t_relation = TestsRelation(self.function, end_node_type=GDiagnosticTest)
		super().__init__(f'Add tested_by to {self.function}', self.function, [
			Button('Discard', None, 'warning', lambda: goto(self.function)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable tests relation create fields and available actions."""
		tests_relation_form(self.t_relation)

	def _save(self):
		"""Save the tests relation create changes to the model."""
		self.t_relation.save(self.function)


class TestsRelationUpdatePage(FunctionalPage):
	"""Display the tests relation update editing page."""

	function: GFunction
	t_relation: TestsRelation

	def __init__(self, function_id: str, test_id: str):
		"""Load the tests relation and configure its editing actions.

		Args:
		    function_id: Identifier of the function to load.
		    test_id: Identifier of the diagnostic test to load.
		"""
		self.function = get_object_or_404(GFunction, uid=function_id)
		test = get_object_or_404(GDiagnosticTest, uid=test_id)
		relation = get_relation_or_404(self.function, test, 'tested_by')
		self.t_relation = TestsRelation(self.function, test, weight=relation.weight)
		super().__init__(f'Update {relation}', self.function, [
			Button('Discard', None, 'warning', lambda: goto(self.function)),
			Button('Save', 'save', None, self._save)
		])

	def _show_content(self):
		"""Render editable tests relation update fields and available actions."""
		tests_relation_form(self.t_relation)

	def _save(self):
		"""Save the tests relation update changes to the model."""
		self.t_relation.save(self.function)


class FunctionCPTPage(CPTPage):
	"""Display the function CPT probability table editor."""

	def __init__(self, function_id: str):
		"""Load the function cpt and configure its available actions.

		Args:
		    function_id: Identifier of the function to load.
		"""
		editor_mode = self.get_mode() == 'Editor'
		super().__init__(GFunction, function_id, lambda f: f if editor_mode else f.get_root())
