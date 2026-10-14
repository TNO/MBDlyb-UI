# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
import io
import os
import shutil
import tempfile
from multiprocessing import Manager, Queue
from pathlib import Path
from typing import Optional, Callable
from zipfile import ZipFile

import pandas as pd
from mbdlyb.gdb import cls, GMBDNet
from mbdlyb.cpt import CPT
from mbdlyb_ui import Button, Table, TableColumn, TableMultiColumn
from mbdlyb_ui.dialogs import confirm, confirm_delete
from mbdlyb_ui.mermaid import MermaidBuilder
from mbdlyb_ui.helpers import (goto, get_object_or_404, save_object, download_graph, download_bayesnet,
							   download_cpt as base_download_cpt, get_url)
from neomodel import db
from nicegui import app, ui, events, run

from mbdlyb.functional.config import COLOR_MAP, LABEL_MAP
from mbdlyb.functional.gdb import (GFunctionalNode, GCluster, GFunction, GHardware, update_name, CLASS_ICONS,
								   GCPTEnabledNode)
from .base import FunctionalPage
from .config import MERMAID_ATTRIBUTES
from .helpers import save_new_object, RequiredForRelation
from .validation import base_name_validation


# HELPERS METHODS

def download_cpt(node: GCPTEnabledNode):
	"""Download the node's conditional probability table as a spreadsheet.

	Args:
	    node: CPT-enabled node whose table is downloaded.
	"""
	cpt, _ = CPT.from_dict(node, node.cpt)
	base_download_cpt(cpt, str(node.fqn))

def download_cpts(cluster: GCluster, only_required: bool = True):
	"""Package the cluster's conditional probability tables into a ZIP download.

	Args:
	    cluster: Cluster whose descendant CPTs are packaged for download.
	    only_required: Whether to include only nodes needing or defining a CPT.
	"""
	node_cpts = collect_cpts(cluster, only_required)
	zip_buffer = io.BytesIO()
	with ZipFile(zip_buffer, mode='w') as zip_file:
		for node, cpt in node_cpts.items():
			with zip_file.open(f'{node.fqn}.xlsx', mode='w') as buffer:
				with pd.ExcelWriter(buffer) as writer:
					cpt.to_df().to_excel(writer, sheet_name='CPT')
	ui.download.content(zip_buffer.getvalue(), f'{cluster.name}_cpts.zip', media_type='application/zip')

def collect_cpts(cluster: GCluster, only_required: bool = True) -> dict[GFunctionalNode, CPT]:
	"""Collect conditional probability tables recursively from a cluster.

	Args:
	    cluster: Cluster to search recursively for eligible CPT nodes.
	    only_required: Whether to include only nodes needing or defining a CPT.

	Returns:
	    Mapping of eligible nodes to their conditional probability tables.
	"""
	cpt_nodes: dict[GFunctionalNode, CPT] = dict()
	for element in cluster.elements.order_by('name'):
		if isinstance(element, GCluster):
			cpt_nodes.update(collect_cpts(element, only_required))
		elif isinstance(element, GCPTEnabledNode) and (not only_required or (element.has_cpt or element.requires_cpt)):
			cpt_nodes[element], _ = CPT.from_dict(element, element.cpt)
	return cpt_nodes

def copy_cluster(obj) -> None:
	"""Ask for confirmation before cloning a cluster and its relations.

	Args:
	    obj: Cluster whose graph and relations are cloned after confirmation.
	"""
	def _copy():
		"""Clone the cluster subgraph in the database, rename the copy, and navigate to it."""
		if obj.at_root:
			query = f"""
				MATCH p = (c: Cluster {{uid: '{obj.uid}'}})<-[:PART_OF*]-(m)-[r]-(l)
				WHERE (l)-[:PART_OF*]->(c) AND type(r) <> 'PART_OF'
				WITH c, collect(p) as paths
				CALL apoc.refactor.cloneSubgraphFromPaths(paths) YIELD output
				WITH c, collect(DISTINCT output) AS outputs

				FOREACH (n IN outputs | SET n.uid = randomUUID())
				WITH c, outputs

				MATCH (copy: Cluster)
				WHERE copy.fqn = c.fqn AND copy IN outputs
				RETURN DISTINCT copy
				"""
		else:
			query = f"""
				MATCH p = (root)<-[:PART_OF]-(c: Cluster {{uid: '{obj.uid}'}})<-[:PART_OF*]-(m)-[r]-(l)
				WHERE (l)-[:PART_OF*]->(c) AND type(r) <> 'PART_OF'
				WITH root, c, collect(p) as paths
				CALL apoc.refactor.cloneSubgraphFromPaths(paths, {{standinNodes: [[root, root]]}}) YIELD output
				WITH c, collect(DISTINCT output) AS outputs

				FOREACH (n IN outputs | SET n.uid = randomUUID())
				WITH c, outputs

				MATCH (copy: Cluster)
				WHERE copy.fqn = c.fqn AND copy IN outputs
				RETURN DISTINCT copy
				"""
		copy, _ = db.cypher_query(query, resolve_objects=True)
		cluster = copy[0][0]

		update_name(cluster)
		goto(cluster)

	confirm('Copy Cluster',
		 f'Do you want to copy {type(obj).__name__} {obj}?',
		 'Yes', _copy, 'negative')


