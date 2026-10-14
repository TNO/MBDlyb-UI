# -*- coding: utf-8 -*-
"""
	Copyright (c) 2026 TNO-ESI
	All rights reserved.

Capture the screenshots used in the MBDlyb-UI user documentation.

The script drives a running MBDlyb-UI instance with a headless Chromium browser
(Playwright) and stores the images in ``docs/source/images``. It only navigates
and opens forms/dialogs; it never presses *Save* on model forms, so the model in
the database is not modified. The diagnoser and design-for-diagnostics pages
only compute in memory.

Prerequisites:

* A running MBDlyb-UI connected to a database that contains the
  ``CDRadioPlayer`` example model (see the "Example projects" section of the
  documentation).
* ``uv sync --group screenshots`` and
  ``uv run --group screenshots playwright install chromium``.

Usage::

	uv run --group screenshots python docs/tools/capture_screenshots.py --url http://localhost:8080 --database neo4j

The application mode (Editor/Tree) that is active before running the script is
restored afterwards.
"""
import argparse
import asyncio
from pathlib import Path
from typing import Optional

from neo4j import GraphDatabase
from playwright.async_api import Page, async_playwright

ROOT = 'CDRadioPlayer'
OUT_DIR = Path(__file__).resolve().parents[1] / 'source' / 'images'
SHOTS = OUT_DIR / 'screenshots'
ICONS = OUT_DIR / 'icons'
WIDTH, HEIGHT = 1400, 900


class Capturer:
	"""Take screenshots of pages of a running MBDlyb-UI instance."""

	def __init__(self, page: Page, url: str, uids: dict[str, str]):
		self.page = page
		self.url = url.rstrip('/')
		self.uids = uids
		self.width = WIDTH

	def uid(self, fqn: str) -> str:
		"""Return the uid of an element, given its FQN relative to the root cluster."""
		return self.uids[f'{ROOT}.{fqn}' if fqn else ROOT]

	async def goto(self, path: str, wait: int = 1500):
		await self.page.set_viewport_size({'width': self.width, 'height': HEIGHT})
		await self.page.goto(f'{self.url}{path}')
		await self.page.wait_for_load_state('networkidle')
		await self.page.wait_for_timeout(wait)

	async def shot(self, name: str, full: bool = True, height: Optional[int] = None):
		"""Store a screenshot of the viewport, optionally grown to fit all content.

		Growing the viewport (instead of a Playwright full-page capture) keeps the
		fixed header, footer and navigation drawer in place.
		"""
		if full or height:
			h = height or await self.page.evaluate('document.documentElement.scrollHeight')
			await self.page.set_viewport_size({'width': self.width, 'height': max(int(h), 400)})
			await self.page.wait_for_timeout(700)
		await self.page.screenshot(path=SHOTS / f'{name}.png')
		await self.page.set_viewport_size({'width': self.width, 'height': HEIGHT})
		print(f'  screenshot {name}')

	async def shot_locator(self, name: str, locator, folder: Path = SHOTS, padding: int = 0, max_width: int = 0):
		"""Store a screenshot of a single element, optionally with padding and a maximum width.

		The viewport is first grown to the full page height, so fixed elements (header, footer)
		do not overlap tall elements.
		"""
		h = await self.page.evaluate('document.documentElement.scrollHeight')
		await self.page.set_viewport_size({'width': self.width, 'height': max(int(h), HEIGHT)})
		await self.page.wait_for_timeout(500)
		box = await locator.bounding_box()
		width = min(box['width'], max_width) if max_width else box['width']
		await self.page.screenshot(path=folder / f'{name}.png', clip={
			'x': max(box['x'] - padding, 0), 'y': max(box['y'] - padding, 0),
			'width': width + 2 * padding, 'height': box['height'] + 2 * padding})
		await self.page.set_viewport_size({'width': self.width, 'height': HEIGHT})
		print(f'  {"icon" if folder == ICONS else "screenshot"} {name}')

	async def mode(self) -> str:
		await self.goto('/', 500)
		return (await self.page.locator('.q-btn-toggle button[aria-pressed="true"]').inner_text()).strip().title()

	async def set_mode(self, mode: str):
		await self.goto('/', 500)
		await self.page.locator('.q-btn-toggle button', has_text=mode.upper()).click()
		await self.page.wait_for_timeout(1500)

	async def select_option(self, scope, option: str):
		"""Pick an option from the (first) Quasar select in the given scope."""
		await scope.locator('.q-select').first.click()
		await self.page.locator('.q-menu .q-item', has_text=option).first.click()
		await self.page.wait_for_timeout(300)

	async def wait_ready(self, timeout: int = 180_000):
		"""Wait until the page status indicator no longer shows a computation."""
		await self.page.wait_for_timeout(1000)
		await self.page.wait_for_function('!document.querySelector(".q-spinner")', timeout=timeout)
		await self.page.wait_for_timeout(1000)

	def title_buttons(self):
		return self.page.locator('.q-page .q-btn-group button')

	def expansion(self, label: str):
		return self.page.locator('.q-expansion-item', has=self.page.locator('.q-item__label', has_text=label)).first


