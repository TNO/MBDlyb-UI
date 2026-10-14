# -*- coding: utf-8 -*-
"""
	Copyright (c) 2026 TNO-ESI
	All rights reserved.
"""

from nicegui import APIRouter

from .clusters import (ClusterCreatePage, ClusterImportPage, ClusterUpdatePage, ClusterDetailPage, CPTImportPage,
                       RequiredForTablePage)
from .functions import (FunctionCreatePage, FunctionUpdatePage, FunctionDetailPage, SubfunctionRelationCreatePage,
						SubfunctionRelationUpdatePage, SubfunctionRelationTablePage, RequiredForRelationCreatePage,
						RequiredForRelationUpdatePage, RequiredForRelationRepairPage,
						ObservesRelationCreatePage as ObservesFunctionRelationCreatePage,
						ObservesRelationUpdatePage as ObservesFunctionRelationUpdatePage,
						TestsRelationCreatePage as TestsFunctionRelationCreatePage,
						TestsRelationUpdatePage as TestsFunctionRelationUpdatePage, FunctionCPTPage)
from .hardware import (HardwareCreatePage, HardwareUpdatePage, HardwareDetailsPage, RealizesRelationCreatePage,
					   RealizesRelationUpdatePage, AffectsRelationCreatePage, AffectsRelationUpdatePage,
					   ObservesRelationCreatePage as ObservesHardwareRelationCreatePage,
					   ObservesRelationUpdatePage as ObservesHardwareRelationUpdatePage,
					   TestsRelationCreatePage as TestsHardwareRelationCreatePage,
					   TestsRelationUpdatePage as TestsHardwareRelationUpdatePage)
from .observables import (ObservableCreatePage, ObservableUpdatePage, ObservableDetailsPage,
						  ObservesFunctionRelationPage, ObservesHardwareRelationPage, ObservableCPTPage)
from .diagnostic_tests import TestUpdatePage, TestDetailsPage
from .diagnostic_test_results import TestResultUpdatePage, TestResultRelationPage, TestResultCPTPage
from .operating_modes import OpmUpdatePage, OpmDetailsPage
from .validator import ValidatorPage
from .design_for_diagnostics import DesignForDiagnosticsPage
from .diagnoser import DiagnoserPage

cluster_router = APIRouter(prefix='/cluster')
cluster_id_router = APIRouter(prefix='/{cluster_id}')

@cluster_router.page('/new')
def cluster_create_root():
	"""Load and display the cluster create page."""
	ClusterCreatePage().show()

@cluster_router.page('/import')
def cluster_import_root():
	"""Load and display the cluster import page."""
	ClusterImportPage().show()

@cluster_id_router.page('/')
def cluster_details(cluster_id: str):
	"""Load and display the cluster detail page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	ClusterDetailPage(cluster_id).show()

@cluster_id_router.page('/new')
def cluster_create_with_parent(cluster_id: str):
	"""Load and display the cluster create page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	ClusterCreatePage(cluster_id).show()

@cluster_id_router.page('/update')
def cluster_update(cluster_id: str):
	"""Load and display the cluster update page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	ClusterUpdatePage(cluster_id).show()

@cluster_id_router.page('/requiredfor')
def required_for_table(cluster_id: str):
	"""Render the required for table and its controls.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	RequiredForTablePage(cluster_id).show()

@cluster_id_router.page('/import')
def cluster_import_with_parent(cluster_id: str):
	"""Load and display the cluster import page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	ClusterImportPage(cluster_id).show()

@cluster_id_router.page('/import_cpt')
def cpt_import(cluster_id: str):
	"""Load and display the cpt import page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	CPTImportPage(cluster_id).show()

@cluster_id_router.page('/validator')
def validator_main(cluster_id: str):
	"""Load and display the validator page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	ValidatorPage(cluster_id).show()

@cluster_id_router.page('/design_for_diagnostics')
def design_for_diagnostics_main(cluster_id: str):
	"""Load and display the design for diagnostics page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	DesignForDiagnosticsPage(cluster_id).show()