def move_cluster(obj) -> None:
	"""Offer eligible parent clusters and move the selected cluster on confirmation.

	Args:
	    obj: Cluster whose parent can be changed.
	"""
	def _move(obj, trgt_fqn):
		"""Replace the cluster's parent relation and remove invalid subfunction links.

		Args:
		    obj: Cluster to relocate under the selected parent.
		    trgt_fqn: Fully qualified name of the destination cluster.
		"""
		trgt = get_object_or_404(GCluster, fqn=trgt_fqn)

		query = f"""
			MATCH (m: Cluster {{uid: '{obj.uid}'}})
			OPTIONAL MATCH (m)-[r:PART_OF]->(t:Cluster)
			DELETE r
			WITH m

			MATCH (t:Cluster {{uid: '{trgt.uid}'}})
			CREATE (m)-[:PART_OF]->(t)
			WITH m, t

			OPTIONAL MATCH (m)<-[:PART_OF]-(f:Function)-[r:SUBFUNCTION_OF]->(f2:Function)-[:PART_OF]->(o: Cluster)
			WHERE o.uid <> m.uid
			DELETE r
			RETURN m
			"""
		db.cypher_query(query)

		update_name(obj)
		goto(obj)

	def _on_cancel():
		"""Close and clear the cluster move dialog."""
		dialog.close()
		dialog.clear()

	def _on_confirm(obj, trgt_fqn):
		"""Move the cluster to the chosen parent and close the dialog.

		Args:
		    obj: Cluster to move when the dialog is confirmed.
		    trgt_fqn: Fully qualified name of the destination cluster.
		"""
		_move(obj, trgt_fqn)
		_on_cancel()

	query = f"""
		MATCH (c:Cluster)-[:PART_OF*1..]->(root:Cluster)
		MATCH (move:Cluster {{uid: '{obj.uid}'}})-[:PART_OF*1..]->(root)
		WHERE NOT (c)-[:PART_OF*]->(move)
		AND NOT (root)-->()
		AND c.uid <> move.uid
		RETURN DISTINCT c.fqn, root.fqn
		"""
	clusters, _ = db.cypher_query(query, resolve_objects=True)
	clusters = sorted([c[0] for c in clusters] + [clusters[0][1]])

	with ui.dialog(value=True) as dialog, ui.card():
		ui.label('Move Cluster').classes('text-h6')
		ui.label(f'Where do you want to move {type(obj).__name__} {obj} to?',)
		select = ui.select(clusters, with_input=True, label="Cluster").classes('w-60')
		with ui.row():
			ui.button('Cancel', color='secondary', on_click=_on_cancel).props('outline')
			ui.button('Move', color='negative', on_click=lambda: _on_confirm(obj, select.value))
		dialog.on('close', dialog.clear)


# CLUSTER METHODS

class ClusterProps:
	"""Hold editable cluster form state."""

	DEFAULT_FUNCTION_NAME = 'MainFunction'

	def __init__(self, add_hw: bool, add_fn: bool):
		"""Initialize cluster props with its editable state.

		Args:
		    add_hw: Whether to create default hardware.
		    add_fn: Whether to create a default function.
		"""
		self.add_hw = add_hw
		self.hw_name: str = ''
		self.add_fn = add_fn
		self.fn_name: str = ''


def cluster_form(cluster: GCluster, props: Optional[ClusterProps] = None, parent: Optional[GCluster] = None,
                 update: bool = True):
	"""Render the cluster name and optional default hardware and function controls.

	Args:
	    cluster: Cluster whose name is edited in the form.
	    props: Options for adding default function and hardware to a new cluster.
	    parent: Optional parent cluster for the new cluster.
	    update: Whether to edit an existing cluster instead of creating one.
	"""
	cluster_input = ui.input('Name', validation=base_name_validation(parent, cluster if update else None)) \
		.bind_value(cluster, 'name').props('hide-bottom-space')
	if not update:
		if parent is not None:
			hw_check = ui.checkbox('Add default hardware?').bind_value(props, 'add_hw')
			hw_input = ui.input('Hardware name', validation=base_name_validation(allow_empty=True),
					   placeholder='Leave empty to use cluster name').bind_visibility_from(
						   props, 'add_hw').bind_value(props, 'hw_name').props('hide-bottom-space')
		else:
			hw_input = None
		fn_check = ui.checkbox('Add default function?').bind_value(props, 'add_fn')
		fn_input = ui.input('Function name', validation=base_name_validation(allow_empty=True),
					  placeholder='Leave empty to use \'' + ClusterProps.DEFAULT_FUNCTION_NAME + '\'').bind_visibility_from(
						  props, 'add_fn').bind_value(props, 'fn_name').props('hide-bottom-space')
		if hw_input is not None:
			hw_input.validation['Hardware and Function must have different names'] = \
				lambda s: not props.add_fn or (s != fn_input.value if fn_input.value else s != ClusterProps.DEFAULT_FUNCTION_NAME)
			fn_input.validation['Hardware and Function must have different names'] = \
				lambda s: not props.add_hw or (s != hw_input.value if hw_input.value else s != cluster_input.value)
			cluster_input.on_value_change(fn_input.validate)
			hw_input.on_value_change(fn_input.validate)
			fn_input.on_value_change(hw_input.validate)
			hw_check.on_value_change(fn_input.validate)
			hw_check.on_value_change(hw_input.validate)
			fn_check.on_value_change(fn_input.validate)
			fn_check.on_value_change(hw_input.validate)
		if parent is not None:
			ui.label(
				'If both default hardware and function are added, a realizes relation between them will automatically be created.')