async def capture_tree_mode(c: Capturer):
	print('Tree mode')
	await c.set_mode('Tree')
	await c.goto('/')
	await c.shot('landing-tree', full=False, height=450)

	await c.goto(f'/cluster/{c.uid("")}/')
	for name in ('CDReader', 'Detector'):
		row_button = c.page.locator('.q-page button', has_text=name).first
		await row_button.locator('xpath=preceding-sibling::i[1]').click()
		await c.page.wait_for_timeout(300)
	await c.page.locator('.q-page button', has_text='DetectReflectedLaser').first.click()
	await c.page.wait_for_timeout(800)
	await c.shot('cluster-tree')


async def capture_editor_mode(c: Capturer):
	print('Editor mode')
	await c.set_mode('Editor')
	await c.goto('/')
	await c.shot('landing-editor', full=False, height=450)
	await c.shot_locator('header', c.page.locator('.q-header'))

	await c.goto(f'/cluster/{c.uid("")}/', 3000)
	await c.shot('cluster-editor-root')
	await c.shot_locator('cluster-buttons', c.page.locator('.q-page .text-h5').first.locator('xpath=..'), padding=4)

	names = ['diagnoser', 'design-for-diagnostics', 'check-model', 'download-graph', 'download-bayesnet',
			 'import-cluster', 'download-all-cpts', 'download-required-cpts', 'import-cpts', 'copy-cluster',
			 'view-table', 'edit', 'delete']
	for i, name in enumerate(names):
		await c.shot_locator(name, c.title_buttons().nth(i), ICONS)

	# A cluster with hardware, an operating mode selector, and a move button (non-root)
	await c.goto(f'/cluster/{c.uid("PowerSystem.PowerBoard")}/', 3000)
	await c.shot('cluster-editor-powerboard')
	await c.shot_locator('move-cluster', c.title_buttons().nth(8), ICONS)
	cards = c.page.locator('.q-page .q-card')
	await c.shot_locator('cluster-diagram', cards.nth(0))
	await c.shot_locator('table-functions', cards.nth(1))
	await c.shot_locator('table-hardware', cards.nth(2))
	await c.shot_locator('table-opm', cards.nth(6))
	row_icons = cards.nth(1).locator('.q-icon.cursor-pointer')
	for i, name in enumerate(['row-cpt', 'row-edit', 'row-delete']):
		await c.shot_locator(name, row_icons.nth(i), ICONS, padding=3)
	await c.shot_locator('add', cards.nth(1).locator('button').first, ICONS)

	await c.goto(f'/cluster/{c.uid("CDReader")}/', 3000)
	await c.shot_locator('cluster-diagram-cdreader', c.page.locator('.q-page .q-card').first)

	# Settings dialog
	await c.page.locator('.q-header .q-icon', has_text='settings').click()
	await c.page.wait_for_timeout(600)
	await c.shot_locator('settings-dialog', c.page.locator('.q-dialog .q-card'))
	await c.page.keyboard.press('Escape')

	# Move dialog (cancelled, nothing is moved)
	await c.goto(f'/cluster/{c.uid("PowerSystem.Battery")}/', 1500)
	await c.title_buttons().nth(8).click()
	await c.page.wait_for_timeout(800)
	await c.shot_locator('move-cluster-dialog', c.page.locator('.q-dialog .q-card'))
	await c.page.locator('.q-dialog button', has_text='Cancel').click()


