{
    "name": "Unique Partner Email",
    "version": "19.0.1.0.0",
    "summary": "Prevents duplicate email addresses across partners (res.partner).",
    "description": """
Unique Partner Email
====================

This module adds a constraint that prevents creating or updating partners
(res.partner) with an email address that is already used by another partner
in the system.

Features
--------

* SQL UNIQUE constraint on normalized email (case-insensitive)
* Python-level validation with clear error messages
* Handles email normalization (lowercase, trim whitespace)
* Full Ukrainian translation included

Configuration
-------------

No configuration needed. The constraint is applied automatically upon
module installation.
""",
    "category": "Tools",
    "author": "H0RR0N",
    "website": "https://github.com/H0RR0N",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [],
    "demo": [],
    "installable": True,
    "application": False,
    "auto_install": False,
    "image": "static/description/icon.png",
    "images": ["static/description/banner.png"],
}
