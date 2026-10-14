# -*- coding: utf-8 -*-
"""
	Copyright (c) 2026 TNO-ESI
	All rights reserved.
"""
import asyncio
import inspect
from typing import Union, Callable, Any

from nicegui import ui

from mbdlyb.gdb import GMBDElement

from .helpers import goto


def confirm(title: str, message: str, confirm_text: str, on_confirm: Union[Callable, tuple[Callable, tuple[Any]]],
			confirm_color: str = 'primary'):
	"""Show a confirmation dialog and invoke the selected callback on acceptance.

	Args:
		title: Dialog heading.
		message: Explanation displayed beneath the heading.
		confirm_text: Label of the acceptance button.
		on_confirm: Callback or a callback paired with its positional arguments.
		confirm_color: Color of the acceptance button.
	"""
	def _on_cancel():
		"""Close and clear the confirmation dialog."""
		dialog.close()
		dialog.clear()

	def _on_confirm():
		"""Invoke the callback, schedule a coroutine if returned, and close the dialog."""
		if isinstance(on_confirm, tuple):
			oc_fn, args = on_confirm
		else:
			oc_fn, args = on_confirm, ()
		_r = oc_fn(*args)
		if inspect.iscoroutine(_r):
			asyncio.create_task(_r)
		_on_cancel()

	with ui.dialog(value=True) as dialog, ui.card():
		ui.label(title).classes('text-h6')
		ui.label(message)
		with ui.row():
			ui.button('Cancel', color='secondary', on_click=_on_cancel).props('outline')
			ui.button(confirm_text, color=confirm_color, on_click=_on_confirm)
		dialog.on('close', dialog.clear)


def confirm_delete(obj, redirect_url: Union[str, GMBDElement]):
	"""Confirm deletion of an object before navigating away.

	Args:
		obj: Object with a ``delete`` method and optional ``on_delete`` hook.
		redirect_url: URL or element to visit after deletion.
	"""
	def _delete():
		"""Run the deletion hook, delete the object, and redirect."""
		if hasattr(obj, 'on_delete') and callable(obj.on_delete):
			obj.on_delete()
		obj.delete()
		goto(redirect_url)

	confirm('Delete confirmation', f'Are you sure you want to delete {type(obj).__name__} {obj}?', 'Yes', _delete,
			'negative')


def confirm_delete_relation(relation: str, start: GMBDElement, end: GMBDElement, redirect_url: Union[str, GMBDElement]):
	"""Confirm disconnection of two elements before navigating away.

	Args:
		relation: Relationship attribute on the starting element.
		start: Element owning the relationship.
		end: Element to disconnect.
		redirect_url: URL or element to visit after disconnection.
	"""
	def _delete():
		"""Disconnect the selected relationship and redirect."""
		start.__getattribute__(relation).disconnect(end)
		goto(redirect_url)

	confirm('Delete confirmation',
			f'Are you sure you want to delete \'{relation}\' relation from  {start.fqn} to {end.fqn}?', 'Yes', _delete,
			'negative')