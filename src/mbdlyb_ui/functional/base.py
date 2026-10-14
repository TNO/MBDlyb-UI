# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
from typing import Optional, Callable, Union

from mbdlyb.gdb import GMBDElement
from mbdlyb.cpt import CPT
from mbdlyb_ui.utils import Status
from nicegui import app, ui

from mbdlyb.functional.gdb import GCluster, GFunctionalNode, GCPTEnabledNode
from mbdlyb_ui import Page, Button
from mbdlyb_ui.dialogs import confirm
from mbdlyb_ui.helpers import goto, get_object_or_404, save_object


class FunctionalPage(Page):
	"""Display the functional editing page."""

	_MENU_TREE_CLASS = GCluster

	def __init__(self, title: Optional[str] = None, element: Optional[GMBDElement] = None,
	             buttons: Optional[list[Button]] = None, header_text: Optional[str] = None,
	             status: Optional[Status] = None, force_hide_nav: bool = False):
		"""Configure the functional page header, navigation, settings, and status.

		Args:
		    title: Title displayed in the page header.
		    element: Model element displayed on the page.
		    buttons: Actions displayed in the page header.
		    header_text: Optional text displayed in the page header.
		    status: Status displayed on the page.
		    force_hide_nav: Whether to hide navigation regardless of mode.
		"""
		hide_nav = True if force_hide_nav else self.get_mode() != 'Editor'
		super().__init__(title, element, buttons, header_text or 'Model Editor', hide_nav, hide_nav, _settings, status)

	def _on_mode_change(self):
		"""Navigate to the cluster root or landing page after changing mode."""
		goto(f'/cluster/{self.element.get_root().uid}/' if isinstance(self.element, GCluster) else '/')


class CPTPage(FunctionalPage):
	"""Display the CPT probability table editor."""

	message: Optional[str]
	cpt: CPT
	redirect_url: Union[str, GMBDElement]

	def __init__(self, klass: type[GFunctionalNode], node_id: str,
	             url: Union[str, GMBDElement, Callable[[GFunctionalNode], Union[str, GMBDElement]]]):
		"""Load the node's CPT and configure save, discard, and drop actions.

		Args:
		    klass: Model class used to look up the node.
		    node_id: Identifier of the node to load.
		    url: Destination after saving or discarding changes.
		"""
		element: GCPTEnabledNode = get_object_or_404(klass, uid=node_id)

		self.redirect_url = url.format(node_id) if isinstance(url, str) else url if isinstance(url, GMBDElement) else url(element)
		self.cpt, self.message = CPT.from_dict(element, element.cpt)

		buttons = [Button('Discard', None, 'warning', lambda: goto(self.redirect_url)),
				   Button('Save', 'save', None, self._save)]
		if not element.requires_cpt:
			buttons = [Button('Drop', None, 'negative', lambda: confirm('Drop CPT',
																		'Are you sure to drop the CPT? This will revert the behavior of this node to its default behavior?',
																		'Drop CPT', self._drop,
																		'negative'))] + buttons
		super().__init__(f'CPT of {element}', element, buttons)

	def _show_content(self):
		"""Render the cpt probability table editor."""
		if self.message:
			ui.label(f'{self.message} The CPT has been regenerated.').classes('text-warning')
		with ui.grid(columns=len(self.cpt.parents) + len(self.element.states)).classes('gap-0'):
			fill_all = {s: .0 for s in self.element.states}
			for _ in self.cpt.parents:
				ui.label()
			for state in self.element.states:
				ui.label(state).classes('border text-weight-bold p-1')
			for parent in self.cpt.parents:
				ui.label(parent.name).classes('border text-weight-bold p-1')
			for state in self.element.states:
				with ui.row().classes('border p-1'):
					ui.number(min=0., max=1., step=.01, precision=5).bind_value(fill_all, state).props(
						'borderless dense')
					ui.button(icon='content_copy').props('flat borderless dense stretch').on_click(
						lambda s=state: self.cpt.set_prob(s, fill_all[s]))
			for line in self.cpt.lines:
				for state_value in line.conditions:
					ui.label(state_value).classes('border p-1')
				for c in line.cells:
					ui.number(min=0., max=1., step=.01, precision=5).bind_value(c, 'probability').props(
						'borderless dense').classes('border p-1')

	def _save(self):
		"""Normalize and persist the edited CPT."""
		self.element.cpt = self.cpt.normalize().to_dict()
		save_object(self.element, self.redirect_url)

	def _drop(self):
		"""Remove the current CPT and persist the node."""
		self.element.cpt = dict()
		save_object(self.element, self.redirect_url)


def _settings(dialog: ui.dialog):
	"""Render switches and reasoner selection in the settings dialog.

	Args:
	    dialog: Settings dialog to populate.
	"""
	def emit_show_diagram():
		"""Notify the browser that the diagram visibility setting changed."""
		ui.run_javascript('''emitEvent('show_diagram', '');''')

	with dialog, ui.card():
		ui.label('Settings').classes('text-h5')
		ui.switch('Model editor - show diagrams').bind_value(app.storage.general, 'show_diagrams').on_value_change(emit_show_diagram)
		ui.switch('Functional diagnoser - auto-compute').bind_value(app.storage.general, 'auto_compute')

		# Since the real class objects are not serializable, we store the reasoner class names:
		ui.select({'BayesNetReasoner': 'BayesNet', 'TensorNetReasoner': 'TensorNet', 'MarkovNetReasoner': 'MarkovNet'},
				  label='Reasoner').bind_value(app.storage.general, 'reasoner')


class LandingPage(FunctionalPage):
	"""Display the landing editing page."""

	def __init__(self):
		"""Configure cluster creation and import actions for the landing page."""
		buttons = [Button(None, 'upload_file', 'secondary', lambda: goto('/cluster/import'), 'Import cluster')]
		if self.get_mode() == 'Editor':
			buttons = [Button(None, 'add', None, lambda: goto('/cluster/new'), 'New cluster')] + buttons
		super().__init__('Clusters', buttons=buttons)

	def _show_content(self):
		"""Display instructions or root clusters according to editor mode."""
		mode = self.get_mode()
		if mode == 'Editor':
			ui.label(
				'Select an existing cluster on the left, or use the buttons on the left to either create a new one or import one.')
		elif mode == 'Tree':
			with ui.list().props('separator').classes('w-full'):
				for cluster in GCluster.nodes.filter(net__exists=False).order_by('name'):
					with ui.item(on_click=lambda c=cluster: goto(c)):
						with ui.item_section().props('avatar'):
							ui.icon('account_tree')
						with ui.item_section():
							ui.item_label(cluster.name)
