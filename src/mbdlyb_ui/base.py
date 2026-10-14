# -*- coding: utf-8 -*-
"""
	Copyright (c) 2026 TNO-ESI
	All rights reserved.
"""
from dataclasses import dataclass
from typing import Callable, Optional, Iterable, Any, Union

from nicegui import ui, app

from mbdlyb.gdb import GMBDNet, GMBDElement
import mbdlyb_ui.app as mbdlyb_app
from .utils import Status, status
from .helpers import goto, get_url, build_menu_tree


class Page:
	"""Render a model-backed page with shared navigation, controls, and layout."""

	_hide_breadcrumbs: bool
	_hide_menu_tree: bool
	_settings: Optional[Callable[[ui.dialog], None]]

	_selected_element: Optional[GMBDElement] = None
	_breadcrumbs: Optional[list[GMBDNet]] = None

	_title: Optional[str] = None
	_header_text: Optional[str] = None
	_buttons: Optional[list['Button']] = None
	_ui_buttons: list[list | ui.button]
	_status: Optional[Status]

	def __init__(self, title: Optional[str] = None, element: Optional[GMBDElement] = None,
	             buttons: Optional[list['Button']] = None, header_text: str = '', hide_breadcrumbs: bool = False,
	             hide_menu_tree: bool = False, settings: Optional[Callable[[ui.dialog], None]] = None,
	             status: Optional[Status] = None):
		"""Configure the page and derive its network breadcrumbs.

		Args:
			title: Optional page heading.
			element: Model element represented by this page.
			buttons: Actions displayed alongside the heading.
			header_text: Text shown in the application header.
			hide_breadcrumbs: Whether to suppress the network path.
			hide_menu_tree: Whether to suppress the navigation drawer.
			settings: Callback that populates a settings dialog.
			status: Optional state indicator beside the title.
		"""
		self._title = title
		self._selected_element = element
		self._buttons = buttons or []
		self._ui_buttons = []
		self._header_text = header_text
		self._hide_breadcrumbs = hide_breadcrumbs
		self._hide_menu_tree = hide_menu_tree
		self._settings = settings
		self._status = status
		self._breadcrumbs = None if (hide_menu_tree and hide_breadcrumbs) or element is None else Page._net_trace(element)
		self._init()

	@staticmethod
	def get_mode() -> str:
		"""Return the mode currently stored in NiceGUI's general storage.

		Returns:
			The selected application mode.

		Raises:
			KeyError: If no mode has been stored.
		"""
		return app.storage.general['mode']

	def _init(self):
		"""Provide a subclass hook for additional page initialization."""
		pass

	def show(self):
		"""Render the shared page layout and subclass-specific content."""
		self._show_header()
		if not self._hide_menu_tree:
			with ui.left_drawer(bottom_corner=True).style('background-color: #d7e3f4'):
				menu = ui.tree(build_menu_tree(mbdlyb_app.MBDLYB_MENU_CLASS),
							   on_select=lambda s: goto(get_url(s.value)))
				if self._breadcrumbs is not None:
					menu.expand([f'{c.__class__.__name__}__{c.uid}' for c in self._breadcrumbs])
		self._show_footer()
		self._show_breadcrumbs()
		self._show_title()
		self._show_content()

	def _show_header(self, url='/'):
		"""Render the application header, mode selector, and settings control.

		Args:
			url: Destination of the header's title link.
		"""
		ui.page_title(self._header_text)
		with ui.header(elevated=True).style('background-color: #3874c8'):
			with ui.link(target=url).classes(remove='nicegui-link'):
				ui.label(self._header_text).classes('text-h4')
			if self.has_modes or self._settings is not None:
				ui.space()
				if self.has_modes:
					ui.toggle(mbdlyb_app.MBDLYB_MODES).bind_value(app.storage.general, 'mode').on_value_change(
						self._on_mode_change)
			if self._settings is not None:
				dialog = ui.dialog()
				self._settings(dialog)
				ui.icon('settings').classes('text-h4').on('click', dialog.open)

	def _show_title(self):
		"""Render the page title, status indicator, and page actions."""
		if self._title:
			with ui.row().classes('w-full'):
				if self._status is not None:
					status(self._status)
				ui.label(self._title).classes('text-h5')
				if self._buttons:
					ui.space()
					self._ui_buttons = Page._show_buttons(self._buttons)

	def _show_content(self):
		"""Provide an override point for rendering page-specific content."""
		pass

	def _show_footer(self):
		"""Render the shared attribution footer."""
		with ui.footer(elevated=False):
			ui.label(
				'This prototype tool has been developed by TNO-ESI. All rights reserved.').classes('fit text-right')

	def _show_breadcrumbs(self):
		"""Render links to ancestor networks when breadcrumbs are enabled."""
		if not self._hide_breadcrumbs and self._breadcrumbs:
			with ui.row():
				for c in self._breadcrumbs:
					ui.link(c.name, target=get_url(c))
			ui.separator()

	def _on_mode_change(self):
		"""Provide an override point for responding to application mode changes."""
		pass

	@property
	def element(self) -> Optional[GMBDElement]:
		"""Return the model element associated with this page.

		Returns:
			The selected element, or None if the page has no element.
		"""
		return self._selected_element

	@property
	def has_modes(self) -> bool:
		"""Report whether the app offers more than one mode.

		Returns:
			True when the mode selector is needed.
		"""
		return len(mbdlyb_app.MBDLYB_MODES) > 1

	@staticmethod
	def _show_buttons(buttons: list[Union[list, 'Button']]) -> list[Union[list, ui.button]]:
		"""Render action buttons, grouping nested lists into button groups.

		Args:
			buttons: Buttons or nested groups to display.

		Returns:
			The rendered buttons and nested UI button lists.
		"""
		ui_buttons: list[list | ui.button] = []
		for button in buttons:
			if isinstance(button, Button):
				ui_buttons.append(button.show(btn_props='outline', tooltip_classes='text-xs'))
			elif isinstance(button, list):
				with ui.button_group().props('flat'):
					ui_buttons.append(Page._show_buttons(button))
			else:
				import warnings
				warnings.warn('Could not add buttons to page.')
		return ui_buttons

	@staticmethod
	def _net_trace(n: GMBDElement) -> list[GMBDNet]:
		"""Find the chain of ancestor networks, including a network element itself.

		Args:
			n: Element from which to follow containing networks.

		Returns:
			Networks ordered from the root to the selected element.
		"""
		return (Page._net_trace(n.get_net()) if not n.at_root else []) + ([n] if isinstance(n, GMBDNet) else [])


