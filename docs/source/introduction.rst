Introduction
============

Why model-based diagnostics?
----------------------------

When a complex system fails, a service engineer has to find out *which part* is
broken. Typically only a few symptoms are visible, for example an error
message or a function that does not work. Many parts could explain these
symptoms, and every test or inspection costs time and money.

MBDlyb approaches this with a *model* of the system. The model describes:

* the **functions** the system performs and how they depend on each other;
* the **hardware** that realizes these functions and how it can fail;
* what can be **observed** directly, and which **diagnostic tests** can be
  performed at which cost;
* the **operating modes** that change which dependencies are active.

From this model, MBDlyb automatically generates a probabilistic reasoning model
(by default a Bayesian network). The reasoning model computes the most likely
causes of the observed symptoms, and which test gives the most useful
information for its cost.

The methodology
---------------

`MBDlyb <https://github.com/TNO/mbdlyb>`_ is an open-source, proof-of-concept
Python library. It was developed in the SD2Act and Carefree research projects,
and it formalizes and consolidates the research done in these projects. With
it you can specify large diagnostic networks easily and experiment at scale.
MBDlyb-UI makes the library available through a web interface.

The figure shows the workflow of the methodology. **Orange** arrows need
people. **Green** arrows are fully automated transformations or
computations.

.. figure:: /images/methodology/mbdlyb-overview.png
   :width: 80%
   :alt: Overview of the MBDlyb methodology.

   High-level overview of the workflow of the methodology.

1. **Model the system.** Engineers turn system descriptions into system
   dependencies. They model the system in `Capella <https://mbse-capella.org/>`_
   with diagnostic annotations and import it (see :doc:`capella`), or build
   and edit the model in the :doc:`model editor <modelling>`.
2. **Refine the model.** Add custom states and conditional probability tables
   (:doc:`cpts`), tests, and observables. Then check the model with the
   :doc:`validator <validation>`. The result is the *diagnostic network*.
3. **Generate the reasoning model.** MBDlyb translates the diagnostic network
   into a probabilistic reasoning model automatically.
4. **Use the model.**

   * At service time, the **diagnoser** combines operational data and the
     observations of the service engineer. It proposes diagnostic steps
     (see :doc:`diagnoser`).
   * At design time, the **analyser** gives diagnostic insights, such as the
     diagnosability of the design and diagnostic procedures. Designers use
     these insights to improve the system descriptions
     (see :doc:`design-for-diagnostics`).

Everything is stored in a `Neo4j <https://neo4j.com/>`_ graph database. You can
open the same model in the web interface, in scripts that use the MBDlyb Python
library, and in Neo4j's own tools.

.. _example-projects:

Example projects
----------------

Two company-agnostic example projects were developed during the projects with
industry partners. Each comes as a Capella (7.0) model that follows the
modelling guidelines of the methodology, and as a ready-to-use Neo4j database
dump. The Capella models contain diagnostic annotations, so you can
:ref:`import them <capella:Importing a Capella model>` directly. The Capella
archive also contains some CPTs, to
:ref:`complete the model <cpts:Exporting and importing CPTs>` after the import.

CDRadioPlayer
   A typical device from the '90s that plays CDs and radio. It is simple to
   understand and shows the methodology. All screenshots in this guide use this
   model.
   Downloads:
   `Capella <https://mbdlyb.esi.nl/projects/cdradioplayer-v2/Capella_CDRadioPlayer-v2.zip>`__ |
   `Database <https://mbdlyb.esi.nl/projects/cdradioplayer-v2/neo4j_cdradioplayer-v2.dump>`__

Car
   Part of a car, with some parts modelled in more detail.
   Downloads:
   `Capella <https://mbdlyb.esi.nl/projects/car/Capella_Car.zip>`__ |
   `Database <https://mbdlyb.esi.nl/projects/car/neo4j_car.dump>`__

To load a database dump into Neo4j, see :ref:`installation:Importing and exporting databases`.

Contact
-------

MBDlyb is developed by the
`TNO-ESI diagnostics team <https://esi.tno.nl/research/expertise/diagnostics/>`_.
For questions about the library, the interface or the methodology, contact
`Thomas Nägele <mailto:thomas.nagele@tno.nl>`_.