@cluster_id_router.page('/diagnoser')
def diagnoser_main(cluster_id: str):
	"""Load and display the diagnoser page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	DiagnoserPage(cluster_id).show()


function_router = APIRouter(prefix='/function/{function_id}')

@cluster_id_router.page('/function/new')
def function_create(cluster_id: str):
	"""Load and display the function create page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	FunctionCreatePage(cluster_id).show()

@function_router.page('/update')
def function_update(function_id: str):
	"""Load and display the function update page.

	Args:
	    function_id: Identifier of the function to load.
	"""
	FunctionUpdatePage(function_id).show()

@function_router.page('/')
def function_details(function_id: str):
	"""Load and display the function detail page.

	Args:
	    function_id: Identifier of the function to load.
	"""
	FunctionDetailPage(function_id).show()

@function_router.page('/subfunction/new')
def subfunction_relation_create(function_id: str):
	"""Load and display the subfunction relation create page.

	Args:
	    function_id: Identifier of the function to load.
	"""
	SubfunctionRelationCreatePage(function_id).show()

@function_router.page('/subfunction/{subfunction_id}/update')
def subfunction_relation_update(function_id: str, subfunction_id: str):
	"""Load and display the subfunction relation update page.

	Args:
	    function_id: Identifier of the function to load.
	    subfunction_id: Identifier of the subfunction to edit.
	"""
	SubfunctionRelationUpdatePage(function_id, subfunction_id).show()

@function_router.page('/subfunction')
def subfunction_relation_table(function_id: str):
	"""Render the subfunction relation table and its controls.

	Args:
	    function_id: Identifier of the function to load.
	"""
	SubfunctionRelationTablePage(function_id).show()

@function_router.page('/requiredfor/new')
def requiredfor_relation_create(function_id: str):
	"""Load and display the required for relation create page.

	Args:
	    function_id: Identifier of the function to load.
	"""
	RequiredForRelationCreatePage(function_id).show()

@function_router.page('/requiredfor/{dep_function_id}/update')
def requiredfor_relation_update(function_id: str, dep_function_id: str):
	"""Load and display the required for relation update page.

	Args:
	    function_id: Identifier of the function to load.
	    dep_function_id: Identifier of the dependent function.
	"""
	RequiredForRelationUpdatePage(function_id, dep_function_id).show()

@function_router.page('/requiredfor/{dep_function_id}/repair')
def requiredfor_relation_repair(function_id: str, dep_function_id: str):
	"""Load and display the required for relation repair page.

	Args:
	    function_id: Identifier of the function to load.
	    dep_function_id: Identifier of the dependent function.
	"""
	RequiredForRelationRepairPage(function_id, dep_function_id).show()

@function_router.page('/observedby/new')
def function_observes_relation_create(function_id: str):
	"""Load and display the observes function relation create page.

	Args:
	    function_id: Identifier of the function to load.
	"""
	ObservesFunctionRelationCreatePage(function_id).show()

@function_router.page('/observedby/{observable_id}/update')
def function_observes_relation_update(function_id: str, observable_id: str):
	"""Load and display the observes function relation update page.

	Args:
	    function_id: Identifier of the function to load.
	    observable_id: Identifier of the observable to load.
	"""
	ObservesFunctionRelationUpdatePage(function_id, observable_id).show()

@function_router.page('/testedby/new')
def function_tests_relation_create(function_id: str):
	"""Load and display the tests function relation create page.

	Args:
	    function_id: Identifier of the function to load.
	"""
	TestsFunctionRelationCreatePage(function_id).show()

@function_router.page('/testedby/{test_id}/update')
def function_tests_relation_update(function_id: str, test_id: str):
	"""Load and display the tests function relation update page.

	Args:
	    function_id: Identifier of the function to load.
	    test_id: Identifier of the diagnostic test to load.
	"""
	TestsFunctionRelationUpdatePage(function_id, test_id).show()

@function_router.page('/cpt')
def function_cpt(function_id: str):
	"""Load and display the function cpt page.

	Args:
	    function_id: Identifier of the function to load.
	"""
	FunctionCPTPage(function_id).show()


