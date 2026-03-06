Vesna Macarons Courier
======================

This module provides a production-ready foundation for courier operations in Odoo:

- Courier zones based on GeoJSON polygons.
- Route planning with stops tied to stock deliveries.
- GPX tracks stored in the module and parsed into map-ready geometry.
- Dispatch batches for operational grouping.
- Driver shifts and courier assignment by zone.
- Website map page with zones, stops and route lines.
- Route Sheet PDF report.

Main entities
-------------

- ``courier.zone``
- ``courier.gpx.track``
- ``courier.dispatch.batch``
- ``courier.route``
- ``courier.route.stop``
- ``courier.driver.shift``

Security
--------

Two hierarchical groups are included:

- ``Courier User``
- ``Courier Admin`` (implies Courier User)

Record rules restrict zone and route visibility for Courier Users.

GPX lifecycle
-------------

- Place ``.gpx`` files in ``data/routes/``.
- On module install/update, the post-init hook imports the files into ``courier.gpx.track``.
- Route generation wizard can sequence stops by nearest point on the GPX line.

Developer notes
---------------

- Includes demo data, tests, Ukrainian translation scaffold, report, and website map template.
- Designed to satisfy training requirements while keeping architecture suitable for later scaling.