class ClusterCreatePage(FunctionalPage):
	"""Display the cluster create editing page."""

	cluster: GCluster
	props: ClusterProps

	def __init__(self, parent_cluster_id: Optional[str] = None):
		"""Prepare a new cluster and configure its editing actions.

		Args:
		    parent_cluster_id: Identifier of the parent cluster.
		"""
		parent_cluster = get_object_or_404(cls(GMBDNet), uid=parent_cluster_id) if parent_cluster_id else None
		self.cluster = cls(GCluster)(name='')
		self.props = ClusterProps(False, False)
		title = 'New cluster'
		if parent_cluster is not None:
			title += f' in {parent_cluster.fqn}'
			self.props.add_hw = True
			self.props.add_fn = True
		super().__init__(title, parent_cluster, [
			Button('Discard', None, 'warning', lambda: goto('/' if parent_cluster is None else parent_cluster)),
			Button('Save', 'save', None, self._save_cluster)
		])

	@property
	def parent_cluster(self) -> Optional[GCluster]:
		"""Return the selected parent cluster.

		Returns:
		    Selected parent cluster.
		"""
		return self._selected_element

	def _show_content(self):
		"""Render editable cluster create fields and available actions."""
		cluster_form(self.cluster, self.props, self.parent_cluster, False)

	def _save_cluster(self):
		"""Persist the new cluster and any requested default elements."""
		save_object(self.cluster)
		if self.parent_cluster is not None:
			self.cluster.set_net(self.parent_cluster)
			self.cluster.update_fqn()
		hw = None
		if self.props.add_hw:
			hw = cls(GHardware)(name=self.props.hw_name if self.props.hw_name else self.cluster.name)
			save_new_object(hw, self.cluster, True)
		if self.props.add_fn:
			fn = cls(GFunction)(name=self.props.fn_name if self.props.fn_name else ClusterProps.DEFAULT_FUNCTION_NAME)
			save_new_object(fn, self.cluster, True)
			if hw is not None:
				hw.realizes.connect(fn)
		goto(self.cluster if self.parent_cluster is None else self.parent_cluster)


