Tutorial: building a model from scratch
=======================================

This tutorial shows how to build a simple model of a CD radio player in the
:doc:`model editor <modelling>`. It is a simplified version of the
:ref:`CDRadioPlayer example project <example-projects>` that you explore in
:doc:`tutorial`. If you have not read :doc:`concepts` yet, read it first.

.. figure:: /images/build-tutorial/cdradioplayer-photo.jpg
   :width: 50%
   :alt: A portable CD radio player.

   A CD radio player.
   Source: `Wikimedia Commons <https://commons.wikimedia.org/wiki/File:Akai_APRC-90_portable_radio_cassette_CD_player_with_Bluetooth_%28edited,_white_background%29.jpg>`__.

.. contents:: On this page
   :local:

.. note::

   The cluster diagrams in this tutorial come from an earlier version of this
   guide. Their colours differ slightly from the
   :ref:`colours in the interface <concepts:Model elements>`. For example,
   test results are light green there. The model also differs from the
   example project: it is simpler and uses other names. To compare your
   model with the diagrams, enable the diagram on the cluster pages (see
   :ref:`interface:Settings`).

All steps are done in **Editor mode**. Remember that nothing is stored until
you press *Save* in a form.

1. Create the model
-------------------

1. Start the interface with an empty database (see
   :ref:`installation:Starting the interface`).
2. On the landing page, click |icon-add| and create the root cluster
   ``CDRadioPlayer``.
3. On the cluster page of ``CDRadioPlayer``, add two functions with
   |icon-add| in the *Functions* table: ``PlayCD`` and ``PlayRadio``. These are
   the main functions of the device.

A root cluster cannot contain hardware. The hardware goes into the
subclusters that you create next.

2. CD reader and radio receiver
-------------------------------

Each component of the device gets its own cluster with a function, the
hardware that realizes it, and a test.

1. In the *Clusters* table of ``CDRadioPlayer``, click |icon-add| and create
   the cluster ``CDReader``. Select both *Add default hardware?* and
   *Add default function?*, and name the function ``ReadCD``. The interface
   creates the hardware ``CDReader``, which *realizes* ``ReadCD``.
2. Make ``ReadCD`` a subfunction of ``PlayCD``. Open the page of ``PlayCD``,
   click |icon-add| in the *Subfunctions* table and select
   ``CDReader.ReadCD``. Reading the CD is part of playing a CD.
3. In the *Diagnostic tests* table of ``CDReader``, create the test
   ``Test_ReadCD``. Select *Add default test result?* to create
   ``Test_ReadCD_Result``, and enter a cost.
4. On the page of ``Test_ReadCD``, open the *tested items* of
   ``Test_ReadCD_Result`` and select the function ``ReadCD``. The result now
   *indicates* whether the CD can be read.

.. figure:: /images/build-tutorial/cdreader.png
   :width: 45%
   :alt: The CDReader cluster.

   The ``CDReader`` cluster.

Create the cluster ``RadioReceiver`` in the same way, with the function
``ReceiveRadio`` (a subfunction of ``PlayRadio``) and the test
``Test_ReceiveRadio``.

.. figure:: /images/build-tutorial/radioreceiver.png
   :width: 50%
   :alt: The RadioReceiver cluster.

   The ``RadioReceiver`` cluster.

3. Audio system
---------------

Both playing a CD and playing the radio need the audio system. Create the
cluster ``AudioSystem`` like the previous clusters, with the function
``GenerateAudio`` and the test ``Test_AudioSystem``. Make ``GenerateAudio`` a
subfunction of **both** ``PlayCD`` and ``PlayRadio``.

.. figure:: /images/build-tutorial/audiosystem.png
   :width: 50%
   :alt: The AudioSystem cluster.

   The ``AudioSystem`` cluster.

4. Power system
---------------

The power system provides power to all parts of the device. The power comes
from a battery or from the wall socket. A power board selects one of these
sources and distributes the power.

1. Create the cluster ``PowerSystem`` in ``CDRadioPlayer``, with the hardware
   ``PowerSystem`` and the function ``ProvidePower``.
2. In the *Observables* table of ``PowerSystem``, create the direct
   observable ``PowerLED``. The LED shows whether there is power.
3. On the page of ``ProvidePower``, click |icon-add| in the *Observed by*
   table and select ``PowerLED``.

Power board
~~~~~~~~~~~

1. In ``PowerSystem``, create the cluster ``PowerBoard`` with default
   hardware and the function ``DistributePower``. Add the test
   ``Test_DistributePower``, whose result indicates ``DistributePower``.