@dataclass
class Button:
	"""Hold presentation and action options for a model-aware UI button."""

	label: Optional[str | Callable[[GMBDElement], str]] = None
	icon: Optional[str | Callable[[GMBDElement], str]] = None
	color: Optional[str | Callable[[GMBDElement], str]] = None
	handler: Optional[str | Callable[[], Any] | Callable[[GMBDElement], Any]] = None
	tooltip: Optional[str | Callable[[GMBDElement], str]] = None
	enabled_from: Optional[tuple[Any, str, Any]] = None

	def show(self, obj: Optional[GMBDElement] = None, hide_label=False, btn_props: Optional[str] = None,
	         tooltip_classes: Optional[str] = None) -> ui.button:
		"""Render a button with evaluated labels, colors, and click handler.

		Args:
			obj: Element used to evaluate dynamic button options.
			hide_label: Whether to display only the icon.
			btn_props: Additional NiceGUI button properties.
			tooltip_classes: CSS classes for the tooltip.

		Returns:
			The created NiceGUI button.
		"""
		with ui.button(text=None if hide_label else self._eval(self.label, obj), icon=self._eval(self.icon, obj),
					   color=self._eval(self.color, obj), on_click=self._eval_handler(self.handler, obj)).props(
				btn_props or '') as btn:
			if self.tooltip:
				ui.tooltip(self._eval(self.tooltip)).classes(tooltip_classes or '')
			if self.enabled_from is not None:
				btn.bind_enabled_from(*self.enabled_from)
			return btn

	def show_icon(self, obj: GMBDElement = None, btn_props: str = None, tooltip_classes: str = None):
		"""Render this action as a clickable icon.

		Args:
			obj: Element used to evaluate dynamic icon options.
			btn_props: Additional NiceGUI icon properties.
			tooltip_classes: CSS classes for the tooltip.
		"""
		with ui.icon(self._eval(self.icon, obj), color=self._eval(self.color, obj)).on('click', self._eval_handler(
				self.handler, obj)).classes('cursor-pointer').props(btn_props or ''):
			if self.tooltip:
				ui.tooltip(self._eval(self.tooltip, obj)).classes(tooltip_classes or '')

	@staticmethod
	def _eval(attr: Optional[str | Callable[[GMBDElement], str]], obj: Optional[GMBDElement] = None) -> Optional[str]:
		"""Resolve a literal, formatted, or callable button attribute.

		Args:
			attr: Value or callable to resolve.
			obj: Element passed to the callable or used for string formatting.

		Returns:
			The evaluated value, or None when no attribute was supplied.
		"""
		if attr is None:
			return None
		if isinstance(attr, str):
			return attr.format(obj.name if obj is not None else None)
		elif isinstance(attr, Callable):
			return attr(obj)
		return attr

	@staticmethod
	def _eval_handler(attr: Optional[str | Callable[[], Any] | Callable[[GMBDElement], Any]], obj: Optional[GMBDElement] = None) -> Optional[Callable]:
		"""Resolve a URL or callable into a click handler.

		Args:
			attr: Destination URL or handler callback.
			obj: Element to pass to a callback when available.

		Returns:
			A callable click handler, or None when none is configured.
		"""
		if attr is None:
			return None
		if isinstance(attr, str):
			return lambda: goto(attr)
		elif isinstance(attr, Callable):
			if obj is None:
				return attr
			return lambda: attr(obj)
		return attr