hardware_router = APIRouter(prefix='/hardware/{hardware_id}')

@cluster_id_router.page('/hardware/new')
def hardware_create(cluster_id: str):
	"""Load and display the hardware create page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	HardwareCreatePage(cluster_id).show()

@hardware_router.page('/update')
def hardware_update(hardware_id: str):
	"""Load and display the hardware update page.

	Args:
	    hardware_id: Identifier of the hardware to load.
	"""
	HardwareUpdatePage(hardware_id).show()

@hardware_router.page('/')
def hardware_details(hardware_id: str):
	"""Load and display the hardware details page.

	Args:
	    hardware_id: Identifier of the hardware to load.
	"""
	HardwareDetailsPage(hardware_id).show()

@hardware_router.page('/realizes/new')
def realizes_relation_create(hardware_id: str):
	"""Load and display the realizes relation create page.

	Args:
	    hardware_id: Identifier of the hardware to load.
	"""
	RealizesRelationCreatePage(hardware_id).show()

@hardware_router.page('/realizes/{function_id}/update')
def realizes_relation_update(hardware_id: str, function_id: str):
	"""Load and display the realizes relation update page.

	Args:
	    hardware_id: Identifier of the hardware to load.
	    function_id: Identifier of the function to load.
	"""
	RealizesRelationUpdatePage(hardware_id, function_id).show()

@hardware_router.page('/affects/new')
def affects_relation_create(hardware_id: str):
	"""Load and display the affects relation create page.

	Args:
	    hardware_id: Identifier of the hardware to load.
	"""
	AffectsRelationCreatePage(hardware_id).show()

@hardware_router.page('/affects/{function_id}/update')
def affects_relation_update(hardware_id: str, function_id: str):
	"""Load and display the affects relation update page.

	Args:
	    hardware_id: Identifier of the hardware to load.
	    function_id: Identifier of the function to load.
	"""
	AffectsRelationUpdatePage(hardware_id, function_id).show()

@hardware_router.page('/observedby/new')
def hardware_observes_relation_create(hardware_id: str):
	"""Load and display the observes hardware relation create page.

	Args:
	    hardware_id: Identifier of the hardware to load.
	"""
	ObservesHardwareRelationCreatePage(hardware_id).show()

@hardware_router.page('/observedby/{observable_id}/update')
def hardware_observes_relation_update(hardware_id: str, observable_id: str):
	"""Load and display the observes hardware relation update page.

	Args:
	    hardware_id: Identifier of the hardware to load.
	    observable_id: Identifier of the observable to load.
	"""
	ObservesHardwareRelationUpdatePage(hardware_id, observable_id).show()

@hardware_router.page('/testedby/new')
def hardware_tests_relation_create(hardware_id: str):
	"""Load and display the tests hardware relation create page.

	Args:
	    hardware_id: Identifier of the hardware to load.
	"""
	TestsHardwareRelationCreatePage(hardware_id).show()

@hardware_router.page('/testedby/{test_id}/update')
def hardware_tests_relation_update(hardware_id: str, test_id: str):
	"""Load and display the tests hardware relation update page.

	Args:
	    hardware_id: Identifier of the hardware to load.
	    test_id: Identifier of the diagnostic test to load.
	"""
	TestsHardwareRelationUpdatePage(hardware_id, test_id).show()


observable_router = APIRouter(prefix='/observable/{observable_id}')

@cluster_id_router.page('/observable/new')
def observable_create(cluster_id: str):
	"""Load and display the observable create page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	ObservableCreatePage(cluster_id).show()

@observable_router.page('/update')
def observable_update(observable_id: str):
	"""Load and display the observable update page.

	Args:
	    observable_id: Identifier of the observable to load.
	"""
	ObservableUpdatePage(observable_id).show()

@observable_router.page('/')
def observable_details(observable_id: str):
	"""Load and display the observable details page.

	Args:
	    observable_id: Identifier of the observable to load.
	"""
	ObservableDetailsPage(observable_id).show()