class ClusterUpdatePage(FunctionalPage):
	"""Display the cluster update editing page."""

	def __init__(self, cluster_id: str):
		"""Load the cluster and configure its editing actions.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		cluster = get_object_or_404(GCluster, uid=cluster_id)
		super().__init__(f'Update {cluster}', cluster, [
			Button('Discard', None, 'warning', lambda: goto(cluster)),
			Button('Save', 'save', None, lambda: save_object(cluster, cluster))
		])

	def _show_content(self):
		"""Render editable cluster update fields and available actions."""
		cluster_form(self.element)


class ClusterDetailPage(FunctionalPage):
	"""Display the cluster detail properties and relations."""

	cluster: GCluster
	mmb: MermaidBuilder

	def __init__(self, cluster_id: str):
		"""Load the cluster detail and configure its available actions.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		self.cluster: GCluster = get_object_or_404(GCluster, uid=cluster_id)
		self.mmb = MermaidBuilder(self.cluster, MERMAID_ATTRIBUTES, COLOR_MAP, LABEL_MAP)
		super().__init__(f'Cluster {self.cluster.name}', self.cluster, self._build_buttons())

	def _show_content(self):
		"""Display cluster detail properties, relations, and navigation actions."""
		if self.get_mode() == 'Tree':
			self._show_content_tree()
		elif self.get_mode() == 'Editor':
			self._show_content_editor()

	def _show_content_tree(self):
		"""Render the cluster hierarchy and selected node details."""
		ui.separator()
		with ui.grid(columns='3fr 2fr').classes('w-full divide-x gap-0'):
			with ui.row().classes('w-full pr-4'):
				_build_tree_row(self.cluster, True)
			with ui.row().classes('w-full pl-4'):
				show_node_details()

	def _show_content_editor(self):
		"""Render the editable cluster overview and its elements."""
		cluster = self.cluster
		with ui.column().classes('w-full'):
			with ui.card().classes('w-full') as card:
				card.bind_visibility_from(app.storage.general, 'show_diagrams')
				with ui.context_menu():
					save_button = ui.menu_item('Save')
				self.mmb.draw_mermaid_diagram(save_button)
				ui.on('show_diagram', lambda: self.mmb.draw_mermaid_diagram.refresh(save_button))
			with ui.card().classes('w-full'):
				Table('Functions', cluster.functions.order_by('name'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableMultiColumn('Subfunctions', 'name', get_url, 'fqn', 'subfunctions'),
					TableMultiColumn('Required for', 'name', get_url, 'fqn', 'required_for'),
					TableMultiColumn('Observed by', 'name', get_url, 'fqn', 'observed_by'),
					TableMultiColumn('Indicated by', 'name', get_url, 'fqn', 'indicated_by')
				], cluster, [
						  Button(icon='add', color='positive', tooltip='Add function',
								 handler=f'{get_url(cluster)}/function/new')
					  ], [
						  Button(icon='border_all', color='secondary', tooltip='Modify CPT for {}',
								 handler=lambda f: goto(f'{get_url(f)}/cpt')),
						  Button(icon='edit', tooltip='Edit {}', handler=lambda f: goto(f'{get_url(f)}/update')),
						  Button(icon='delete', color='negative', tooltip='Delete {}',
								 handler=lambda f: confirm_delete(f, cluster))
					  ]).show()
			if not cluster.at_root:
				with ui.card().classes('w-full'):
					Table('Hardware', cluster.hardware.order_by('name'), [
						TableColumn('Name', 'name', get_url, 'fqn'),
						TableColumn('Faults',
									lambda h: ' | '.join([f'{key}: {value}' for key, value in h.fault_rates.items()])),
						TableMultiColumn('Realizes', 'name', get_url, 'fqn', 'realizes'),
						TableMultiColumn('Observed by', 'name', get_url, 'fqn', 'observed_by'),
						TableMultiColumn('Indicated by', 'name', get_url, 'fqn', 'indicated_by'),
					], cluster, [
							  Button(icon='add', color='positive', tooltip='Add hardware',
									 handler=f'{get_url(cluster)}/hardware/new')
						  ], [
							  Button(icon='edit', tooltip='Edit {}', handler=lambda x: goto(f'{get_url(x)}/update')),
							  Button(icon='delete', color='negative', tooltip='Delete {}',
									 handler=lambda x: confirm_delete(x, cluster))
						  ]).show()
			with ui.card().classes('w-full'):
				Table('Clusters', cluster.subnets.order_by('name'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableMultiColumn('Functions', 'name', get_url, 'fqn', 'functions'),
					TableMultiColumn('Hardware', 'name', get_url, 'fqn', 'hardware'),
					TableMultiColumn('Observables', 'name', get_url, 'fqn', 'observables'),
					TableMultiColumn('Diagnostic tests', 'name', get_url, 'fqn', 'tests')
				], cluster, [
						  Button(icon='add', color='positive', tooltip='Add cluster', handler=f'{get_url(cluster)}/new')
					  ]).show()
			with ui.card().classes('w-full'):
				Table('Observables', cluster.observables.order_by('name'), [
					TableColumn('Name', 'name', get_url, tooltip='fqn'),
					TableColumn('FPR', 'fp_rate'),
					TableColumn('FNR', 'fn_rate'),
					TableMultiColumn('Observed functions', 'name', get_url, 'fqn', 'observed_functions'),
					TableMultiColumn('Observed hardware', 'name', get_url, 'fqn', 'observed_hardware')
				], cluster, [
						  Button(icon='add', color='positive', tooltip='Add observable',
								 handler=f'{get_url(cluster)}/observable/new')
					  ], [
						  Button(icon='border_all', color='secondary', tooltip='Update CPT of {}',
								 handler=lambda x: goto(f'{get_url(x)}/cpt')),
						  Button(icon='edit', tooltip='Edit {}', handler=lambda x: goto(f'{get_url(x)}/update')),
						  Button(icon='delete', color='negative', tooltip='Delete {}',
								 handler=lambda x: confirm_delete(x, cluster))
					  ]).show()
			with ui.card().classes('w-full'):
				Table('Diagnostic tests', cluster.tests.order_by('name'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableColumn('Costs', lambda t: f'{sum(t.fixed_cost.values())} ({", ".join(t.fixed_cost.keys())})'),
					TableMultiColumn('Results',
									 lambda r: f'{r.name} ({", ".join(o.name for o in r.get_observed_nodes())})',
									 list_attribute='test_results')
				], cluster, [
						  Button(icon='add', color='positive', tooltip='Add diagnostic test',
								 handler=f'{get_url(cluster)}/test/new')
					  ], [
						  Button(icon='edit', tooltip='Edit {}', handler=lambda t: goto(f'{get_url(t)}/update')),
						  Button(icon='delete', color='negative', tooltip='Delete {}',
								 handler=lambda t: confirm_delete(t, cluster))
					  ]).show()
			with ui.card().classes('w-full'):
				Table('Operating mode selectors', cluster.operating_modes.order_by('name'), [
					TableColumn('Name', 'name', get_url, 'fqn'),
					TableMultiColumn('Modes', lambda x: x, list_attribute='operating_modes')
				], cluster, [
						  Button(icon='add', color='positive', tooltip='Add operating mode',
								 handler=f'{get_url(cluster)}/opm/new')
					  ], [
						  Button(icon='edit', tooltip='Edit {}', handler=lambda x: goto(f'{get_url(x)}/update')),
						  Button(icon='delete', color='negative', tooltip='Delete {}',
								 handler=lambda x: confirm_delete(x, cluster))
					  ]).show()

	def _build_buttons(self) -> list[list | Button]:
		"""Assemble actions available for this cluster.

		Returns:
		    Actions to display for the cluster.
		"""
		buttons = [
			[Button(None, 'checklist', 'secondary', lambda: goto(f'{get_url(self.cluster)}/validator'), 'Check model')]]
		if self.cluster.at_root:
			buttons[0] = [Button(None, 'play_circle', 'positive', lambda: goto(f'{get_url(self.cluster)}/diagnoser'),
								 'Diagnoser'),
						  Button(None, 'design_services', 'positive',
								 lambda: goto(f'{get_url(self.cluster)}/design_for_diagnostics'),
								 'Design for diagnostics')] + buttons[0]
		buttons.extend([[
			Button(None, 'account_tree', 'secondary', lambda: download_graph(self.cluster, COLOR_MAP), 'Download graph'),
			Button(None, 'developer_board', 'secondary', lambda: download_bayesnet(self.cluster, colormap=COLOR_MAP), 'Download Bayesnet')
		]])
		if self.get_mode() == 'Tree':
			return buttons + self._build_buttons_tree(self.cluster)
		elif self.get_mode() == 'Editor':
			return buttons + self._build_buttons_editor(self.cluster)
		return buttons

	@staticmethod
	def _build_buttons_tree(cluster: GCluster) -> list[list | Button]:
		"""Assemble actions for a cluster in tree mode.

		Args:
		    cluster: Cluster for which tree-mode actions are assembled.

		Returns:
		    Actions to display for the cluster.
		"""
		return [[
			Button(None, 'table_view', 'secondary', lambda: download_cpts(cluster, False), 'Download all CPTs'),
			Button(None, 'backup_table', 'secondary', lambda: download_cpts(cluster),
				   'Download required and existing CPTs'),
			Button(None, 'add_to_photos', 'secondary', lambda: goto(f'{get_url(cluster)}/import_cpt'),
				   'Import CPT')
		],
			Button(None, 'delete', 'negative', lambda: confirm_delete(cluster, '/'), 'Delete cluster')
		]

	@staticmethod
	def _build_buttons_editor(cluster: GCluster) -> list[list | Button]:
		"""Assemble editing actions for a cluster.

		Args:
		    cluster: Cluster for which editor actions are assembled.

		Returns:
		    Actions to display for the cluster.
		"""
		buttons = [[
			Button(None, 'upload_file', 'secondary', lambda: goto(f'{get_url(cluster)}/import'), 'Import cluster'),
			Button(None, 'table_view', 'secondary', lambda: download_cpts(cluster, False), 'Download all CPTs'),
			Button(None, 'backup_table', 'secondary', lambda: download_cpts(cluster),
				   'Download required and existing CPTs'),
			Button(None, 'add_to_photos', 'secondary', lambda: goto(f'{get_url(cluster)}/import_cpt'),
				   'Import CPT')
		]]
		transfer_buttons = [Button(None, 'content_copy', 'secondary', lambda: copy_cluster(cluster), 'Copy cluster')]
		if not cluster.at_root:
			transfer_buttons.append(
				Button(None, 'trending_flat', 'secondary', lambda: move_cluster(cluster), 'Move cluster'))
		buttons.append(transfer_buttons)
		buttons.append([
			Button(None, 'table_view', 'secondary', lambda: goto(f'{get_url(cluster)}/requiredfor'), 'View table'),
			Button(None, 'edit', None, lambda: goto(f'{get_url(cluster)}/update'), 'Edit cluster'),
			Button(None, 'delete', 'negative',
				   lambda: confirm_delete(cluster, '/' if cluster.at_root else get_url(cluster.get_net())),
				   'Delete cluster')
		])
		return buttons