@dataclass
class ConditionalButton(Button):
	"""Display a button only when its condition accepts the current element."""

	condition: Optional[Callable[[GMBDElement], bool]] = None

	def show(self, obj: GMBDElement = None, hide_label=False, btn_props: str = None, tooltip_classes: str = None):
		"""Render the button when its condition passes.

		Args:
			obj: Element tested against the condition.
			hide_label: Whether to omit button text.
			btn_props: Additional NiceGUI button properties.
			tooltip_classes: CSS classes for the tooltip.
		"""
		if self.condition is None or self.condition(obj):
			super().show(obj, hide_label, btn_props, tooltip_classes)

	def show_icon(self, obj: GMBDElement = None, btn_props: str = None, tooltip_classes: str = None):
		"""Render the clickable icon when its condition passes.

		Args:
			obj: Element tested against the condition.
			btn_props: Additional NiceGUI icon properties.
			tooltip_classes: CSS classes for the tooltip.
		"""
		if self.condition is None or self.condition(obj):
			super().show_icon(obj, btn_props, tooltip_classes)


@dataclass
class TableColumn:
	"""Describe a table column backed by an element attribute or callable."""

	header: str
	value: str | Callable[[GMBDElement], str]
	url: Optional[Callable[[GMBDElement], str]] = None
	tooltip: Optional[str | Callable[[GMBDElement], str]] = None

	def show(self, obj: GMBDElement, classes: Optional[str] = None, tooltip_classes: Optional[str] = None):
		"""Render a cell for an element, optionally with a link and tooltip.

		Args:
			obj: Element providing the cell value.
			classes: CSS classes applied to the cell row.
			tooltip_classes: CSS classes applied to its tooltip.
		"""
		if isinstance(self.value, str):
			label = str(obj.__getattribute__(self.value))
		elif isinstance(self.value, Callable):
			label = self.value(obj)
		else:
			return
		with ui.row().classes(classes):
			with (ui.link(label, self.url(obj)) if self.url else ui.label(label)):
				if self.tooltip:
					ui.tooltip(
						str(obj.__getattribute__(self.tooltip)) if isinstance(self.tooltip, str) else self.tooltip(
							obj)).classes(tooltip_classes or '')


@dataclass
class TableMultiColumn(TableColumn):
	"""Render a collection-valued field as multiple cells in one column."""

	list_attribute: str = None
	order_by: Optional[str] = None
	separator: str = '	|'

	def show(self, obj: GMBDElement, classes: Optional[str] = None, tooltip_classes: Optional[str] = None):
		"""Render each related element, optionally sorted, with separators.

		Args:
			obj: Element providing the related collection.
			classes: CSS classes applied to the row.
			tooltip_classes: CSS classes passed to the child column renderer.
		"""
		elements = obj.__getattribute__(self.list_attribute) if not (
					self.order_by or isinstance(self.value, str)) else obj.__getattribute__(
			self.list_attribute).order_by(self.order_by or self.value)
		if not elements:
			ui.label().classes(classes or '')
			return
		l_idx = len(elements) - 1
		with ui.row().classes(classes):
			for idx, o in enumerate(elements):
				super().show(o, 'inline')
				if idx < l_idx:
					ui.label(self.separator).classes('inline')


@dataclass
class Table:
	"""Render a titled table of model elements with optional actions."""

	title: str
	rows: Iterable
	columns: list[TableColumn]
	obj: Optional[object] = None
	table_actions: Optional[list[Button]] = None
	row_actions: Optional[list[Button]] = None

	def show(self):
		"""Render table headings, rows, and configured action buttons."""
		with ui.row().classes('w-full'):
			ui.label(self.title).classes('text-h6')
			if self.table_actions:
				ui.space()
				for table_action in self.table_actions:
					table_action.show(self.obj, btn_props='outline', tooltip_classes='text-xs')

		def_classes = 'p-3 border border-gray-200'
		with ui.grid(columns=' '.join(['auto'] * len(self.columns)) + (' 1fr' if self.row_actions else '')).classes('w-full gap-0'):
			if not self.rows:
				ui.label('No entries found.')
				return
			for column in self.columns:
				ui.label(column.header).classes(f'font-bold {def_classes}')
			if self.row_actions:
				ui.label().classes(def_classes)
			for o in self.rows:
				for column in self.columns:
					column.show(o, def_classes)
				if self.row_actions:
					with ui.element('div').classes(f'w-full text-right {def_classes}'):
						for action in self.row_actions:
							action.show_icon(o)