2. Make ``DistributePower`` a subfunction of ``ProvidePower``.
3. The CD reader, the radio receiver and the audio system need power. On the
   page of ``DistributePower``, click |icon-add| in the *Required for* table.
   Add ``ReadCD``, ``ReceiveRadio`` and ``GenerateAudio`` one by one, without
   operating modes.

.. figure:: /images/build-tutorial/powerboard.png
   :width: 55%
   :alt: The PowerBoard cluster.

   The ``PowerBoard`` cluster. The diagram does not show the *required for*
   relations to ``ReadCD``, ``ReceiveRadio`` and ``GenerateAudio``.

Operating mode: battery or wall power
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The device runs on battery power or on wall power. Model this with an
operating mode selector:

* In the *Operating mode selectors* table of ``PowerSystem``, create the
  selector ``Select_Power`` with the operating modes ``BatteryPower`` and
  ``WallPower``.

The selector is placed in ``PowerSystem``. Then its modes are available for
*required for* relations between the functions in all clusters inside
``PowerSystem`` (see :ref:`modelling:Required for`).

Battery, AC-DC converter and power cable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The battery supplies the power board in the mode ``BatteryPower``. In the mode
``WallPower``, the power cable supplies the AC-DC converter, and the converter
supplies the power board.

1. In ``PowerSystem``, create three clusters with default hardware and a
   default function:

   * ``Battery`` with the function ``SupplyBatteryPower``;
   * ``ACDCConverter`` with the function ``ConvertACtoDC``;
   * ``PowerCable`` with the function ``SupplyWallPower``.

2. Make the three functions subfunctions of ``ProvidePower``.
3. Add the *required for* relations, with the operating modes:

   .. list-table::
      :header-rows: 1
      :widths: 30 30 20

      * - Function
        - Required for
        - Operating mode
      * - ``SupplyBatteryPower``
        - ``DistributePower``
        - ``BatteryPower``
      * - ``ConvertACtoDC``
        - ``DistributePower``
        - ``WallPower``
      * - ``SupplyWallPower``
        - ``ConvertACtoDC``
        - (none)

4. Add a test with a default result to each cluster: ``Test_Battery``,
   ``Test_ACDCConverter`` and ``Test_PowerCable``. These tests check the
   **hardware**, not the function. So in the *tested items*, select the
   hardware node of the cluster (for example ``Battery``) instead of its
   function.

.. figure:: /images/build-tutorial/battery.png
   :width: 60%
   :alt: The Battery cluster.

   The ``Battery`` cluster. The test result indicates the hardware.

.. figure:: /images/build-tutorial/acdcconverter.png
   :width: 60%
   :alt: The ACDCConverter cluster.

   The ``ACDCConverter`` cluster.

.. figure:: /images/build-tutorial/powercable.png
   :width: 60%
   :alt: The PowerCable cluster.

   The ``PowerCable`` cluster.

The complete power system looks like this:

.. figure:: /images/build-tutorial/powersystem.png
   :width: 100%
   :alt: Overview of the PowerSystem cluster.

   Overview of the ``PowerSystem`` cluster. The operating mode selector, the
   *required for* relations and the contents of the subclusters other than
   their main functions are not shown.

5. Check the model
------------------

* Check the dependencies on the
  :ref:`required-for matrix <modelling:The required-for matrix>` of
  ``CDRadioPlayer``. The overview diagram does not show them.
* Run the :doc:`validator <validation>` and solve the reported problems.
* To inspect the complete model, download it as a yEd graph with
  |icon-download-graph| (see
  :ref:`import-export:Downloading the graph and Bayesian network`).

6. Diagnose a failure
---------------------

Open the :doc:`diagnoser` from the ``CDRadioPlayer`` cluster and try this
scenario:

1. The device runs on batteries. Set the operating mode of ``Select_Power`` to
   ``BatteryPower``.
2. The power LED does not light up. Set ``PowerLED`` to ``NOk``.
3. Click *Compute*. The diagnoser shows the most likely broken hardware and
   suggests tests.
4. Perform the suggested tests and enter their results. For example,
   ``Test_DistributePower`` gives ``NOk`` and ``Test_Battery`` gives ``Ok``.
   Then the power board is the most likely cause.

The exact ranking of the tests depends on their costs, the fault rates and
the :ref:`balance setting <diagnoser:How tests are ranked>`. Your model may
therefore suggest the tests in another order.

Next steps
----------

* Add custom faults and states, and their :doc:`CPTs <cpts>`.
* Analyse the diagnosability of the design in
  :doc:`design-for-diagnostics`.
* For larger models, model the system in Capella and import it
  (see :doc:`capella`).