async def capture_elements(c: Capturer):
	print('Element pages')
	pages: list[tuple[str, str]] = [
		('cluster-new', f'/cluster/{c.uid("PowerSystem")}/new'),
		('function-detail', f'/function/{c.uid("PowerSystem.PowerBoard.DistributePower")}/'),
		('function-new', f'/cluster/{c.uid("PowerSystem.PowerBoard")}/function/new'),
		('function-update-states', f'/function/{c.uid("CDReader.Detector.DetectReflectedLaser")}/update'),
		('subfunction-new', f'/function/{c.uid("PowerSystem.ProvidePower")}/subfunction/new'),
		('requiredfor-new', f'/function/{c.uid("PowerSystem.Battery.SupplyPowerFromBattery")}/requiredfor/new'),
		('requiredfor-update',
		 f'/function/{c.uid("PowerSystem.Battery.SupplyPowerFromBattery")}/requiredfor/'
		 f'{c.uid("PowerSystem.PowerBoard.DistributePower")}/update'),
		('requiredfor-table', f'/cluster/{c.uid("PowerSystem")}/requiredfor'),
		('hardware-detail', f'/hardware/{c.uid("PowerSystem.PowerBoard.PowerBoard")}/'),
		('hardware-update', f'/hardware/{c.uid("CDReader.Detector.Detector")}/update'),
		('realizes-new', f'/hardware/{c.uid("PowerSystem.PowerBoard.PowerBoard")}/realizes/new'),
		('observable-new', f'/cluster/{c.uid("PowerSystem.LED")}/observable/new'),
		('test-detail', f'/test/{c.uid("CDReader.Test_ReadCD")}/'),
		('test-new', f'/cluster/{c.uid("CDReader")}/test/new'),
		('test-result-tested-items', f'/test_result/{c.uid("CDReader.Test_ReadCD_Result")}/tests'),
		('test-result-update', f'/test_result/{c.uid("CDReader.Test_ReadCD_Result")}/update'),
		('opm-detail', f'/opm/{c.uid("PowerSystem.PowerBoard.Select_BatteryPower_WallPower")}/'),
		('opm-update', f'/opm/{c.uid("PowerSystem.PowerBoard.Select_BatteryPower_WallPower")}/update'),
		('cpt-editor', f'/function/{c.uid("CDReader.Detector.DetectReflectedLaser")}/cpt'),
		('cpt-import', f'/cluster/{c.uid("")}/import_cpt'),
		('capella-import', '/cluster/import'),
	]
	for name, path in pages:
		await c.goto(path)
		await c.shot(name)


async def capture_validator(c: Capturer):
	print('Validator')
	await c.goto(f'/cluster/{c.uid("")}/validator')
	await c.wait_ready()
	await c.shot('validator', full=False, height=300)


async def capture_diagnoser(c: Capturer):
	print('Diagnoser')
	await c.goto(f'/cluster/{c.uid("")}/diagnoser')
	await c.wait_ready()
	await c.shot('diagnoser-initial')
	await c.shot_locator('diagnoser-toolbar', c.page.locator('.q-page .q-slider').locator(
		'xpath=ancestor::div[contains(@class,"row")][1]'), padding=4)

	async def enter(name: str, value: str, shot: Optional[str] = None):
		exp = c.expansion(name)
		await exp.locator('.q-item').first.click()
		await c.page.wait_for_timeout(400)
		await c.select_option(exp, value)
		if shot:
			await c.shot_locator(shot, exp, padding=4)
		await exp.locator('button', has_text='Save').click()
		await c.page.wait_for_timeout(800)

	async def compute(shot: str):
		await c.page.locator('.q-page button', has_text='Compute').first.click()
		await c.wait_ready()
		await c.shot(shot)

	# Scenario: the player runs on batteries, does not play CDs and shows a CD error on the display.
	await enter('Select_BatteryPower_WallPower', 'BatteryPower', 'diagnoser-enter-opm')
	await enter('CD_ERROR', 'Present', 'diagnoser-enter-observable')
	await c.shot('diagnoser-staged')
	await compute('diagnoser-computed')

	# The radio still works.
	await enter('Test_PlayRadio', 'Ok', 'diagnoser-enter-test')
	await compute('diagnoser-computed-2')

	await c.page.locator('.q-page button', has=c.page.locator('.q-icon', has_text='insert_chart')).click()
	await c.page.wait_for_timeout(2500)
	await c.shot_locator('diagnoser-plot', c.page.locator('.q-dialog .q-card'))
	await c.page.locator('.q-dialog button', has_text='Close').click()
	await c.page.wait_for_timeout(500)

	await c.page.locator('.q-page .q-checkbox', has_text='Soft evidence').click()
	await c.page.wait_for_timeout(800)
	exp = c.expansion('Inspect')
	await exp.locator('.q-item').first.click()
	await c.page.wait_for_timeout(500)
	await c.shot_locator('diagnoser-soft-evidence', exp, padding=4)


