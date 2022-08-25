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

- RawRecord.update improvements

  - allow mtime duplicates with different (domain, field_name) values.
  - requires iteration over multiple elements
  - duplicate mtime is only a problem if field tuple names are also the same
  - maybe do not rely of bisect's key= argument (new in python 3.10)

- Test merges
  
  - handle path collisions

- Hierarchy functionality
- CLI commands

  - ls
  - new
  - rename
  - del
  - set
  - unset


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
