===========
HR Hospital
===========

.. |badge1| image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
   :alt: License: LGPL-3

.. |badge2| image:: https://img.shields.io/badge/Odoo-19.0-blueviolet.svg
   :alt: Odoo 19.0

|badge1| |badge2|

A comprehensive hospital management module for Odoo 19 that streamlines the
complete healthcare workflow — from patient registration and doctor assignment
to visit scheduling, medical diagnosis, and reporting.

**Table of contents**

.. contents::
   :local:
   :depth: 2

Features
========

Patient Management
------------------

* Full patient profiles with personal data, contact information,
  blood group, allergies, and insurance
* Contact person assignment for minors or incapacitated patients
* Doctor assignment with full change history tracking
* Patient card export in JSON or CSV format

Doctor Management
-----------------

* Doctor profiles with specialities and license tracking
* Automatic experience years calculation from license date
* Intern/mentor relationship with nested mentor validation
* Doctor archiving protection (blocked when active visits exist)

Visit Scheduling
----------------

* Calendar, list, and pivot views for visits
* Smart conflict detection (no duplicate visits per day per doctor)
* Weekend and doctor availability blocking
* Visit rescheduling via wizard
* Status workflow: Planned → Done / Cancelled / No Show

Medical Diagnosis
-----------------

* Diagnosis tracking linked to visits
* Approval workflow (intern diagnoses must be approved by mentor)
* Disease classification with ICD-10 codes and danger levels
* Disease report wizard with date/doctor/disease filters

Schedule Management
-------------------

* Doctor work schedules with time slots
* Vacation, sick, and conference blocking
* Bulk schedule generation wizard (weekly, even/odd week modes)
* Time normalization to minute precision

Security
--------

Five security groups with hierarchical inheritance:

1. **Patient** — Read own visits only
2. **Intern** — Read/write own visits
3. **Doctor** — Read/write own + intern visits
4. **Manager** — Read all visits
5. **Administrator** — Full access including delete

Localization
============

* Full Ukrainian translation (``uk_UA``) included
* Ukrainian translation for the disease classifier
* Translatable fields: disease names, descriptions, symptoms, specialities

Configuration
=============

1. Install the module from the Apps menu.
2. Go to **Settings → Users & Companies → Users**.
3. Assign the appropriate Hospital group to each user:
   Patient, Intern, Doctor, Manager, or Administrator.

Usage
=====

1. Create doctor specialities and doctors.
2. Register patients with personal doctors.
3. Schedule visits and track diagnoses.
4. Use wizards for mass operations (reassignment, rescheduling, reporting).

Known Issues / Roadmap
======================

* Integration with external medical systems (HL7/FHIR) is planned.
* SMS/email notifications for upcoming visits.
* Patient portal for self-service visit booking.

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
