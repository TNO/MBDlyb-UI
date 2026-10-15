MBDlyb user guide
====================

`MBDlyb-UI <https://github.com/TNO/mbdlyb-ui>`_ is the web interface of `MBDlyb <https://github.com/TNO/mbdlyb>`_, a
prototype Python library for *design-driven, model-based diagnostics* developed
by `TNO-ESI <https://esi.tno.nl/research/expertise/diagnostics/>`_. With the
interface you build a functional model of a system, enrich it with diagnostic
information, check it, and use it to:

* **diagnose** a malfunctioning system by entering observations and test
  results, and get suggestions for the next most informative test
  (the :doc:`diagnoser`);
* **analyse the diagnosability** of a design and derive diagnostic procedures
  before the system is built (:doc:`design-for-diagnostics`).

.. figure:: /images/screenshots/cluster-editor-root.png
   :class: screenshot
   :width: 90%
   :alt: The model editor showing the CDRadioPlayer example model.

   The model editor showing the root cluster of the *CDRadioPlayer* example
   model.

This guide focuses on using the front-end and on understanding *what* is being
modelled. All screenshots show the CDRadioPlayer example model, which you can
download and load yourself (see :doc:`introduction`).

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   introduction
   installation
   tutorial
   tutorial-build
.. toctree::
   :maxdepth: 2
   :caption: Understanding the model

   concepts

.. toctree::
   :maxdepth: 2
   :caption: Using the interface

   interface
   modelling
   cpts
   capella
   import-export
   validation
   diagnoser
   design-for-diagnostics

.. toctree::
   :maxdepth: 1
   :caption: Reference

   glossary
   maintaining-docs

.. toctree::
   :maxdepth: 2
   :caption: Developer reference
   :glob:

   api/*/index
