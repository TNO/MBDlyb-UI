# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
from typing import Optional

from nicegui import ui

from mbdlyb.gdb import GMBDElement, GMBDNet
from mbdlyb_ui.helpers import Relation, save_new_object as sno
from mbdlyb.functional.gdb import GFunctionalNode, GCluster, CLASS_ICONS


# HELPER CLASSES

class FunctionalRelation(Relation):
	"""Represent an editable functional relation."""

	weight: float

	def __init__(self, start_node: Optional[GMBDElement] = None, end_node: Optional[GMBDElement] = None,
	             start_node_type: Optional[type[GMBDElement]] = None, end_node_type: Optional[type[GMBDElement]] = None,
	             weight: float = 1.):
		"""Initialize functional relation with its editable state.

		Args:
		    start_node: Source node of the relation.
		    end_node: Target node of the relation.
		    start_node_type: Expected source node class.
		    end_node_type: Expected target node class.
		    weight: Weight assigned to the relation.
		"""
		super().__init__(start_node, end_node, start_node_type, end_node_type)
		self.weight = weight

	def get_props(self) -> dict:
		"""Return the relation properties needed for persistence.

		Returns:
		    Properties to persist on the relation.
		"""
		return {
			**super().get_props(),
			'weight': self.weight
		}


class SubfunctionOfRelation(FunctionalRelation):
	"""Represent an editable subfunction of relation."""

	_attr = 'subfunctions'


class RealizesRelation(FunctionalRelation):
	"""Represent an editable realizes relation."""

	_attr = 'realizes'


class RequiredForRelation(FunctionalRelation):
	"""Represent an editable required for relation."""

	_attr = 'required_for'
	operating_modes: list[str]

	def __init__(self, start_node: Optional[GMBDElement] = None, end_node: Optional[GMBDElement] = None,
	             start_node_type: Optional[type[GMBDElement]] = None, end_node_type: Optional[type[GMBDElement]] = None,
	             weight: float = 1., operating_modes: Optional[list[str]] = None):
		"""Initialize required for relation with its editable state.

		Args:
		    start_node: Source node of the relation.
		    end_node: Target node of the relation.
		    start_node_type: Expected source node class.
		    end_node_type: Expected target node class.
		    weight: Weight assigned to the relation.
		    operating_modes: Operating modes in which the relation applies.
		"""
		super().__init__(start_node, end_node, start_node_type, end_node_type, weight)
		self.operating_modes = operating_modes or []

	def get_props(self) -> dict:
		"""Return the relation properties needed for persistence.

		Returns:
		    Properties to persist on the relation.
		"""
		return {
			**super().get_props(),
			'operating_modes': self.operating_modes
		}


class AffectsRelation(FunctionalRelation):
	"""Represent an editable affects relation."""

	_attr = 'affects'


class ObservesRelation(FunctionalRelation):
	"""Represent an editable observes relation."""

	_attr = 'observed_by'


class TestsRelation(FunctionalRelation):
	"""Represent an editable tests relation."""

	_attr = 'tested_by'


class IndicatesRelation(FunctionalRelation):
	"""Represent an editable indicates relation."""

	_attr = 'indicated_by'


# DATABASE HELPERS

def save_new_object(obj: GMBDElement, net: GCluster, disable_redirect: bool = False):
	"""Save a functional element and optionally navigate to its cluster.

	Args:
	    obj: Functional element to add to the cluster.
	    net: Cluster containing the new model object.
	    disable_redirect: Whether to suppress navigation after saving.
	"""
	sno(obj, net, None if disable_redirect else f'/cluster/{net.uid}')


class State:
	"""Represent a named functional node state."""

	def __init__(self, name: str):
		"""Initialize state with its editable state.

		Args:
		    name: Name of this entry.
		"""
		self.name = name

	def __eq__(self, other):
		"""Compare this editable value with another value or name.

		Args:
		    other: Value to compare with this object.

		Returns:
		    Whether the compared values match.
		"""
		if isinstance(other, State):
			return self.name == other.name
		if isinstance(other, str):
			return self.name == other
		return False


class StateTable:
	"""Manage editable functional node states."""

	states: list[State]

	def __init__(self, states: list[State]):
		"""Initialize state table with its editable state.

		Args:
		    states: Editable states bound to the form.
		"""
		self.states = states

	def add_state(self):
		"""Append a uniquely named state and refresh the state editor."""
		name = 'State_'
		for i in range(1, 100):
			if name + str(i) not in self.states:
				name = name + str(i)
				break
		self.states.append(State(name))
		state_table.refresh()


	def drop_state(self, state: State):
		"""Remove a state and refresh the state editor.

		Args:
		    state: State entry to remove.
		"""
		self.states.remove(state)
		state_table.refresh()

	@classmethod
	def from_list(cls, l: list[str]) -> 'StateTable':
		"""Create editable state entries from stored names.

		Args:
		    l: Stored state or operating mode names to turn into entries.

		Returns:
		    Editable collection initialized from the stored values.
		"""
		return StateTable([State(s) for s in l or []])

	def to_list(self) -> list[str]:
		"""Extract state names from the editable entries.

		Returns:
		    Stored values represented by the editable entries.
		"""
		return [s.name for s in self.states]


@ui.refreshable
def state_table(state_table: StateTable, default_states: list[str]):
	"""Render editable state names and controls for adding or removing states.

	Args:
	    state_table: Editable collection of states.
	    default_states: Fallback state names shown when no custom states are set.
	"""
	ui.label(f'Leave empty for default states ({"/".join(default_states)})!')
	with ui.grid(columns=2).classes('vertial-bottom'):
		for col in ('Custom state',):
			ui.label(col).classes('font-bold')
		ui.icon('add', color='primary').on('click', lambda: state_table.add_state()).classes('cursor-pointer')
		for state in state_table.states:
			ui.input('State').bind_value(state, 'name')
			ui.icon('delete', color='negative').on('click', lambda s=state: state_table.drop_state(s)).classes(
				'self-end cursor-pointer')


def build_tree(node: GFunctionalNode | GCluster) -> dict:
	"""Build a nested tree entry with node identity and CPT metadata.

	Args:
	    node: Node whose identity, CPT status, and children are serialized.

	Returns:
	    Nested tree entry describing the node and its children.
	"""
	d = {'id': node.uid,
		 'fqn': str(node.fqn),
		 'name': node.name,
		 'type': node.__class__.__name__,
		 'icon': CLASS_ICONS.get(node.__class__, 'question_mark'),
		 'requires_cpt': node.requires_cpt if isinstance(node, GFunctionalNode) else False,
		 'has_cpt': node.has_cpt if isinstance(node, GFunctionalNode) else False
	 }
	if isinstance(node, GMBDNet):
		d['children'] = [build_tree(c) for c in
						 list(node.subnets.order_by('name')) + list(node.mbdnodes.order_by('name'))]
	return d
