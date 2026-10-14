# -*- coding: utf-8 -*-
"""
	Copyright (c) 2026 TNO-ESI
	All rights reserved.
"""
import html
import re
from collections import defaultdict
from typing import Union, Optional

from nicegui import ui

from mbdlyb.colormap import ColorMap
from mbdlyb.gdb import GMBDDependency, GMBDNet, GMBDNode, GMBDElement, GMBDRelation

from .helpers import get_url, goto


type BaseRelationSpec = tuple[type[GMBDDependency], str]
type RelationSpec = Union[BaseRelationSpec, tuple[type[GMBDDependency], str, tuple[list[BaseRelationSpec], list[BaseRelationSpec]]]]


class MermaidBuilder:
	"""Build interactive Mermaid flowcharts from graph-backed networks."""

	_net: GMBDNet
	_node_types: set[type[GMBDNode]]
	_attributes: dict[str, Union[list[Union[str, tuple[str, bool]]], tuple[list[RelationSpec], list[RelationSpec]]]]
	_color_map: ColorMap
	_label_map: dict[type[GMBDRelation], str]
	_direction: str

	_diagram: list[str]
	_tree: dict
	_n_dict: dict[str, GMBDElement]
	_relations: defaultdict[type[GMBDRelation], set[tuple[str, str]]]

	def __init__(self, net: GMBDNet,
				 attributes: dict[type[GMBDElement], Union[list[Union[str, tuple[str, bool]]], tuple[list[RelationSpec], list[RelationSpec]]]],
				 color_map: ColorMap, label_map: Optional[dict[type[GMBDRelation], str]] = None,
				 direction: str = 'LR'):
		"""Configure which network elements and relationships appear in the chart.

		Args:
			net: Root network to visualize.
			attributes: Node collections and relation attributes to traverse.
			color_map: Colors associated with node classes.
			label_map: Optional labels associated with relation classes.
			direction: Mermaid flowchart direction, such as ``LR``.
		"""
		self._net = net
		self._node_types: set[type[GMBDNode]] = set()
		self._attributes = {k.__name__: v for k, v in attributes.items()}
		self._color_map = color_map or ColorMap()
		self._label_map = label_map or dict()
		self._direction = direction

	def reset(self):
		"""Clear chart text and traversal state before a new build."""
		self._diagram = []
		self._tree = dict()
		self._n_dict = dict()
		self._relations = defaultdict(set)

	def build(self) -> str:
		"""Traverse the network and render the complete Mermaid flowchart.

		Returns:
			Mermaid source with subgraphs, nodes, class colors, and edges.
		"""
		self.reset()
		self._diagram = ['flowchart']
		self._diagram.append(f'subgraph "{str(self._net.fqn)}" ["<b>{self._net.name}</b>"]')
		self._diagram.append(f'direction {self._direction}')

		self._build_tree(self._net)

		# add color mapping
		for clazz in self._node_types:
			self._diagram.append(f'classDef {clazz.__name__} fill:{self._color_map.get_color(clazz)};')

		self.add_tree(self._tree, True)
		for rt, links in self._relations.items():
			for x, y in links:
				self._diagram.append(f'{x} --> |{self._label_map.get(rt, rt.__class__.__name__)}| {y}')

		self._diagram.append('end')
		return '\n'.join(self._diagram)

	def _build_tree(self, net: GMBDNet):
		"""Visit configured nodes and optionally recurse into nested networks.

		Args:
			net: Network whose configured attributes should be traversed.
		"""
		for n_attr_t in self._attributes.get(net.__class__.__name__, []):
			if isinstance(n_attr_t, str):
				n_attr, recursion_allowed = n_attr_t, False
			elif isinstance(n_attr_t, tuple):
				n_attr, recursion_allowed = n_attr_t
			else:
				continue
			for n in net.__getattribute__(n_attr):
				if isinstance(n, GMBDNode):
					self._node_types.add(type(n))
					n_id = self.add_to_tree(n)
					parent_relations, child_relations = self._attributes.get(n.__class__.__name__, ([], []))
					self._build_tree_node_relations(n, n_id, parent_relations, True)
					self._build_tree_node_relations(n, n_id, child_relations, False)
				elif recursion_allowed and isinstance(n, GMBDNet):
					self._build_tree(n)

	def _build_tree_node_relations(self, n: GMBDNode, n_id: str, relations: list[RelationSpec], parent_relation: bool):
		"""Collect and recursively traverse relationships for a chart node.

		Args:
			n: Model node whose relations are visited.
			n_id: Mermaid identifier of that node.
			relations: Relation types, attributes, and optional nested specifications.
			parent_relation: Whether edge arrows point toward the current node.
		"""
		for r_spec in relations:
			if len(r_spec) == 2:
				r_type, r_attr = r_spec
				rec_pr, rec_cr = [], []
			elif len(r_spec) == 3:
				r_type, r_attr, (rec_pr, rec_cr) = r_spec
			else:
				return
			for rn in n.__getattribute__(r_attr):
				rn_id = self.add_to_tree(rn)
				self._relations[r_type].add((rn_id, n_id) if parent_relation else (n_id, rn_id))
				self._build_tree_node_relations(rn, rn_id, rec_pr, True)
				self._build_tree_node_relations(rn, rn_id, rec_cr, False)

	@staticmethod
	def m_id(n: GMBDElement | str) -> str:
		"""Convert an element's FQN or string into a Mermaid-safe identifier.

		Args:
			n: Model element or raw identifier.

		Returns:
			An identifier containing only word characters.
		"""
		return re.sub("\\W", "_", n if isinstance(n, str) else str(n.fqn))

	@staticmethod
	def m_name(n: GMBDElement | str, quote: bool = True) -> str:
		"""Escape a label for inclusion in a Mermaid diagram.

		Args:
			n: Model element or raw label.
			quote: Whether to surround the escaped label in double quotes.

		Returns:
			The HTML-escaped, optionally quoted label.
		"""
		name = html.escape(n if isinstance(n, str) else n.name)
		return f'"{name}"' if quote else name

	@staticmethod
	def m_url(element: GMBDElement, in_current_view: bool) -> Optional[str]:
		"""Choose the navigation target for a diagram element.

		Args:
			element: Element for which to resolve a URL.
			in_current_view: Whether the element belongs to the displayed network.

		Returns:
			A resolved URL, or None when no URL is configured.
		"""
		if isinstance(element, GMBDNode) and not in_current_view:
			return get_url(element.get_net())
		return get_url(element)

	def add_element(self, e: GMBDNode, url: Optional[str] = None) -> str:
		"""Append a styled node and optional click handler to the diagram.

		Args:
			e: Node to display.
			url: Optional destination emitted on a node click.

		Returns:
			The node's Mermaid identifier.
		"""
		e_id = self.m_id(e)
		self._diagram.append(f'{e_id}({self.m_name(e)})')
		self._diagram.append(f'class {e_id} {e.__class__.__name__}')
		if url:
			self._diagram.append('click {} call emitEvent("mermaid_click", "{}")'.format(e_id, url))
		return e_id

	def add_tree(self, t: dict, in_current_view: bool = False):
		"""Render a nested tree as subgraphs and clickable nodes.

		Args:
			t: Nested mapping of IDs and labels to nodes or child mappings.
			in_current_view: Whether node links should remain in this network.
		"""
		for (e_id, name), te in t.items():
			if isinstance(te, dict):
				self._diagram.append(f'subgraph "{e_id}" ["<b>{name}</b>"]')
				self.add_tree(te)
				self._diagram.append('end')
			else:
				url = self.m_url(te, in_current_view)
				self.add_element(te, url)

	def add_to_tree(self, element: GMBDElement) -> str:
		"""Insert an element under its relative FQN path in the diagram tree.

		Args:
			element: Model element to place in its containing subgraph.

		Returns:
			The inserted element's Mermaid identifier.
		"""
		path_segments = [self.m_name(s, False) for s in self._net.fqn.relative_fqn(element.fqn).aslist()]
		element_id = self.m_id(element)
		_tree = self._tree
		for segment_idx, path_segment in enumerate(path_segments[:-1]):
			key = (self.m_id('.'.join(path_segments[:segment_idx] + [path_segment])), path_segment)
			if key not in _tree:
				_tree[key] = dict()
			_tree = _tree[key]
		_tree[(element_id, element.name)] = element
		return element_id

	@ui.refreshable
	def draw_mermaid_diagram(self, save_button: ui.menu_item):
		"""Render the chart and wire its navigation and SVG export events.

		Args:
			save_button: Menu item that initiates an SVG download.
		"""
		mermaid_diagram = self.build()
		mermaid_config = {
			'securityLevel': 'loose',
			'theme': 'neutral',
			'themeVariables': {
				'fontSize': '14px'
			},
			'layout': 'elk',
			'elk': {
				'nodePlacementStrategy': 'LINEAR_SEGMENTS'
			},
			'maxTextSize': 1e6
		}
		mm = ui.mermaid(mermaid_diagram, config=mermaid_config).classes('w-full')
		ui.on('mermaid_click', lambda event: goto(event.args))

		def export_start():
			"""Request the rendered SVG from the browser."""
			ui.run_javascript(f'''
				svg = document.querySelector("#c" + {mm.id} + " > svg");
				emitEvent('mermaid_export', svg.outerHTML);
			''')
		save_button.on_click(export_start)

		def export_store_svg(svg):
			"""Download the SVG returned by the browser.

			Args:
				svg: SVG markup of the rendered diagram.
			"""
			ui.download(svg.encode(), f'{self._net.name}.svg')

		ui.on('mermaid_export', lambda evt: export_store_svg(evt.args))
