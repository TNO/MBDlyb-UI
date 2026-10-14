# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
import re
from typing import Optional, Union

from mbdlyb.gdb import GMBDNet, GMBDElement


def valid_name(s: str) -> bool:
	"""Check that a name contains only ASCII letters, digits, underscores, or hyphens.

	Args:
		s: Proposed name.

	Returns:
		Whether all characters in the name are allowed.
	"""
	return bool(re.match('^[a-zA-Z0-9_-]*$', s))


def base_name_validation(context: Union[GMBDNet, type[GMBDNet]], element: Optional[GMBDElement] = None,
                         allow_empty: bool = False):
	"""Build NiceGUI validators for a name within a network or root node class.

	Args:
		context: Network whose children must have distinct names, or root node class.
		element: Existing element to exclude when checking duplicate names.
		allow_empty: Whether an empty name is permitted.

	Returns:
		A mapping of error messages to name-checking callables.
	"""
	validation = {
		'Invalid characters used': valid_name
	}
	if not allow_empty:
		validation['Required field'] = lambda s: s != ''
	elements = set(context.elements.all()) if isinstance(context, GMBDNet) else {c for c in context.nodes.filter(
		net__exists=False)}
	children = {e.name for e in elements if element is None or e != element}
	validation['Name already exists'] = lambda s: s not in children
	return validation
