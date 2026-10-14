Tutorial: exploring the CD radio player
=======================================

This tutorial takes you through the CDRadioPlayer example model. It shows how
a real system becomes an MBDlyb model, and how to use that model. It takes
about 20 minutes.

.. contents:: Steps
   :local:

1. Load the example
-------------------

1. Download the
   `CDRadioPlayer database dump <https://mbdlyb.esi.nl/projects/cdradioplayer-v2/neo4j_cdradioplayer-v2.dump>`_
   and import it into Neo4j, for example as database ``cdradioplayer``
   (see :ref:`installation:Importing and exporting databases`).
2. Start the interface: ``mbdlyb-ui --database cdradioplayer``.
3. Open http://localhost:8080/ and select *Editor* in the header.
4. Click **CDRadioPlayer**.

You can also import the
`Capella model <https://mbdlyb.esi.nl/projects/cdradioplayer-v2/Capella_CDRadioPlayer-v2.zip>`_
yourself (see :ref:`capella:Importing a Capella model`) and then import
its CPTs.

2. The system and its structure
-------------------------------

The CD radio player has five subsystems. Each is a cluster:

.. figure:: /images/screenshots/cluster-diagram.png
   :class: screenshot
   :width: 90%
   :alt: Diagram of the root cluster.

   The root cluster ``CDRadioPlayer``. It shows the subsystems and the
   top-level function ``PlayCDOrRadio`` with its system tests.

``PowerSystem``
   Supplies power from the battery or from the wall: ``ACPowerSystem``
   (with ``Converter`` and ``PowerCable``), ``Battery``, ``LED`` and
   ``PowerBoard``.
``CDReader``
   Reads the CD: ``Board``, ``Detector``, ``Laser``, ``Motor`` and
   ``Transducer``.
``RadioReceiver``
   Receives radio: ``Antenna`` and ``Board``.
``AudioSystem``
   Turns the signal into sound: ``Amplifier``, ``DAC`` and ``Speaker``.
``HMI``
   The user interface: ``Board``, ``Display`` and ``SourceSwitch``.

Use the navigation drawer to open the clusters. Most of the lowest-level
clusters contain one hardware node with the same name, and the functions that
it realizes. For example, ``CDReader.Laser`` contains the hardware ``Laser``,
which realizes ``IlluminateCD``.

3. Functions and their dependencies
-----------------------------------

Open ``CDReader``. The diagram shows how the parts work together to *read a
CD*. The ``Motor`` spins the CD, the ``Laser`` illuminates it, the
``Detector`` detects the reflected light, and so on. Every arrow is a
dependency. If ``SpinCD`` fails, ``DetectReflectedLaser`` cannot work either.

.. figure:: /images/screenshots/cluster-diagram-cdreader.png
   :class: screenshot
   :width: 90%
   :alt: Diagram of the CDReader cluster.

   The ``CDReader`` cluster.

Click |icon-view-table| on ``PowerSystem`` to see the *required for* relations
of the power system as a matrix
(see :ref:`modelling:The required-for matrix`).

4. Operating modes
------------------

Open ``PowerSystem.PowerBoard``. Its operating mode selector
``Select_BatteryPower_WallPower`` has the modes ``BatteryPower`` and
``WallPower``. ``SupplyPowerFromBattery`` is only required for
``DistributePower`` in the ``BatteryPower`` mode. So when the player runs on
wall power, a broken battery does not explain a power problem.

The second selector, ``AudioSystem.DAC.Select_PlayCD_PlayRadio``, chooses
between the CD and the radio as audio source.

5. Faults and custom states
---------------------------

Open ``CDReader.Detector``. The hardware ``Detector`` has two faults:
``Broken`` (prior 0.015) and ``Dusty`` (prior 0.04). Its function
``DetectReflectedLaser`` has three states: ``Ok``, ``Intermittent`` and
``NOk``. Click |icon-row-cpt| to see its CPT. A dusty detector mostly causes
intermittent detection, but a broken one makes detection fail.
See :doc:`cpts`.

6. Observations and tests
-------------------------

* The display (``HMI.Display``) reports the observed errors ``CD_ERROR`` and
  ``RADIO_ERROR``. These come from the Capella model.
* The root cluster contains cheap system tests: ``Test_PlayCD`` and
  ``Test_PlayRadio``.
* Most hardware has an *inspection* test, for example
  ``CDReader.Laser.Inspect_Laser``.

7. Check the model
------------------

Click |icon-check-model| on the root cluster. The validator reports
*No issues were found*. See :doc:`validation`.

8. Diagnose a failure
---------------------

Click |icon-diagnoser|. Follow the
:ref:`walkthrough in the diagnoser chapter <diagnoser:Walkthrough: the CD player does not play>`:
the player runs on batteries and shows ``CD_ERROR``. After one cheap test,
the ``Detector`` is the main suspect.

9. Analyse the design
---------------------

Close the diagnoser and click |icon-design-for-diagnostics|. Select
``WallPower`` and compute. The result has four diagnostic procedures.
``DP_2``, for faults that cause ``CD_ERROR``, cannot tell a broken
``Transducer`` from a broken ``Detector``. A designer could add a test or an
error code for this. See :doc:`design-for-diagnostics`.

Next steps
----------

* Read :doc:`concepts` for the meaning of every element and relation.
* Build your own model: import it from Capella, refine it in the
  :doc:`editor <modelling>`, add :doc:`CPTs <cpts>` where needed, and
  :doc:`check it <validation>`.
