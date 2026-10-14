# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
from pathlib import Path
from typing import Optional, Callable, Union, Type

import pandas as pd
from nicegui import ui

import io
from mbdlyb import base
from mbdlyb.colormap import ColorMap
from mbdlyb.io import export_to_yed
from mbdlyb.formalisms.bayesnet import BayesNet, export_to_bifxml, export_to_netica
from mbdlyb.gdb import cls, GMBDIdentifiable, GMBDElement, GMBDNet, get_object
from mbdlyb.cpt import CPT

import mbdlyb_ui.app as mbdlyb_app


def goto(url: Union[str, GMBDElement]):
	"""Navigate to a URL or the registered URL of a model element.

	Args:
		url: Destination URL or resolvable model element.

	Returns:
		The result of NiceGUI's navigation call.
	"""
	return ui.navigate.to(url if isinstance(url, str) else get_url(url))

def get_url(element: Union[str, GMBDIdentifiable]) -> Optional[str]:
	"""Resolve an element or serialized menu-tree ID to its registered URL.

	Args:
		element: Model object, UID, or ``ClassName__uid`` tree ID.

	Returns:
		A formatted URL, or None if no resolver matches.
	"""
	clazz, uid = (element.split('__') if '__' in element else (None, element)) if isinstance(element, str) else (
		element.__class__, element.uid)
	clazz = cls(clazz)
	if clazz in mbdlyb_app.MBDLYB_URL_RESOLVER:
		url = mbdlyb_app.MBDLYB_URL_RESOLVER[clazz]
		if isinstance(url, str):
			return url.format(uid)
		elif isinstance(url, Callable) and isinstance(element, GMBDIdentifiable):
			return url(element)
	return None

def build_menu_tree(clazz: Type[GMBDNet], parent: Optional[GMBDNet] = None):
	"""Create nested NiceGUI tree data for a network class or parent subnet.

	Args:
		clazz: Network class from which to load root nodes.
		parent: Network whose subnets should form this level.

	Returns:
		Tree nodes with IDs, labels, and nested child lists.
	"""
	return [
		{'id': f'{subnet.__class__.__name__}__{subnet.uid}', 'label': subnet.name,
		 'children': build_menu_tree(clazz, subnet)} for subnet in
		(clazz.nodes.filter(net__exists=False).order_by('name') if parent is None else parent.subnets.order_by('name'))
	]


# HELPER CLASSES

# TODO: Seems more like a GDB class, not a helper class. Move and reconsider.
class Relation:
	"""Track an editable graph relation and its original endpoints."""

	_attr: str = ''

	_start_cls: type[GMBDElement]
	_end_cls: type[GMBDElement]
	start_uid: Optional[str] = None
	end_uid: Optional[str] = None
	_original_start_uid: Optional[str] = None
	_original_end_uid: Optional[str] = None

	def __init__(self, start_node: Optional[GMBDElement] = None, end_node: Optional[GMBDElement] = None,
	             start_node_type: Optional[type[GMBDElement]] = None,
	             end_node_type: Optional[type[GMBDElement]] = None):
		"""Capture relation endpoints and their lookup classes.

		Args:
			start_node: Initial source element, when available.
			end_node: Initial target element, when available.
			start_node_type: Lookup class for the source element.
			end_node_type: Lookup class for the target element.
		"""
		if start_node is not None:
			self._start_cls = start_node_type or type(start_node)
			self.start_uid = start_node.uid
			self._original_start_uid = start_node.uid
		else:
			self._start_cls = start_node_type
		if end_node is not None:
			self._end_cls = end_node_type or type(end_node)
			self.end_uid = end_node.uid
			self._original_end_uid = end_node.uid
		else:
			self._end_cls = end_node_type or start_node_type

	def get_start_node(self) -> GMBDElement:
		"""Look up the currently selected source element by UID.

		Returns:
			The source element, or None when no source UID is selected.
		"""
		return self._start_cls.nodes.get(uid=self.start_uid) if self.start_uid else None

	def get_end_node(self) -> GMBDElement:
		"""Look up the currently selected target element by UID.

		Returns:
			The target element, or None when no target UID is selected.
		"""
		return self._end_cls.nodes.get(uid=self.end_uid) if self.end_uid else None

	def get_original_start_node(self) -> GMBDElement:
		"""Look up the source element before any edits.

		Returns:
			The original source, or None for a new relation.
		"""
		return self._start_cls.nodes.get(uid=self._original_start_uid) if self._original_start_uid else None

	def get_original_end_node(self) -> GMBDElement:
		"""Look up the target element before any edits.

		Returns:
			The original target, or None for a new relation.
		"""
		return self._end_cls.nodes.get(uid=self._original_end_uid) if self._original_end_uid else None

	def start_node_changed(self) -> bool:
		"""Check whether an existing relation's source UID changed.

		Returns:
			True when the original and selected source UIDs differ.
		"""
		return self._original_start_uid is not None and self.start_uid != self._original_start_uid

	def end_node_changed(self) -> bool:
		"""Check whether an existing relation's target UID changed.

		Returns:
			True when the original and selected target UIDs differ.
		"""
		return self._original_end_uid is not None and self.end_uid != self._original_end_uid

	def save(self, redirect: Optional[Union[str, GMBDElement]] = None):
		"""Replace the old graph edge with the currently selected relation.

		Args:
			redirect: Optional URL or element to navigate to after saving.
		"""
		if self.start_node_changed():
			self.get_original_start_node().__getattribute__(self._attr).disconnect(self.get_original_end_node())
		elif self._original_end_uid is not None:
			self.get_start_node().__getattribute__(self._attr).disconnect(self.get_original_end_node())
		self.get_start_node().__getattribute__(self._attr).connect(self.get_end_node(), self.get_props())
		if redirect is not None:
			ui.navigate.to(redirect if isinstance(redirect, str) else get_url(redirect))

	def get_props(self) -> dict:
		"""Provide relationship properties for the edge being saved.

		Returns:
			An empty mapping by default; subclasses can supply edge properties.
		"""
		return dict()


