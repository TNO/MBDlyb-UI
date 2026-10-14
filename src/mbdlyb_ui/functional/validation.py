# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
from typing import Optional

from mbdlyb.gdb import GMBDElement
from mbdlyb.functional.gdb import GCluster
from mbdlyb_ui.validation import base_name_validation as bnv


def base_name_validation(cluster: Optional[GCluster] = None, element: Optional[GMBDElement] = None, allow_empty: bool = False):
	"""Build name validators for a node within its parent cluster.

	Args:
	    cluster: Cluster defining the name's uniqueness scope; defaults to the cluster class.
	    element: Model element displayed on the page.
	    allow_empty: Whether an empty name is accepted.

	Returns:
	    Name validation rules for the specified cluster and element.
	"""
	return bnv(GCluster if cluster is None else cluster, element, allow_empty)
