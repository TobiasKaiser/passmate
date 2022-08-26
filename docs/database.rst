.. _Database Format:

Database Format
===============

Passmate organizes the password database as JSON object. The JSON object is stored on disk using `scrypt`_'s `container format`_. The password database is protected by a user-defined master passphrase. The scrypt key derivation function is used to provide comparatively strong protection against brute-force guessing of the master passphrase when an attacker gains access to your encrypted password storage file, as explained in `this paper`_. The container format uses symmetric AES256-CTR encryption and HMAC-SHA256 to ensure file integrity. If you want to access the raw JSON object without using Passmate, you can for example use the encryption utility program that comes with `scrypt`_.

.. _scrypt: https://www.tarsnap.com/scrypt.html
.. _container format: https://github.com/Tarsnap/scrypt/blob/master/FORMAT
.. _this paper: https://www.tarsnap.com/scrypt/scrypt.pdf

Data Model
----------

A password database can contain an arbitrary number of password records. Each password record can contain metadata and user data fields. Each field has a name (string) and a value (string).

Currently, the only vald metadata field is "path". The path of a record is stored in this field. The path is the primary identifier through which the user can access password records. 

User data fields can have arbitrary field names. Example field names are "password", "username" and "email".

JSON Object
-----------

Here a short example password database JSON object obj::

    {
        "version": 2,
        "purpose": "primary",
        "records": {
            "MyRecordId": [
                ["meta", "path", "record_path", 12345],
                ["user", "password", "thisismypassword", 67890]
            ]
        }
    }

obj.version must be 2.

obj.purpose must be either "primary" or "sync_copy". A primary database file is marked with the purpose "primary" and can be opened directly through Passmate. Records can be read, added and modified in this file. After a primary database file has been modified, the updated database file will be written and replace the prevous primary database. Synchronization copies marked by the purpose "sync_copy" are written by one peer of a synchronization network and read by all other peers. The mechanism for synchronization is described further in the section on :ref:`Synchronization`.

obj.records is a dictionary containing all records. Keys of the records dictionary (record identifiers) are random strings (in this example "MyRecordId") that uniquely identify records and are not exposed to the user. Values of the records dictionary are arrays of field tuples. Record identifiers areis immutable. When new record identifiers are generated, enough randomness should be used in order to rule out collisions with other copies of the password database, which cannot be detected by inspecting the local copy of the password database.

A field tuple describes the modification of a field at a particular point in time. As a JSON array, it consists of the following four elements:

1. domain identifier, either "meta" for metadata or "user" for user data,
2. field name,
3. field value, either a string or null,
4. time of modification as UNIX time integer.

Field values of null can be used to remove fields from the record. Records can be deleted by removing the path meta field.

The order in which the field tuples are stored in the field tuple array does not matter (with the small and unlikely exception of when two modifications to the same field have been performed at the same UNIX time).

The JSON object keeps track of all modifications that have ever been saved to the database. Records or fields are never removed from the database. When the database is opened, Passmate constructs a representation with only the most recent field values.

TODO: JSON schema

.. _Merging:

Merging
-------

This format allows easy merging of databases that have been modified separately (practically, on different computers). Two field tuple arrays A and B are merged by appending all field tuples from B to A that are not already present in A (set union operation).

When records are added and fields are modified in separate copies, generally no manual intervention is required when merging the copies. The most recent modifications are used to determine what data is displayed to the user.

The only problem arises when path meta fields of different records in different copies are set to the same value and those copies are then merged, since paths should be unique within a database.

TODO: How do we resolve this? Renaming the path of one of the two records to a new unique path, seems best.

File locking
------------

Primary database files should not be opened by more than one process at a time. File locking prevents this. A separate lock file is created and fcntl.lockf is used to aquire an exclusive lock on the lock file. The lock is removed when Passmate is closed.

Future version
--------------

The fact that records are represented using a JSON hierarchy layer, but fields are modelling using a flat array, can be seen as a logical weakness of the current database. It does not affect security, but could be improved upon. A future version of the JSON database could be either entirely flat or use hierarchy (JSON objects) for records and fields.

Proposed JSON format (entirely flat)::

    {
        "version": 3,
        "purpose": "primary",
        "records": [
            ["MyRecordId", "meta", "path", "record_path", 12345],
            ["MyRecordId", user", "password", "thisismypassword", 67890]
        ]
    }

Proposed JSON format (hierarchical records and fields)::

    {
        "version": 3,
        "purpose": "primary",
        "records": {
            "MyRecordId": {
                "meta":{
                    "path":[
                        ["record_path", 12345]
                    ]
                },
                "user":{
                    "password":[
                        ["thisismypassword", 67890]
                    ]
                }
            }
        }
    }