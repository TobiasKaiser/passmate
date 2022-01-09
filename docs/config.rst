.. _Configuration:

Configuration
=============

Passmate is configured through a TOML config file.

.. code-block:: toml

   primary_db = "~/.local/share/passmate/local.pmdb"
   shared_folder = "~/.local/share/passmate/sync/"
   host_id = "MyHostname"


Default paths
-------------

The default paths used by passmate under Linux are:

+-------------------------------------+------------------------+--------------------------------+
| Path                                | Purpose                | How to change path             |
+=====================================+========================+================================+
| ~/.local/share/passmate/config.toml | Config file            | passmate command line argument |
+-------------------------------------+------------------------+--------------------------------+
| ~/.local/share/passmate/local.pmdb  | Primary database       | change in config file          |
+-------------------------------------+------------------------+--------------------------------+
| ~/.local/share/passmate/sync/       | shared folder for sync | change in config file          |
+-------------------------------------+------------------------+--------------------------------+
