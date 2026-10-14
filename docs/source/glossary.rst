Glossary
========

.. glossary::
   :sorted:

   Cluster
      A container that structures the model hierarchically, for example a
      subsystem. See :ref:`concepts:Clusters and names`.

   Root cluster
      A cluster without a parent. It represents a complete model.

   Fully qualified name
   FQN
      The unique name of an element: the cluster path followed by its name,
      for example ``CDRadioPlayer.CDReader.Laser.IlluminateCD``.

   Function
      Something the system does. It works (``Ok``) or not (``NOk``), or has
      custom states.

   Leaf function
      A function without subfunctions. *Required for* relations must connect
      leaf functions.

   Composite function
      A function with subfunctions.

   Hardware
      A physical part that can fail. It has the state ``Healthy`` and one or
      more fault states.

   Fault
   Failure mode
      A state of hardware other than ``Healthy``, for example ``Broken``. In
      design for diagnostics, a failure mode is a hardware/fault combination.

   Prior
      The probability of a fault before there is any evidence. This is a
      fault rate.

   Operating mode
      A situation of the system, for example ``BatteryPower``, that
      determines which *required for* relations are active.

   Operating mode selector
      A model element whose states are the operating modes.

   Direct observable
      Information that is available without doing a test, for example a
      status LED.

   Observed error
      An error code that one function generates and another function reports
      to the user.

   Diagnostic test
      An action with a cost that gives one or more test results.

   Test result
      The outcome (``Ok``/``NOk``) of a test. It indicates a set of functions
      and hardware.

   Weight
      A number between 0 and 1 for how strongly a failure propagates along a
      relation. See :ref:`concepts:Relation weights`.

   FPR
   False positive rate
      An observable or test result parameter for the chance that a failure is
      reported while everything works.

   FNR
   False negative rate
      An observable or test result parameter for the chance that an actual
      failure is missed.

   CPT
   Conditional probability table
      The table that gives the probability of each state of a node for every
      combination of parent states. See :doc:`cpts`.

   Evidence
      Information entered in the diagnoser: operating modes, observations and
      test results.

   Soft evidence
      Uncertain evidence, entered as probabilities instead of one state.

   Information gain
      The expected reduction of uncertainty (entropy) about the diagnosis when
      you perform a test.

   Balance
      The diagnoser setting that trades test cost against information gain.

   Signature
      The pattern of observable values that a failure mode causes.

   Diagnostic procedure
   DP
      A decision tree of tests that diagnoses the failure modes with one
      signature.

   Ambiguity group
      Failure modes that the available tests cannot tell apart.

   Capella
      A model-based systems engineering tool. MBDlyb can import its models.

   PVMT
      The Capella *Property Values Management Tools* add-on, used to annotate
      Capella models with diagnostic information.

   Neo4j
      The graph database that stores MBDlyb models.