_ICON_OPEN = 'keyboard_arrow_down'
_ICON_CLOSED = 'chevron_right'

def _build_tree_row(node: GFunctionalNode | GCluster, visible: bool = False):
	"""Render a cluster tree row and its node status badges.

	Args:
	    node: Cluster or functional node shown in the tree row.
	    visible: Whether this tree row is visible.
	"""
	is_cluster = isinstance(node, GCluster)
	with ui.row().classes('w-full gap-0 divide-y'):
		with ui.row().classes('w-full items-center py-2'):
			if is_cluster:
				icon = ui.icon(_ICON_OPEN if visible else _ICON_CLOSED).classes('cursor-pointer').on('click', lambda
					e: e.sender.set_name(_ICON_OPEN if e.sender.name == _ICON_CLOSED else _ICON_CLOSED))
			else:
				ui.icon(CLASS_ICONS.get(node.__class__, 'question_mark'), color=COLOR_MAP.get_color(node)).tooltip(
					node.__class__.__name__)
			ui.button(node.name, color='standard', on_click=lambda n=node: show_node_details.refresh(n)).props(
				'flat dense sm no-caps').classes('text-weight-medium' if is_cluster else 'text-weight-regular')
			ui.space()
			if not is_cluster and node.requires_cpt:
				ui.icon('grid_on', color='positive' if node.has_cpt else 'negative').classes('cursor-pointer').on(
					'click', lambda n=node: show_node_details.refresh(n))
		if is_cluster:
			with ui.row().classes('w-full ml-4 divide-y gap-0') as content_block:
				for child in list(node.subnets.order_by('name')) + list(node.mbdnodes.order_by('name')):
					_build_tree_row(child)
				content_block.bind_visibility_from(icon, 'name', backward=lambda n: n == _ICON_OPEN)

@ui.refreshable
def show_node_details(node: Optional[GFunctionalNode | GCluster] = None):
	"""Render details and actions for the selected functional node.

	Args:
	    node: Selected tree node whose details are displayed.
	"""
	if node is None:
		ui.label('Select a node to view its details.')
		return
	with ui.row().classes('w-full justify-between items-start'):
		with ui.column():
			color = COLOR_MAP.get_color(node)
			if color == '#000000':
				color = '#CCCCCC'
			ui.chip(node.__class__.__name__, icon=CLASS_ICONS.get(node.__class__, 'question_mark'), color=color)
			ui.label(node.name).classes('text-h5')
			ui.label(str(node.fqn)).classes('text-grey')
			if isinstance(node, GFunctionalNode) and node.states:
				ui.label(
					f'States: {", ".join((f"{k} ({v})" for k, v in node.priors.items()) if isinstance(node, GHardware) else node.states)}')
		with ui.column():
			if isinstance(node, GCPTEnabledNode):
				with ui.button_group().props('flat'):
					ui.button(icon='table_view', color='secondary', on_click=lambda: download_cpt(node)).tooltip(
						'Download CPT').props('outline')
					with ui.button(icon='grid_on', on_click=lambda n=node: goto(n.cpt_url)).tooltip(
							'Modify CPT').props('outline'):
						if node.requires_cpt:
							ui.badge('!', color='positive' if node.has_cpt else 'negative').props('floating')


# REQUIRED_FOR RELATION TABLE

