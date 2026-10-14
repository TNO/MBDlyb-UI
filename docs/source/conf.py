# Copyright (c) 2023 - 2026 TNO-ESI
# All rights reserved.
"""Sphinx configuration for the MBDlyb-UI user documentation."""
from pathlib import Path

project = 'MBDlyb'
author = 'TNO-ESI'
copyright = '2023 - 2026, TNO-ESI'
release = '0.1.0'
version = release

extensions = [
	'sphinx.ext.autosectionlabel',
	'sphinx.ext.napoleon',
	'autoapi.extension',
]
autosectionlabel_prefix_document = True

# Code reference, generated from the docstrings by static analysis (the packages are not imported).
# The mbdlyb reference is only included when a checkout of mbdlyb sits next to this repository.
_MBDLYB_SRC = Path(__file__).resolve().parents[3] / 'mbdlyb' / 'src' / 'mbdlyb'
autoapi_type = 'python'
autoapi_dirs = ['../../src/mbdlyb_ui'] + ([str(_MBDLYB_SRC)] if _MBDLYB_SRC.is_dir() else [])
autoapi_root = 'api'
autoapi_add_toctree_entry = False
autoapi_keep_files = False
autoapi_member_order = 'groupwise'
autoapi_options = [
	'members',
	'undoc-members',
	'show-inheritance',
	'show-module-summary',
]
napoleon_google_docstring = True
napoleon_numpy_docstring = False
# Render "Attributes:" sections as fields, so they do not clash with the attributes AutoAPI documents itself.
napoleon_use_ivar = True
# 'ref.python': MBDlyb-UI helper classes share names with mbdlyb classes (e.g. AffectsRelation), which makes
# unqualified references in the combined reference ambiguous.
suppress_warnings = ['autoapi.python_import_resolution', 'ref.python']

exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
html_title = 'MBDlyb user guide'
html_static_path = ['_static']
html_css_files = ['custom.css']
html_theme_options = {
	'navigation_depth': 3,
	'collapse_navigation': False,
}
numfig = True

# Inline images of the buttons that are referred to in the text, e.g. |icon-diagnoser|.
_icons = [
	'diagnoser', 'design-for-diagnostics', 'check-model', 'download-graph', 'download-bayesnet', 'import-cluster',
	'download-all-cpts', 'download-required-cpts', 'import-cpts', 'copy-cluster', 'move-cluster', 'view-table',
	'edit', 'delete', 'add', 'row-cpt', 'row-edit', 'row-delete',
]
rst_prolog = '\n'.join(
	f'.. |icon-{name}| image:: /images/icons/{name}.png\n   :class: inline-icon\n   :alt: {name.replace("-", " ")}\n'
	for name in _icons)

latex_engine = 'xelatex'
latex_documents = [
	('index', 'mbdlyb-ui.tex', 'MBDlyb-UI user guide', author, 'manual'),
]