@observable_router.page('/observes_fn/new')
def observes_fn_relation_create(observable_id: str):
	"""Load and display the observes function relation page.

	Args:
	    observable_id: Identifier of the observable to load.
	"""
	ObservesFunctionRelationPage(observable_id).show()

@observable_router.page('/observes_fn/{function_id}/update')
def observes_fn_relation_update(observable_id: str, function_id: str):
	"""Load and display the observes function relation page.

	Args:
	    observable_id: Identifier of the observable to load.
	    function_id: Identifier of the function to load.
	"""
	ObservesFunctionRelationPage(observable_id, function_id).show()

@observable_router.page('/observes_hw/new')
def observes_hw_relation_create(observable_id: str):
	"""Load and display the observes hardware relation page.

	Args:
	    observable_id: Identifier of the observable to load.
	"""
	ObservesHardwareRelationPage(observable_id).show()

@observable_router.page('/observes_hw/{hardware_id}/update')
def observes_hw_relation_update(observable_id: str, hardware_id: str):
	"""Load and display the observes hardware relation page.

	Args:
	    observable_id: Identifier of the observable to load.
	    hardware_id: Identifier of the hardware to load.
	"""
	ObservesHardwareRelationPage(observable_id, hardware_id).show()

@observable_router.page('/cpt')
def observable_cpt(observable_id: str):
	"""Load and display the observable cpt page.

	Args:
	    observable_id: Identifier of the observable to load.
	"""
	ObservableCPTPage(observable_id).show()


diagnostic_test_router = APIRouter(prefix='/test/{test_id}')

@cluster_id_router.page('/test/new')
def test_create(cluster_id: str):
	"""Load and display the test update page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	TestUpdatePage(cluster_id=cluster_id).show()

@diagnostic_test_router.page('/update')
def test_update(test_id: str):
	"""Load and display the test update page.

	Args:
	    test_id: Identifier of the diagnostic test to load.
	"""
	TestUpdatePage(test_id=test_id).show()

@diagnostic_test_router.page('/')
def test_details(test_id: str):
	"""Load and display the test details page.

	Args:
	    test_id: Identifier of the diagnostic test to load.
	"""
	TestDetailsPage(test_id=test_id).show()


diagnostic_test_result_router = APIRouter(prefix='/test_result/{result_id}')

@diagnostic_test_router.page('/results/new')
def test_result_create(test_id: str):
	"""Load and display the test result update page.

	Args:
	    test_id: Identifier of the diagnostic test to load.
	"""
	TestResultUpdatePage(test_id=test_id).show()

@diagnostic_test_result_router.page('/update')
def test_result_update(result_id: str):
	"""Load and display the test result update page.

	Args:
	    result_id: Identifier of the test result to load.
	"""
	TestResultUpdatePage(result_id=result_id).show()

@diagnostic_test_result_router.page('/tests')
def testresult_relation_table(result_id: str):
	"""Render the testresult relation table and its controls.

	Args:
	    result_id: Identifier of the test result to load.
	"""
	TestResultRelationPage(result_id).show()

@diagnostic_test_result_router.page('/cpt')
def test_cpt(result_id: str):
	"""Load and display the test result cpt page.

	Args:
	    result_id: Identifier of the test result to load.
	"""
	TestResultCPTPage(result_id).show()


operating_mode_router = APIRouter(prefix='/opm/{opm_id}')

@cluster_id_router.page('/opm/new')
def opm_create(cluster_id: str):
	"""Load and display the opm update page.

	Args:
	    cluster_id: Identifier of the cluster to load.
	"""
	OpmUpdatePage(cluster_id=cluster_id).show()

@operating_mode_router.page('/update')
def opm_update(opm_id: str):
	"""Load and display the opm update page.

	Args:
	    opm_id: Identifier of the operating mode to load.
	"""
	OpmUpdatePage(opm_id=opm_id).show()

@operating_mode_router.page('/')
def operating_mode_details(opm_id: str):
	"""Load and display the opm details page.

	Args:
	    opm_id: Identifier of the operating mode to load.
	"""
	OpmDetailsPage(opm_id=opm_id).show()



cluster_router.include_router(cluster_id_router)
