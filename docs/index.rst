.. Passmate documentation master file, created by
   sphinx-quickstart on Sat Jan  1 13:26:04 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Passmate
========

Passmate is a simple password manager that stores your secret data (login credentials, keys etc.) securely encrypted and offers a mechanism to synchronize the data between multiple machines.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   getting_started
   config
   database
   sync
   security


Todo
----

- Test shell
- Test syncing
- Test new reporting of SyncSummary
- Check CmdRename error handling
- Built-in help
- Improve docs
- Mask passwords after showing them
- CmdGen: Allow customization of template_preset using config file
- Revise session setup and sync at startup in cli / shell


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