async def capture_dfd(c: Capturer):
	print('Design for diagnostics')
	await c.goto(f'/cluster/{c.uid("")}/design_for_diagnostics')
	await c.wait_ready()
	await c.shot('dfd-initial', full=False, height=500)
	exp = c.expansion('Select_BatteryPower_WallPower')
	await exp.locator('.q-item').first.click()
	await c.page.wait_for_timeout(400)
	await c.select_option(exp, 'WallPower')
	await exp.locator('button', has_text='Save').click()
	await c.page.wait_for_timeout(400)
	await c.page.locator('.q-page button', has_text='Compute').first.click()
	await c.wait_ready(600_000)
	await c.page.wait_for_timeout(3000)
	await c.shot('dfd-results')
	sections = c.page.locator('.q-page .nicegui-grid')
	for i, name in enumerate(['dfd-opm', 'dfd-signatures', 'dfd-procedures', 'dfd-overview']):
		await c.shot_locator(name, sections.nth(i), max_width=WIDTH - 40)
	await c.shot_locator('dfd-procedure-tree', c.page.locator('.q-tab-panel svg').first.locator('xpath=..'))


def load_uids(args) -> dict[str, str]:
	driver = GraphDatabase.driver(f'{args.protocol}://{args.host}:{args.port}', auth=(args.username, args.password))
	with driver.session(database=args.database) as s:
		uids = {r['fqn']: r['uid'] for r in s.run(
			'MATCH (n) WHERE n.uid IS NOT NULL AND n.fqn STARTS WITH $root RETURN n.fqn AS fqn, n.uid AS uid',
			root=ROOT)}
	driver.close()
	if ROOT not in uids:
		raise SystemExit(f'Example model {ROOT} not found in database {args.database}.')
	return uids


GROUPS = {'tree': capture_tree_mode, 'editor': capture_editor_mode, 'elements': capture_elements,
		  'validator': capture_validator, 'diagnoser': capture_diagnoser, 'dfd': capture_dfd}


async def main():
	parser = argparse.ArgumentParser(description='Capture the screenshots of the MBDlyb-UI documentation.')
	parser.add_argument('--url', default='http://localhost:8080', help='URL of the running MBDlyb-UI.')
	parser.add_argument('--host', default='localhost', help='Hostname of the neo4j database.')
	parser.add_argument('--port', default=7687, type=int, help='Port of the neo4j database.')
	parser.add_argument('--protocol', default='bolt', help='Protocol to connect to the neo4j database.')
	parser.add_argument('--username', default='neo4j', help='Username for neo4j authentication.')
	parser.add_argument('--password', default='password', help='Password for neo4j authentication.')
	parser.add_argument('--database', default='neo4j', help='Name of the neo4j database used by MBDlyb-UI.')
	parser.add_argument('--only', nargs='*', choices=list(GROUPS), help='Only capture the given groups.')
	args = parser.parse_args()

	SHOTS.mkdir(parents=True, exist_ok=True)
	ICONS.mkdir(parents=True, exist_ok=True)
	uids = load_uids(args)

	async with async_playwright() as p:
		browser = await p.chromium.launch()
		page = await browser.new_page(viewport={'width': WIDTH, 'height': HEIGHT})
		c = Capturer(page, args.url, uids)
		original_mode = await c.mode()
		try:
			for key, group in GROUPS.items():
				if args.only and key not in args.only:
					continue
				if key not in ('tree', 'editor'):
					await c.set_mode('Editor')
				await group(c)
		finally:
			await c.set_mode(original_mode)
			await browser.close()


if __name__ == '__main__':
	asyncio.run(main())