# DATABASE HELPERS

def get_object_or_404[T](klass: type[T], **kwargs) -> T:
	"""Fetch a model object, displaying a message when none is found.

	Args:
		klass: Model class to query.
		**kwargs: Properties used to filter the lookup.

	Returns:
		The matching object, or None when the lookup finds nothing.
	"""
	# TODO: Fix None handling in UI (actually throw a 404)
	o = get_object(klass, **kwargs)
	if o is None:
		ui.label(f'Could not find {klass.__name__} with parameters {dict(**kwargs)}.')
	return o

def get_relation_or_404(start_node: GMBDElement, end_node: GMBDElement, attr: str):
	"""Find a graph relationship and display a message when missing.

	Args:
		start_node: Element whose relationship manager is queried.
		end_node: Related element being looked up.
		attr: Relationship manager attribute on the source.

	Returns:
		The relationship record, or None when no edge exists.
	"""
	relation = start_node.__getattribute__(attr).relationship(end_node)
	if relation is None:
		ui.label(f'Could not find \'{attr}\' relationship between {start_node} and {end_node}.')
	return relation

def save_object(obj: GMBDElement, success_url: Optional[Union[str, GMBDElement, Callable]] = None):
	"""Save an existing model element, update its FQN, and optionally redirect.

	Args:
		obj: Element to persist.
		success_url: Destination URL, element, or callable receiving ``obj``.
	"""
	obj.save()
	obj.update_fqn()
	if success_url is not None:
		goto(success_url if isinstance(success_url, (str, GMBDElement)) else success_url(obj))

def save_new_object(obj: GMBDElement, net: GMBDNet, success_url: Optional[Union[str, GMBDElement, Callable]] = None):
	"""Save a new element in a network and optionally redirect.

	Args:
		obj: New element to persist.
		net: Containing network to associate with the element.
		success_url: Destination URL, element, or callable receiving ``obj``.
	"""
	obj.save()
	obj.set_net(net)
	obj.update_fqn()
	if success_url is not None:
		goto(success_url if isinstance(success_url, (str, GMBDElement)) else success_url(obj))


# DOWNLOAD HELPERS

def download_graph(gdb_net: GMBDNet, colormap: Optional[ColorMap] = None):
	"""Download a network graph as GraphML for yEd.

	Args:
		gdb_net: Database-backed network to export.
		colormap: Optional node color mapping used for rendering.
	"""
	net: base.MBDNet = type(gdb_net).load_from_db(gdb_net.uid)
	yed_graph = export_to_yed(net, colormap=colormap)
	xml = yed_graph.get_graph()
	ui.download(xml.encode(), f'{net.name}.graphml')

def download_bayesnet(gdb_net: GMBDNet, suffix: str = '.dne', colormap: Optional[ColorMap] = None):
	"""Export a Bayesian network in Netica or BIF XML format.

	Args:
		gdb_net: Database-backed network to export.
		suffix: Export format, either ``.dne`` or ``.bifxml``.
		colormap: Optional colors for Netica output.
	"""
	# TODO: Use tempfile
	net: base.MBDNet = type(gdb_net).load_from_db(gdb_net.uid)
	if not isinstance(net, BayesNet):
		ui.notify(f'{net.name} does not support exporting to BayesNet!')
		return
	temp_file = Path(f'__mbdlyb_temp__{net.name}{suffix}')
	if temp_file.exists():
		temp_file.unlink()
	match suffix:
		case '.dne':
			export_to_netica(net, temp_file, colormap=colormap, overwrite=True)
		case '.bifxml':
			export_to_bifxml(net, temp_file, overwrite=True)
		case _:
			ui.notify('Invalid export file type selected!')
			return
	ui.download(temp_file, net.name + suffix)

def download_cpt(cpt: CPT, name: str):
	"""Download a conditional probability table as an Excel workbook.

	Args:
		cpt: Probability table to serialize.
		name: Base name of the downloaded workbook.
	"""
	xls_buffer = io.BytesIO()
	with pd.ExcelWriter(xls_buffer, engine='xlsxwriter') as writer:
		cpt.to_df().to_excel(writer, sheet_name='CPT', index=bool(cpt.parents))
	ui.download.content(xls_buffer.getvalue(), f'{name}.xlsx',
						media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
