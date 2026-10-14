Modelling in Capella
====================

Usually you create an MBDlyb model by importing a
`Capella <https://mbse-capella.org/>`_ system model. MBDlyb converts the
components, functions and functional exchanges of the logical or physical
architecture into clusters, hardware, functions and *required for* relations.
Add diagnostic annotations to the Capella model as well. The more complete
the Capella model is, the less you have to change in the editor after the
import, and the easier it is to import the model again after it changes.

.. contents:: On this page
   :local:
   :depth: 2

Importing a Capella model
-------------------------

* To import a **new model**, open the landing page (http://localhost:8080/)
  and use the import button. This works in both Editor mode and Tree mode.
* To import into an **existing cluster**, use |icon-import-cluster| in the
  cluster toolbar (Editor mode only).

.. figure:: /images/screenshots/capella-import.png
   :class: screenshot
   :width: 90%
   :alt: The Capella import page.

   The Capella import page.

On the import page:

1. Upload **all files** that make up the Capella model, for example
   ``.aird``, ``.capella`` and ``.afm``.
2. Choose the **Capella architecture** to import: *logical* or *physical*.
3. Choose which tests to generate:

   * *Default tests on functions*: a test for every function;
   * *Default tests on high-level functions*: a test for every function with
     subfunctions;
   * *Default tests on hardware*: an inspection test for every hardware node;
   * *Default tests on low-level hardware*: an inspection test for hardware
     that realizes functions without subfunctions.

   You do not need these options for elements that are already annotated as
   tests or as inspectable in Capella (see below).
4. Choose whether to **import operating modes**.
5. Press **Save**. *Save* is only enabled after you upload files and choose
   an architecture.

If a name already exists in the target cluster, ``_1`` is added to the
imported name. After the import, :doc:`check the model <validation>` and
:ref:`import the CPTs <cpts:Exporting and importing CPTs>` if you have them.

The :ref:`example projects <example-projects>` contain annotated Capella
models (Capella 7.0) and CPTs that you can import.

.. note::

   Some modelling features are only available with a Capella import. The
   editor cannot create them. The main example is *error reporting chains*
   (observed errors). The editor focuses on refining models, and the project
   focuses on developing the methodology rather than the tool.

Diagnostic annotations
----------------------

Capella has no built-in diagnostic information. You add it as property values
with the Capella add-on
`PVMT <https://mbse-capella.org/addons.html>`_ (Property Values Management
Tools):

1. Install PVMT in Capella. The built-in help of Capella explains how to use
   it.
2. Import the MBDlyb property domain ``MBDlyb.vpd``. You find it in the folder
   ``capella-extension`` of the
   `MBDlyb repository <https://github.com/TNO/mbdlyb>`_.

The PVMT editor then shows the MBDlyb domain with its property groups and
default values:

.. figure:: /images/capella/pvmt-editor-loaded-with-mbdlyb-domain.png
   :alt: The PVMT editor with the MBDlyb domain.

   The PVMT editor with the MBDlyb property domain.

The table summarizes the annotations. The sections after it describe each one.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Annotation
     - Effect in MBDlyb
   * - **States** on a function
     - Custom states. A custom CPT is then required.
   * - **Inspectable** (and **Cost**) on a component
     - An inspection test with its result is created for the hardware.
   * - **Complete composite** on a component
     - No hardware node is created for the component. Its functions are kept.
   * - **Diagnostic test** (and **Cost**) on a function
     - The function becomes a diagnostic test.
   * - **Observable** on a function output port
     - A direct observable that observes the function.
   * - **Error code** on a function output port
     - An *observed error* that the function yields.
   * - **Reporting errors** on a function output port
     - The function reports errors to the user.
   * - **Required** = false on a functional exchange
     - The exchange is not imported. Use this to break cycles.
   * - **Fault rate** / **Fault rates** on a component
     - The prior of the ``Broken`` fault, or custom faults with their priors.

Custom states on a function
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes *Ok* and *NOk* are not enough to describe the behaviour of a
function. Enter the states as a comma-separated list in the **States**
property (group *MultiState*), for example ``Ok, Intermittent, NOk``.

.. figure:: /images/capella/custom-states-function.png
   :alt: Custom states on a Capella function.

   Custom states on a Capella function.

.. important::

   Custom states require a custom :doc:`CPT <cpts>`.

Inspectable hardware
~~~~~~~~~~~~~~~~~~~~

A service engineer can often inspect a component directly to see whether it
is broken. To model this, set **Inspectable** (group *Inspections*) to *true*
and enter the cost of the inspection in **Cost** (default 2.0).

.. figure:: /images/capella/hardware-element-labeled-as-inspectable.png
   :alt: A component labeled as inspectable.

   A component labeled as inspectable.

The import creates an inspection test (blue hexagon) with its result (green
box) for the component. It does this even when *Default tests on hardware* is
off.

.. figure:: /images/capella/hardware-element-with-inspection.png
   :alt: Imported hardware with its inspection test.

   The imported hardware with its inspection test.

Complete composites
~~~~~~~~~~~~~~~~~~~

Normally, every Capella component with allocated functions becomes a hardware
node, so that it can be diagnosed as healthy or broken. Sometimes you do not
want this. Suppose a component is responsible for a higher-level function, but
its subcomponents describe it completely. There is nothing in the component
that is not in a subcomponent, and the subcomponents perform all subfunctions
of the higher-level function. In that case, set **Complete composite** (group
*Composite*) to *true*.

.. figure:: /images/capella/component-labeled-as-complete-composite.png
   :alt: A component labeled as complete composite.

   A component labeled as complete composite.

The import does not create a hardware node for a complete composite, but it
keeps its functions:

.. figure:: /images/capella/complete-composite-in-mbdlyb.png
   :alt: A complete composite in MBDlyb.

   A complete composite in MBDlyb: the functions are kept, but there is no
   hardware node for the component.

Diagnostic tests
~~~~~~~~~~~~~~~~

You can define diagnostic tests in Capella:

1. Define a function in the logical or physical architecture that represents
   the test.
2. Set **Diagnostic test** (group *Diagnostic test*) to *true*, and enter the
   cost of the test in **Cost** (default 1.0).
3. Define subfunctions of the test and allocate them to the components that
   the test covers. If such a subfunction is basically the same as a regular
   function of the component, give it a similar name.

You can group several tests as subfunctions of a higher-level function. If
that higher-level function contains *only* tests, it is not imported.

.. figure:: /images/capella/function-labeled-as-test.png
   :alt: A function labeled as diagnostic test.

   A function labeled as diagnostic test.

You do not need the *Default tests on functions* option for these functions.
They are imported as tests:

.. figure:: /images/capella/diagnostic-test-imported-from-capella.png
   :alt: A diagnostic test imported from Capella.

   The diagnostic test after the import.

Direct observables
~~~~~~~~~~~~~~~~~~

Sometimes you can observe directly whether a function works, for example
because an error message appears or not. To model this:

1. Add an output port to the function and give it a meaningful name.
2. Set **Observable** (group *Direct observables*) of the port to *true*.

Only one observable output per function is useful, because it only shows
whether the function works.

.. figure:: /images/capella/function-output-labeled-as-observable.png
   :alt: A function output labeled as observable.

   A function output labeled as observable.

.. figure:: /images/capella/observable-function-imported-from-capella.png
   :alt: The imported observable.

   The observable after the import.

Observed errors
~~~~~~~~~~~~~~~

In complex systems, the component that *detects* an error is often not the
component that *reports* it to the user. MBDlyb models this with observed
errors.

**The function that detects (yields) the error:**

1. Add an output port to the function. Its name does not matter.
2. Set **Error code** (group *Error reporting*) to the name of the error, for
   example ``CD_ERROR``.
3. Leave **Reporting errors** on *false*. If the same function also shows the
   error to the user, model it as a direct observable instead. That is
   simpler.

.. figure:: /images/capella/function-output-labeled-yielding-error.png
   :alt: A function output that yields an error.

   A function output that yields an error.

The import shows the error as a yellow box:

.. figure:: /images/capella/function-yielding-error.png
   :alt: A function yielding an error in MBDlyb.

   The imported function that yields the error.

**The function that reports the error:**

1. Make sure that a path of functional exchanges leads from every function
   that yields the error to the reporting function. This path is the
   *error chain*.
2. Add an output port to the reporting function. You can give it a
   meaningful name.
3. Set **Reporting errors** (group *Error reporting*) to *true*.
4. Leave **Error code** empty to report all incoming errors here, or enter the
   error codes that this function reports.

.. figure:: /images/capella/function-output-labeled-reporting-errors.png
   :alt: A function output that reports errors.

   A function output that reports errors.

The import shows a *reports* arrow from the reporting function to the error:

.. figure:: /images/capella/function-reporting-error.png
   :alt: A function reporting an error in MBDlyb.

   The imported function that reports the error.

With a yielding function, a reporting function and an error chain between
them, the :doc:`diagnoser` handles the error correctly. If the error is
*Present*, the yielding function does not work, but the functions in the
chain *after* it do work, because they pass the error on.

.. note::

   You cannot create or edit observed errors in the web interface yet. You can
   only import them from Capella.

Functional exchanges that are not required
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Capella models can contain cycles of functional exchanges, for example in
control loops. The probabilistic reasoning model cannot contain cycles. A
cycle would also hide hardware failures. That is why MBDlyb cuts cycles
automatically when it builds the reasoning model.

You can also decide where to cut a cycle yourself. Set **Required** (group
*Required functional exchange*) of an exchange to *false*. The default is
*true*. A good place is often the incoming exchange of a function that
*measures* something. The measured value often depends on the function
before it, but if that function is broken, the measurement itself is usually
still correct, as long as the sensor hardware works.

.. figure:: /images/capella/functional-exchange-labeled-as-not-required.png
   :alt: A functional exchange labeled as not required.

   A functional exchange labeled as not required.

An exchange that is not required is not imported, so it cannot cause a cycle.
The :doc:`validator <validation>` reports any remaining cycles.

Fault rates
~~~~~~~~~~~

By default, MBDlyb gives every hardware node one fault ``Broken`` with a prior
probability of 0.01. The prior holds as long as there is no diagnostic
information. To use another value for a component, set **Fault rate** (group
*Hardware priors*):

.. figure:: /images/capella/hardware-element-with-explicit-fault-rate.png
   :alt: A component with an explicit fault rate.

   A component with an explicit fault rate.

The import assigns this fault rate to the ``Broken`` fault:

.. figure:: /images/capella/hardware-element-with-non-default-fault-rate.png
   :alt: Imported hardware with a non-default fault rate.

   The imported hardware with its fault rate.

Some components can fail in several ways or to several degrees. For these,
fill in **Fault rates** instead: a comma-separated list of faults, each with a
name and a prior separated by a colon. For example:
``Broken: 0.015, Dusty: 0.04``. If **Fault rates** is set, **Fault rate** is
ignored.

.. figure:: /images/capella/custom-fault-rates.png
   :alt: Custom fault rates in Capella.

   Custom fault rates for the ``Detector`` component.

.. figure:: /images/capella/custom-fault-rates-mbdlyb.png
   :alt: Custom faults in MBDlyb.

   The imported faults and priors.

.. note::

   With the default CPTs, every fault has the same effect as ``Broken`` on the
   functions that the hardware realizes. To give a fault a different effect,
   for example a dusty detector that makes detection intermittent, define a
   custom :doc:`CPT <cpts>` for those functions.
