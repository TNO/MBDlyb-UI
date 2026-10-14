Importing and exporting
=======================

.. contents:: On this page
   :local:
   :depth: 2

Importing a Capella model
-------------------------

Use the import button on the landing page to import a Capella model as a new
model, or |icon-import-cluster| to import it into an existing cluster. See
:doc:`capella` for the import options and the diagnostic annotations you can
add in Capella.

Downloading the graph and Bayesian network
------------------------------------------

|icon-download-graph| **Download graph**
   Downloads the cluster and everything in it as a yEd ``.graphml`` file, with
   the colours of :doc:`concepts`. Use it to inspect large models. In
   `yEd <https://www.yworks.com/products/yed>`_, all nodes are initially on top
   of each other. Choose *Tools → Fit Node to Label* and then
   *Layout → Hierarchical* (default options) to get a readable diagram.

|icon-download-bayesnet| **Download Bayesian network**
   Downloads the reasoning model that MBDlyb generates from the cluster. Use it
   to analyse the generated network with external tools.

CPTs
----

See :ref:`cpts:Exporting and importing CPTs`.

Diagnosis results
-----------------

The diagnoser can download the evidence, the diagnosis and the test
suggestions as an Excel file (see :ref:`diagnoser:Evidence`). Design for
diagnostics can export its results to Excel, and its decision trees as SVG
images (see :doc:`design-for-diagnostics`).
