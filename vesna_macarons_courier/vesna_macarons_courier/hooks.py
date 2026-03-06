"""Module hooks for loading built-in GPX tracks."""

from __future__ import annotations

import base64
import os

from odoo import SUPERUSER_ID, api
from odoo.modules.module import get_module_resource


def post_init_hook(cr, registry):
    """Load built-in GPX files from the module directory into the database."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    zone_model = env["courier.zone"]
    track_model = env["courier.gpx.track"]

    zones_by_code = {zone.code.lower(): zone for zone in zone_model.search([("code", "!=", False)])}
    routes_dir = get_module_resource("vesna_macarons_courier", "data", "routes")
    if not routes_dir or not os.path.isdir(routes_dir):
        return

    for filename in sorted(os.listdir(routes_dir)):
        if not filename.endswith(".gpx"):
            continue

        code = os.path.splitext(filename)[0]
        path = os.path.join(routes_dir, filename)
        with open(path, "rb") as file_handle:
            raw_content = file_handle.read()

        vals = {
            "name": code.replace("_", " ").title(),
            "code": code,
            "source": "module",
            "gpx_file": base64.b64encode(raw_content),
            "gpx_filename": filename,
            "is_active": True,
        }

        zone = zones_by_code.get(code.split("_")[0])
        if zone:
            vals["zone_id"] = zone.id

        track = track_model.search([("code", "=", code)], limit=1)
        if track:
            track.write(vals)
        else:
            track = track_model.create(vals)

        track.action_parse_gpx()