class RequiredForTablePage(FunctionalPage):
	"""Display the required for table relation table."""

	cluster: GCluster
	functions: list[GFunction]

	def __init__(self, cluster_id: str):
		"""Load the required for table and configure its available actions.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		self.cluster = get_object_or_404(GCluster, uid=cluster_id)
		self.functions, _ = db.cypher_query(f'''MATCH
			(f:Function)-[:PART_OF]->(:Cluster)(()-[:PART_OF]->()){{1,1}}(:Cluster {{uid: '{self.cluster.uid}'}})
		RETURN f
		ORDER BY f.fqn''', resolve_objects=True)
		super().__init__(f'RequiredFor relations of cluster {self.cluster.fqn}', self.cluster, [
			Button('Close', None, None, lambda: goto(self.cluster))
		])

	def _show_content(self):
		"""Display required for table rows and their editing controls."""
		with ui.grid(columns=len(self.functions) + 1).classes('gap-0'):
			ui.label()
			for f in self.functions:
				ui.link(f[0].name, get_url(f[0])).classes('border p-1 font-bold').tooltip(str(f[0].fqn))
			for f in self.functions:
				ui.link(f[0].name, get_url(f[0])).classes('border p-1 font-bold').tooltip(str(f[0].fqn))
				for g in self.functions:
					eligable_for_relation = f[0] != g[0]
					needs_repair = f[0].has_subfunctions or g[0].has_subfunctions
					relation = f[0].required_for.relationship(g[0])
					disabled = False
					color = None
					classes = ''
					props = ''
					on_click: Optional[Callable] = None
					if eligable_for_relation and relation is not None:
						if needs_repair:
							icon, color = 'construction', 'warning'
							on_click = lambda x=f[0], y=g[0]: goto(f'{get_url(x)}/requiredfor/{y.uid}/repair')
						else:
							icon, color = 'edit', 'positive'
							on_click = lambda x=f[0], y=g[0]: goto(f'{get_url(x)}/requiredfor/{y.uid}/update')
					elif eligable_for_relation and not needs_repair:
						icon, classes, props = 'add_circle', 'flat', 'text-color=primary'
						on_click = lambda x=f[0], y=g[0]: self._create_new_rf_rel(x, y)
					else:
						icon, disabled = 'do_not_disturb_on', True
					btn = ui.button(icon=icon, color=color).tooltip(f'{f[0].fqn} -> {g[0].fqn}')
					if classes:
						btn.classes(classes)
					if props:
						btn.props(props)
					if disabled:
						btn.disable()
					elif on_click is not None:
						btn.on_click(on_click)

	def _create_new_rf_rel(self, x: GFunction, y: GFunction):
		"""Save a required-for relation between two functions.

		Args:
		    x: Source function for the relation.
		    y: Target function for the relation.
		"""
		rel = RequiredForRelation(x, y)
		rel.save(f'{get_url(self.cluster)}/requiredfor')


# CLUSTER IMPORT

class ClusterImportProps:
	"""Hold editable cluster import form state."""

	def __init__(self, parent: Optional[GMBDNet] = None, capella_architecture: Optional[str] = None,
				 default_fn_tests: bool = False, default_hl_fn_tests: bool = False, default_hw_tests: bool = False,
				 default_ll_hw_tests: bool = False, import_opms: bool = False):
		"""Initialize cluster import props with its editable state.

		Args:
		    parent: Parent cluster or node used for the operation.
		    capella_architecture: Selected Capella architecture to import.
		    default_fn_tests: Whether to create default function tests.
		    default_hl_fn_tests: Whether to create default high-level function tests.
		    default_hw_tests: Whether to create default hardware tests.
		    default_ll_hw_tests: Whether to create default low-level hardware tests.
		    import_opms: Whether to import operating modes.
		"""
		self.parent = parent
		self.capella_architecture = capella_architecture
		self.default_fn_tests = default_fn_tests
		self.default_hw_tests = default_hw_tests
		self.default_hl_fn_tests = default_hl_fn_tests
		self.default_ll_hw_tests = default_ll_hw_tests
		self.import_opms = import_opms
		self.files: list[Path] = []


class ClusterImportPage(FunctionalPage):
	"""Display the cluster import editing page."""

	parent: Optional[GMBDNet]
	props: ClusterImportProps
	queue: Queue
	progress_bar: ui.linear_progress
	timer: ui.timer

	def __init__(self, cluster_id: Optional[str] = None):
		"""Load the cluster import and configure its available actions.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		self.parent = get_object_or_404(GMBDNet, uid=cluster_id) if cluster_id else None
		self.props = ClusterImportProps(self.parent)

		self.queue: Queue = Manager().Queue()
		self.progress_bar = ui.linear_progress(value=0., show_value=False, size='10px').classes('rounded').props(
			'animation-speed:1000')
		self.progress_bar.visible = False
		self.timer = ui.timer(0.1, callback=lambda: self.progress_bar.set_value(
			self.queue.get() if not self.queue.empty() else self.progress_bar.value), active=False)

		title = 'Capella import'
		if self.parent is not None:
			title += f' into {self.parent.fqn}'
		super().__init__(title, self.parent, [
			Button('Discard', None, 'warning', lambda: goto('/' if self.parent is None else self.parent)),
			Button('Save', None, 'primary', self._save, enabled_from=(locals(), 'props', lambda p: bool(p.files) and bool(p.capella_architecture)))
		])

	def _show_content(self):
		"""Render the Capella upload and model import options."""
		ui.upload(label='Capella', multiple=True, on_multi_upload=self._handle_capella_upload, auto_upload=True)
		ui.select(["logical", "physical"], label="Capella architecture").bind_value(self.props,
																					'capella_architecture').classes(
			'w-60')
		with ui.row():
			ui.checkbox(text="Default tests on functions").bind_value(self.props, "default_fn_tests")
			ui.checkbox(text="Default tests on high-level functions (functions with subfunctions)").bind_value(self.props,
																											   "default_hl_fn_tests")
		with ui.row():
			ui.checkbox(text="Default tests on hardware").bind_value(self.props, "default_hw_tests")
			ui.checkbox(
				text="Default tests on low-level hardware (hardware realizing functions without subfunctions)").bind_value(
				self.props, "default_ll_hw_tests")
		with ui.row():
			ui.checkbox(text="Import operating modes").bind_value(self.props, "import_opms")

	async def _handle_capella_upload(self, e: events.MultiUploadEventArguments):
		"""Read uploaded Capella architecture files for import.

		Args:
		    e: Upload event containing Capella model files.
		"""
		for f in e.files:
			fd, tmp_path = tempfile.mkstemp(suffix=Path(f.name).suffix)
			os.close(fd)

			new_tmp_path = Path(tmp_path).with_name(f.name)
			shutil.move(tmp_path, new_tmp_path)

			with new_tmp_path.open('wb') as new_tf:
				new_tf.write(await f.read())

			self.props.files.append(new_tmp_path)

	async def _save(self):
		"""Import the configured Capella model and update import progress."""
		ui.notify('Importing model, please wait. This could take a long time, depending on the size of your model.')
		self.progress_bar.visible = True
		self.timer.active = True
		c: GCluster = await run.io_bound(
			GCluster.load_capella,
			self.props.capella_architecture,
			self.props.default_fn_tests,
			self.props.default_hl_fn_tests,
			self.props.default_hw_tests,
			self.props.default_ll_hw_tests,
			self.props.import_opms,
			*self.props.files,
			queue=self.queue)
		self.timer.active = False
		self.progress_bar.visible = False
		if self.props.parent is not None:
			if self.props.parent.has_element(c.name):
				i = 1
				while self.props.parent.has_element(f'{c.name}_{i}'):
					i += 1
				c.name = f'{c.name}_{i}'
				c.save()
				ui.notify(f'Imported as {c.name} due to already existing name!')
			c.net.connect(self.props.parent)
		else:
			other_root_clusters = {c.name for c in GMBDNet.nodes.filter(net__exists=False).filter(uid__ne=c.uid)}
			if c.name in other_root_clusters:
				i = 1
				while f'{c.name}_{i}' in other_root_clusters:
					i += 1
				c.name = f'{c.name}_{i}'
				c.save()
				ui.notify(f'Imported as {c.name} due to already existing name!')
		for f in self.props.files:
			f.unlink()
		goto(c)


