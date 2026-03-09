=====================
Unique Partner Email
=====================

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
   :alt: License: LGPL-3

.. |badge2| image:: https://img.shields.io/badge/Odoo-19.0-blueviolet.svg
   :alt: Odoo 19.0

|badge1| |badge2|

This module prevents having multiple partners (``res.partner``) with the
same email address in the system. It adds a validation constraint that
ensures email uniqueness across all partner records.

**Table of contents**

.. contents::
   :local:
   :depth: 2

Features
========

* Unique email enforcement across all partners
* Case-insensitive email comparison
* Clear error messages showing which partner already uses the email
* Empty emails are allowed (multiple partners without email)
* Full Ukrainian translation

Configuration
=============

No configuration required. Install the module and the constraint is active
immediately.

Usage
=====

Simply install the module. From that point, any attempt to create or update
a partner with an email that is already used by another partner will be
blocked with a clear error message.

Known Issues / Roadmap
======================

* Existing duplicate emails must be resolved manually.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/H0RR0N/h0rr0n/issues>`_.

Credits
=======

Authors
-------

* H0RR0N

Maintainers
-----------

* H0RR0N

This module is maintained by H0RR0N.
