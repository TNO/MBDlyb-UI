# -*- coding: utf-8 -*-
"""
	Copyright (c) 2023 - 2026 TNO-ESI
	All rights reserved.
"""
import io
import re
from typing import Optional

from nicegui import ui, run, app
from zipfile import ZipFile, ZIP_DEFLATED

from mbdlyb.colormap import ColorMap
from mbdlyb.functional import Cluster, Analyzer, DPTreeNode
from mbdlyb.functional.config import COLOR_MAP
from mbdlyb.functional.gdb import GCluster
from mbdlyb_ui import Button
from mbdlyb_ui.dialogs import confirm
from mbdlyb_ui.utils import Status, status
from mbdlyb_ui.helpers import goto, get_object_or_404

from .base import FunctionalPage
from .config import REASONER_CLASSES


class UIDesignForDiagnosticsData:
	"""Hold the design for diagnostics analysis and UI state."""

	compute_button: ui.button
	export_button: ui.button
	_cluster_id: str
	cluster: Cluster
	analyzer: Optional[Analyzer]
	costs_text: str = ''
	costs_visible: bool = False
	dp_to_export: list[str] = []
	dp_svg: dict[str, str] = {}
	results_available: bool = False

	def __init__(self, cluster_id: str):
		"""Initialize ui design for diagnostics data state for the selected cluster.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		self._cluster_id = cluster_id

	def reset(self):
		"""Clear analysis results and reload the cluster model."""
		status.refresh(Status.COMPUTING)
		self.results_available = False
		self.cluster = GCluster.load_from_db(self._cluster_id)
		reasoner_klass_name = app.storage.general.get('reasoner')
		reasoner_klass = REASONER_CLASSES[reasoner_klass_name]
		self.analyzer = Analyzer(self.cluster, reasoner_klass)
		self.refresh()
		status.refresh(Status.READY)

	async def compute(self, event=None):
		"""Analyze the cluster and refresh diagnostic design results.

		Args:
		    event: Optional UI event whose sender is disabled during computation.
		"""
		status.refresh(Status.COMPUTING)
		if event is not None:
			event.sender.disable()

		await run.io_bound(self.analyzer.analyze)
		self.results_available = True
		self.refresh()

		if event is not None:
			event.sender.enable()
		status.refresh(Status.READY)

	@staticmethod
	def refresh():
		"""Refresh operating modes, signatures, procedures, and overview."""
		operating_modes.refresh()
		signatures.refresh()
		diagnostic_procedures.refresh()
		overview.refresh()


class DesignForDiagnosticsPage(FunctionalPage):
	"""Display the design for diagnostics editing page."""

	cluster: GCluster
	data: UIDesignForDiagnosticsData

	def __init__(self, cluster_id: str):
		"""Load the design for diagnostics and configure its available actions.

		Args:
		    cluster_id: Identifier of the cluster to load.
		"""
		self.cluster = get_object_or_404(GCluster, uid=cluster_id)
		self.data = UIDesignForDiagnosticsData(cluster_id)
		super().__init__(f'Design for Diagnostics: {self.cluster.name}', self.cluster, [
			Button('Reset', 'restart_alt', 'negative', lambda: confirm('Reset design for diagnostics?', 'Are you sure you want to reset the design for diagnostics results?', 'Reset', self.data.reset, 'negative'), enabled_from=(self.data, 'results_available', None)),
			Button('Export', 'download', 'secondary', lambda: ui.download(self.data.analyzer.export(), f'design_for_diagnostics_{self.data.cluster.name}.xlsx'), enabled_from=(self.data, 'results_available', None)),
			Button('Close', 'arrow_back', 'secondary', lambda: goto(self.cluster))
		], status=Status.READY, force_hide_nav=True)
		self.data.reset()

	def _show_content(self):
		"""Display design analysis controls, signatures, and procedures."""
		with ui.grid(columns='1fr').classes('gap-1 min-w-[600px]'):
			with ui.column().classes('border rounded-borders p-2 h-full'):
				with ui.row().classes('w-full items-center'):
					ui.label('Operating modes').classes('text-h5')
					ui.space()
					Button('Compute', 'refresh', 'primary', lambda e: self.data.compute(e)).show().bind_visibility_from(self.data, 'results_available', value=False)
				operating_modes(self.data)
		with ui.grid(columns='1fr').classes('gap-1 min-w-[600px]').bind_visibility_from(self.data, 'results_available'):
			with ui.column().classes('border rounded-borders p-2 h-full'):
				with ui.row().classes('w-full items-center'):
					ui.label('Signatures').classes('text-h5')
					ui.space()
					filter = ui.input('Filter')
				signatures(self.data, filter)
		with ui.grid(columns='1fr').classes('gap-1 min-w-[600px]').bind_visibility_from(self.data, 'results_available'):
			with ui.column().classes('border rounded-borders p-2 h-full'):
				with ui.row().classes('w-full items-center'):
					ui.label('Diagnostic procedures').classes('text-h5')
					ui.space()
					button = Button('Export diagrams', enabled_from=(self.data, 'results_available', None)).show()
				diagnostic_procedures(self.data, button)
		with ui.grid(columns='1fr').classes('gap-1 min-w-[600px]').bind_visibility_from(self.data, 'results_available'):
			with ui.column().classes('border rounded-borders p-2 h-full'):
				with ui.row().classes('w-full items-center'):
					ui.label('Overview').classes('text-h5')
				overview(self.data)

@ui.refreshable
def operating_modes(data: UIDesignForDiagnosticsData):
	"""Display operating mode selections for the design analyzer.

	Args:
	    data: Design analyzer and selected operating mode state.
	"""
	async def _save(dt, dt_ev, exp):
		"""Apply the selected operating mode evidence to the design analyzer.

		Args:
		    dt: Selected diagnostic test associated with the evidence dialog.
		    dt_ev: Selected operating mode evidence by node name.
		    exp: Dialog to close after saving.
		"""
		data.analyzer.add_operating_mode({data.cluster.get_opm_node(n_fqn): ev for n_fqn, ev in dt_ev.items()})
		exp.close()
		exp.delete()

	with ui.scroll_area().classes('w-full'):
		if data.results_available:
			columns = [{'name': 'opm', 'label': 'Operating mode selector', 'field': 'opm', 'align': 'left'}, 
			           {'name': 'val', 'label': 'Selected mode', 'field': 'val', 'align': 'left'}]
			rows = [{'opm': str(opm), 'val': data.analyzer.selected_operating_modes[opm]} for opm in sorted(data.analyzer.selected_operating_modes)]
			unselected_opm = [opm for opm in data.cluster.get_all_opm_nodes().values() if opm not in data.analyzer.selected_operating_modes]
			rows += [{'opm': str(opm.fqn), 'val': ' | '.join(sorted(opm.states))} for opm in sorted(unselected_opm, key=lambda opm: str(opm.fqn))]
			ui.table(columns=columns, rows=rows, row_key='opm')
		else:
			for opm in data.cluster.get_all_opm_nodes().values():
				ev = dict()
				with ui.expansion(str(opm.fqn)).classes('w-full') as exp:
					ui.select(opm.states, label='Operating mode').bind_value(ev, str(opm.fqn)).classes('w-64')
					ui.button('Save', on_click=lambda t=opm, evd=ev, e=exp: _save(t, evd, e))


@ui.refreshable
def signatures(data: UIDesignForDiagnosticsData, filter: ui.input):
	"""Render the filterable diagnostic signature table.

	Args:
	    data: Design analyzer whose diagnostic signatures are displayed.
	    filter: Filter applied to displayed results.
	"""
	if data.analyzer is None or data.analyzer.signatures is None:
		ui.label('No results to show yet.').classes('text-grey')
		return
	
	signatures = data.analyzer.signatures.reset_index(level=['Node', 'State'])
	signatures['Node'] = signatures['Node'].apply(str)
	signatures.columns = list(map(str, signatures.columns))
	with ui.column().classes('p-2'):
		table = ui.table.from_pandas(signatures, pagination=0)
		table.bind_filter(filter, 'value')
	for col in table.columns:
		col['align'] = 'left'
		col['sortable'] = True

	# first render the entire table, fix the width of the first column and then enable pagination
	async def fix_table_width():
		"""Set the signature table pagination and column widths in the browser."""
		await ui.run_javascript(f'''
			el = document.querySelector("#c{str(table.id)} th");
			el.width = el.offsetWidth;
		''')
		table.pagination = {'rowsPerPage': 10, 'sortBy': 'Node'}
		button.set_visibility(False)
	button = ui.button('Fix width', on_click=fix_table_width)
	button.run_method('click')


class DiagnosticProcedureDiagram:
	"""Build a Mermaid diagram of a diagnostic procedure."""

	_node_cnt: int
	_diagram: list[str]

	def __init__(self, data: UIDesignForDiagnosticsData, dp_name: str):
		"""Build the procedure tree diagram with node styling.

		Args:
		    data: Design analysis containing the selected procedure tree.
		    dp_name: Name of the diagnostic procedure.
		"""
		root_node = data.analyzer.get_diagnostic_procedure_tree(dp_name)

		# start drawing at the root-node
		self._node_cnt = 0
		self._diagram = ['flowchart']
		self._diagram.append(f'subgraph "<b>{dp_name}</b>"')
		self._diagram.append('direction TB')
		self._draw_node(root_node)

		# close diagnostic procedure
		self._diagram.append('end')

		# add color mapping
		colormap = COLOR_MAP + ColorMap({'NonDiagnosableHW': 'red'})
		for type_name in root_node.collect_types():
			self._diagram.append(f'classDef {type_name} fill:{colormap.get_color(type_name)};')

	def _draw_node(self, node: DPTreeNode, prev_node: int = 0, edge_label: str = ''):
		"""Append a diagnostic procedure node and its incoming edge to the diagram.

		Args:
		    node: Functional node selected for this operation.
		    prev_node: Parent node in the diagnostic procedure diagram.
		    edge_label: Label for the incoming diagram edge.
		"""
		self._node_cnt += 1
		new_node = self._node_cnt
		if node.type == 'Hardware' or node.type == 'NonDiagnosableHW':
			hw_names = '<br/>-----<br/>'.join(node.name.split('\n'))
			self._diagram.append(f'{new_node}[[{hw_names}]]')
		else:
			self._diagram.append(f'{new_node}{{{{{node.name}}}}}')
		if node.type == 'NonDiagnosableHW':
			self._diagram.append(f'class {new_node} NonDiagnosableHW')
		else:
			self._diagram.append(f'class {new_node} {node.type}')
		self._diagram.append(f'click {new_node} call emitEvent("mermaid_click", "{node.name}", "{node.cost}")')
		if edge_label:
			self._diagram.append(f'{prev_node} --> |{edge_label}| {new_node}')

		for edge in node.edges:
			edge_label = '<br/>'.join([f'{result_name} = {value}' for result_name, value in edge.results])
			self._draw_node(edge.target, new_node, edge_label)

	@property
	def diagram(self) -> str:
		"""Join the generated diagnostic procedure diagram lines.

		Returns:
		    Mermaid source for the diagnostic procedure diagram.
		"""
		return '\n'.join(self._diagram)


@ui.refreshable
def diagnostic_procedures(data: UIDesignForDiagnosticsData, export_button: ui.button):
	"""Render diagnostic procedures and diagram export controls.

	Args:
	    data: Design analyzer and procedure diagram export state.
	    export_button: Button used to start diagram export.
	"""
	if data.analyzer is None or data.analyzer.dps is None:
		ui.label('No results to show yet.').classes('text-grey')
		return

	def update_costs_label(name: str, costs: str):
		"""Show the costs for the selected diagnostic procedure.

		Args:
		    name: Diagnostic procedure name shown in the cost label.
		    costs: Formatted costs for the selected procedure.
		"""
		name = ', '.join(name.split('\n'))
		data.costs_text = f'Costs for <b>{name}</b>: {costs}'
		data.costs_visible = True

	def hide_costs_label():
		"""Hide the diagnostic procedure cost label."""
		data.costs_visible = False

	dp_names = sorted(data.analyzer.dps.keys())
	dp_tabs = dict()
	with ui.tabs().classes('px-2') as tabs:
		for dp_name in dp_names:
			dp_tabs[dp_name] = ui.tab(dp_name)
	tabs.on_value_change(hide_costs_label)
	mermaid_ids = {}
	with ui.tab_panels(tabs) as panels:
		for dp_name in dp_names:
			with ui.tab_panel(dp_tabs[dp_name]).classes('p-2') as tab_panel:
				panels.value = panels.value or tab_panel
				dp = data.analyzer.dps[dp_name].reset_index(level=['Node', 'State'])
				dp['Node'] = dp['Node'].apply(str)
				dp.columns = list(map(str, dp.columns))				
				table = ui.table.from_pandas(dp, pagination={'rowsPerPage': 0, 'sortBy': 'Node'})
				for col in table.columns:
					col['align'] = 'left'
					col['sortable'] = True
				dpd = DiagnosticProcedureDiagram(data, dp_name)
				mermaid_config = {
					'securityLevel': 'loose',
					'theme': 'neutral',
					'themeVariables': {
						'fontSize': '14px'
					}
				}
				mm = ui.mermaid(dpd.diagram, config=mermaid_config).classes('w-full')
				mermaid_ids[dp_name] = mm.id
	ui.html(sanitize=False).bind_content_from(data, 'costs_text').bind_visibility_from(data, 'costs_visible')
	ui.on('mermaid_click', lambda event: update_costs_label(*event.args))
	
	def export_start():
		"""Initialize SVG collection for the selected diagnostic procedures."""
		data.dp_to_export = dp_names
		data.dp_svg = {}
		export_store_svg()
	export_button.on_click(export_start)

	def export_store_svg(svg = None):
		"""Add rendered procedure SVGs to the pending export.

		Args:
		    svg: Rendered SVG content keyed by procedure.
		"""
		svg = svg or {}
		data.dp_svg |= svg
		if data.dp_to_export:
			dp = data.dp_to_export.pop()
			tabs.set_value(dp)
			export_switch_tab()
		else:
			ui.download(
				export_zip_svg(data.dp_svg, data.cluster.name),
				f'diagnostic_procedures_{data.cluster.name}.zip')

	def export_switch_tab():
		"""Switch to the next diagnostic procedure tab for export."""
		dp = tabs.value._props['name'] if isinstance(tabs.value, ui.tab_panel) else tabs.value			
		id = mermaid_ids[dp]
		ui.run_javascript(f'''
			svg = document.querySelector("#c" + {id} + " > svg");
			emitEvent('mermaid_export', {{
				{dp}: svg.outerHTML,
			}});
		''')
	ui.on('mermaid_export', lambda evt: export_store_svg(evt.args))

	def export_zip_svg(all_svg: dict[str,str], cluster_name: str) -> bytes:
		"""Archive rendered procedure SVGs and return the ZIP bytes.

		Args:
		    all_svg: Rendered SVGs to include in the archive.
		    cluster_name: Cluster name used for the download filename.

		Returns:
		    ZIP archive bytes containing the procedure SVGs.
		"""
		bytes = io.BytesIO()
		z = ZipFile(bytes, 'w', compression=ZIP_DEFLATED, compresslevel=5)
		for dp_name, svg in all_svg.items():
			svg = svg.replace(r'<br>', r'<br/>')
			svg = re.sub(r'id="<b>(.*)</b>"', r'id="\1"', svg)
			z.writestr(f'{cluster_name}-{dp_name}.svg', svg)
		z.close()
		bytes.seek(0,0)
		return bytes.read()


@ui.refreshable
def overview(data: UIDesignForDiagnosticsData):
	"""Render the design-for-diagnostics overview table.

	Args:
	    data: Design analyzer whose procedure overview is displayed.
	"""
	if data.analyzer is None or data.analyzer.overview is None:
		ui.label('No results to show yet.').classes('text-grey')
		return

	overview = data.analyzer.overview.rename_axis('DP').reset_index()
	with ui.column().classes('p-2'):
		table = ui.table.from_pandas(overview, pagination={'rowsPerPage': 0, 'sortBy': 'DP'})
	for col in table.columns:
		col['align'] = 'left'
		col['sortable'] = True