class CPTImportProps:
	"""Hold editable CPT import form state."""

	def __init__(self, cluster: GCluster):
		"""Initialize cpt import props with its editable state.

		Args:
		    cluster: Cluster whose nodes receive the imported CPTs.
		"""
		self.cluster: GCluster = cluster
		self.nodes: dict[GCPTEnabledNode, list[str]] = dict()
		self.cpts: dict[str, tuple[GCPTEnabledNode, CPT]] = dict()
		self.enabled: dict[str, bool] = dict()
		self.validation_msg: dict[GCPTEnabledNode, Optional[str]] = dict()

	def add_cpt(self, origin: str, node: GCPTEnabledNode, cpt: CPT):
		"""Register an imported CPT and set its initial validation and enabled state.

		Args:
		    origin: Source identifier for the imported CPT.
		    node: CPT-enabled node matched to the imported table.
		    cpt: Conditional probability table to import.
		"""
		if node not in self.validation_msg:
			validation = node.validate_cpt()
			self.validation_msg[node] = validation[0].message if validation else None

		if node in self.nodes:
			self.nodes[node].append(origin)
			self.enabled[origin] = False
		else:
			self.nodes[node] = [origin]
			self.enabled[origin] = not (node.has_cpt and self.validation_msg[node] is None)
		self.cpts[origin] = (node, cpt)


async def handle_cpt_upload(e: events.MultiUploadEventArguments, props: CPTImportProps):
	"""Process each uploaded CPT file and refresh the import table.

	Args:
	    e: Multi-upload event containing CPT spreadsheets or ZIP archives.
	    props: Import state to update with uploaded CPTs.
	"""
	for f in e.files:
		if f.content_type == 'application/x-zip-compressed':
			await handle_cpt_zip_file(f, props)
		elif f.content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
			await handle_cpt_xls_file(f, props)
		else:
			ui.notify('Invalid file type provided!', color='negative')
	cpt_import_table.refresh()

async def handle_cpt_zip_file(f: ui.upload.FileUpload, props: CPTImportProps):
	"""Read CPT spreadsheets from an uploaded ZIP archive.

	Args:
	    f: Uploaded file to read.
	    props: Import settings and uploaded CPT candidates.
	"""
	with ZipFile(io.BytesIO(await f.read())) as zip_file:
		for excel_file in zip_file.filelist:
			handle_cpt_file_contents(excel_file.filename, io.BytesIO(zip_file.read(excel_file.filename)), props, origin=f'{f.name}/{excel_file.filename}')

async def handle_cpt_xls_file(f: ui.upload.FileUpload, props: CPTImportProps):
	"""Read and process an uploaded CPT spreadsheet.

	Args:
	    f: Uploaded file to read.
	    props: Import settings and uploaded CPT candidates.
	"""
	handle_cpt_file_contents(f.name, io.BytesIO(await f.read()), props)

def handle_cpt_file_contents(filename: str, contents: io.BytesIO, props: CPTImportProps, origin: str = None):
	"""Resolve and validate a spreadsheet against its matching CPT node.

	Args:
	    filename: Name of the uploaded spreadsheet.
	    contents: Spreadsheet contents to parse.
	    props: Import state used to match and validate this CPT.
	    origin: ZIP member path or uploaded filename identifying the CPT source.
	"""
	f_fqn = filename.removesuffix('.xlsx')
	try:
		node: GCPTEnabledNode = props.cluster.get_element(f_fqn)
	except KeyError:
		ui.notify(f'Node {f_fqn} not found in {props.cluster}!', color='negative')
		return
	df = pd.read_excel(contents, sheet_name='CPT', index_col=list(range(len(node.parents()))))
	cpt, msg = CPT.from_df(node, df)
	if msg:
		ui.notify(f'{node.fqn}: {msg}', color='warning')
		return
	props.add_cpt(origin or filename, node, cpt)

