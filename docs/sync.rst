.. _Synchronization:

Synchronization
===============

To synchronize your Passmate database across multiple systems, synchronize the shared folder (see :ref:`Getting Started`) using a file / folder synchronization tool or remote filesystem of your choice.

Example synchronization tools:

- `Syncthing <https://syncthing.net/>`_
- `Unison <https://www.cis.upenn.edu/~bcpierce/unison/>`_
- NFS
- SMB
- `sshfs <https://github.com/libfuse/sshfs>`_
- A cloud service of your choice such as `NextCloud <https://nextcloud.com/>`_ / WebDAV

If different passphrases are used for containers on different hosts, you will be prompted for the remote host passphrase during synchronization. If the same passphrase is chosen on all hosts, the passphrase does not need to be re-entered during synchronization. If you want to change your passphrase, you need to repeat this process on each host.

Under the hood
--------------

Every participating host creates and writes an own *synchronization copy database file* in the shared folder. Those synchronization copies contain the same password data as the host's local primary databases. For the synchronization copies, the same encrypted :ref:`Database Format` as for the primary database is used.

Through the shared folder, all hosts now have access to the databases of all other hosts, presupposing that the user has entered the correct passphrase or passphrases for all hosts.

Synchronization is now achieved by merging all remote copies with the local primary database as described in the section :ref:`Merging`.