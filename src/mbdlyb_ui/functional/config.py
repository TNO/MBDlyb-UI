# -*- coding: utf-8 -*-
"""
	Copyright (c) 2026 TNO-ESI
	All rights reserved.
"""
from mbdlyb.formalisms.bayesnet import BayesNetReasoner
from mbdlyb.formalisms.tensornet import TensorNetReasoner
from mbdlyb.formalisms.markovnet import MarkovNetReasoner

from mbdlyb.functional.gdb import (GSubfunctionOfRelation, GYieldsErrorRelation, GReportsErrorRelation,
								   GRealizesRelation, GObservedByRelation, GResultsInRelation, GIndicatedByRelation,
								   GCluster, GFunction, GHardware, GDirectObservable, GDiagnosticTest,
								   GDiagnosticTestResult, GOperatingMode, GRequiredForRelation, GAffectsRelation)

URL_RESOLVER = {
	GCluster: '/cluster/{}',
	GFunction: '/function/{}',
	GHardware: '/hardware/{}',
	GDirectObservable: '/observable/{}',
	GDiagnosticTest: '/test/{}',
	GDiagnosticTestResult: lambda dtr: f'/test/{dtr.test.uid}',
	GOperatingMode: '/opm/{}',

	GRealizesRelation: lambda r: f'/hardware/{r.start_node().uid}/realizes/{r.end_node().uid}/update/',
	GRequiredForRelation: lambda r: f'/function/{r.start_node().uid}/requiredfor/{r.end_node().uid}/update/',
	GAffectsRelation: lambda r: f'/hardware/{r.start_node().uid}/affects/{r.end_node().uid}/update/',
	GSubfunctionOfRelation: lambda r: f'/function/{r.end_node().uid}/subfunction/{r.start_node().uid}/update/',

}

REASONER_CLASSES = {'BayesNetReasoner': BayesNetReasoner,
					'TensorNetReasoner': TensorNetReasoner,
					'MarkovNetReasoner': MarkovNetReasoner}

MERMAID_ATTRIBUTES = {
	GCluster: ['observables', 'tests', 'test_results', 'functions', 'hardware'],
	GDirectObservable: (
		[(GObservedByRelation, 'observed_hardware'), (GObservedByRelation, 'observed_functions')],
		[]
	),
	GDiagnosticTest: (
		[],
		[(GResultsInRelation, 'test_results')],
	),
	GDiagnosticTestResult: (
		[(GIndicatedByRelation, 'indicated_functions'), (GIndicatedByRelation, 'indicated_hardware')],
		[]
	),
	GFunction: (
		[(GSubfunctionOfRelation, 'subfunctions', ([], [(GRequiredForRelation, 'required_for')]))],
		[(GRequiredForRelation, 'required_for'), (GYieldsErrorRelation, 'yields_error'),
		 (GReportsErrorRelation, 'reports_error')]
	),
	GHardware: (
		[],
		[(GRealizesRelation, 'realizes')]
	)
}