def cpt_import_form(props: CPTImportProps):
	"""Render the CPT upload control and the resulting import table.

	Args:
	    props: CPT import state bound to the uploader and table.
	"""
	ui.upload(label='CPTs', multiple=True, on_multi_upload=lambda e: handle_cpt_upload(e, props),
			  auto_upload=True)
	cpt_import_table(props)


class CPTImportPage(FunctionalPage):
	"""Display the CPT import probability table editor."""

	props: CPTImportProps

	def __init__(self, cluster_id: str):
		"""Load the cptimport and configure its available actions.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		cluster = get_object_or_404(GCluster, uid=cluster_id)
		self.props = CPTImportProps(cluster)

		super().__init__('CPT import', cluster, [
			Button('Discard', None, 'warning', lambda: goto(cluster)),
			Button('Save', None, 'primary', self._save, enabled_from=(locals(), 'props', lambda p: any(p.enabled.values())))
		])

	def _show_content(self):
		"""Render CPT upload controls and the import candidate table."""
		ui.upload(label='CPTs', multiple=True, on_multi_upload=self._handle_cpt_upload, auto_upload=True)
		cpt_import_table(self.props)

	def _save(self):
		"""Persist enabled imported CPTs and return to the cluster."""
		for origin, enabled in self.props.enabled.items():
			if not enabled:
				continue
			node, cpt = self.props.cpts[origin]
			node.cpt = cpt.to_dict()
			node.save()
		goto(self.element)

	async def _handle_cpt_upload(self, e: events.MultiUploadEventArguments):
		"""Process each uploaded CPT file and refresh the import table.

		Args:
		    e: Multi-upload event containing CPT spreadsheets or ZIP archives.
		"""
		for f in e.files:
			if f.content_type == 'application/x-zip-compressed':
				await handle_cpt_zip_file(f, self.props)
			elif f.content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
				await handle_cpt_xls_file(f, self.props)
			else:
				ui.notify('Invalid file type provided!', color='negative')
		cpt_import_table.refresh()

	async def _handle_cpt_zip_file(self, f: ui.upload.FileUpload):
		"""Read CPT spreadsheets from an uploaded ZIP archive.

		Args:
		    f: Uploaded file to read.
		"""
		with ZipFile(io.BytesIO(await f.read())) as zip_file:
			for excel_file in zip_file.filelist:
				handle_cpt_file_contents(excel_file.filename, io.BytesIO(zip_file.read(excel_file.filename)),
										 self.props, origin=f'{f.name}/{excel_file.filename}')

	async def _handle_cpt_xls_file(self, f: ui.upload.FileUpload):
		"""Read and process an uploaded CPT spreadsheet.

		Args:
		    f: Uploaded file to read.
		"""
		handle_cpt_file_contents(f.name, io.BytesIO(await f.read()), self.props)

	def _handle_cpt_file_contents(self, filename: str, contents: io.BytesIO, origin: Optional[str] = None):
		"""Resolve and validate a spreadsheet against its matching CPT node.

		Args:
		    filename: Name of the uploaded spreadsheet.
		    contents: Spreadsheet contents to parse.
		    origin: ZIP member path or uploaded filename identifying the CPT source.
		"""
		f_fqn = filename.removesuffix('.xlsx')
		try:
			node: GCPTEnabledNode = self.props.cluster.get_element(f_fqn)
		except KeyError:
			ui.notify(f'Node {f_fqn} not found in network!', color='negative')
			return
		df = pd.read_excel(contents, sheet_name='CPT', index_col=list(range(len(node.parents()))))
		cpt, msg = CPT.from_df(node, df)
		if msg:
			ui.notify(f'{node.fqn}: {msg}', color='warning')
			return
		self.props.add_cpt(origin or filename, node, cpt)


@ui.refreshable
def cpt_import_table(props: CPTImportProps):
	"""Display candidate CPTs and their validation and origin controls.

	Args:
	    props: Uploaded CPT candidates, enabled sources, and validation messages.
	"""
	if not props.cpts:
		ui.label('No CPTs have been uploaded yet.')
		return

	with ui.list().props('separator'):
		ui.item_label('CPTs to import').props('header').classes('text-bold')
		for node, origins in props.nodes.items():
			for origin in origins:
				with ui.item():
					with ui.checkbox(str(node.fqn)).bind_value(props.enabled, origin) as cbx:
						_node_cpt_badge(node, props)
						if len(origins) > 1:
							ui.label(origin.removesuffix(f'/{node.fqn}.xlsx')).classes('inline ml-2 text-grey')
							cbx.on_value_change(lambda e, n=node, o=origin, p=props: _change_origin(e, n, o, p))

def _node_cpt_badge(node: GCPTEnabledNode, props: CPTImportProps):
	"""Render a badge showing the imported CPT's validation status.

	Args:
	    node: CPT-enabled node whose import status is shown.
	    props: Import validation messages for the selected CPT node.
	"""
	if props.validation_msg.get(node, None):
		ui.badge('!', color='negative').classes('ml-2').tooltip(props.validation_msg[node])
	elif node.requires_cpt or node.has_cpt:
		ui.badge('!', color='warning').classes('ml-2').tooltip(
			f'A valid CPT has already been specified for {node.fqn}. It will be overwritten when selected.')

def _change_origin(e, node: GCPTEnabledNode, origin: str, props: CPTImportProps):
	"""Update the selected CPT origin when its selection changes.

	Args:
	    e: Selection event indicating whether this CPT source is enabled.
	    node: Node with multiple candidate CPT sources.
	    origin: Source identifier for the imported CPT.
	    props: Candidate CPT origins and their enabled flags.
	"""
	if e.value:
		for o in props.nodes[node]:
			if o is not origin:
				props.enabled[o] = False
