"""GPX track model used for route guidance."""

from __future__ import annotations

import base64
import hashlib
import json
from xml.etree import ElementTree

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class CourierGpxTrack(models.Model):
    """Stores GPX files and parsed line geometry for map visualization."""

    _name = "courier.gpx.track"
    _description = "Courier GPX Track"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    zone_id = fields.Many2one("courier.zone", ondelete="set null")
    version = fields.Integer(default=1)
    source = fields.Selection(
        [("module", "Module"), ("manual", "Manual")],
        default="module",
        required=True,
    )
    checksum = fields.Char(readonly=True)
    gpx_file = fields.Binary(required=True, attachment=True)
    gpx_filename = fields.Char()
    line_geojson = fields.Text(readonly=True)
    point_count = fields.Integer(readonly=True)
    parsed_at = fields.Datetime(readonly=True)
    is_active = fields.Boolean(default=True)
    note = fields.Text()

    _sql_constraints = [
        ("courier_gpx_track_code_unique", "unique(code)", "Track code must be unique."),
    ]

    def _extract_track_points(self, payload):
        """Parse GPX payload and return list of [longitude, latitude] coordinates."""
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError as error:
            raise ValidationError(_("Invalid GPX file content.")) from error

        namespace = {}
        if "}" in root.tag:
            namespace["gpx"] = root.tag.split("}", 1)[0].strip("{")
            nodes = root.findall(".//gpx:trkpt", namespace)
        else:
            nodes = root.findall(".//trkpt")

        points = []
        for node in nodes:
            lat = node.get("lat")
            lon = node.get("lon")
            if lat is None or lon is None:
                continue
            points.append([float(lon), float(lat)])

        if len(points) < 2:
            raise ValidationError(_("GPX track should have at least 2 points."))
        return points

    def action_parse_gpx(self):
        """Parse file, calculate checksum and store a GeoJSON line string."""
        for record in self:
            payload = base64.b64decode(record.gpx_file or b"")
            if not payload:
                raise ValidationError(_("Upload a GPX file before parsing."))

            points = record._extract_track_points(payload)
            line = {"type": "LineString", "coordinates": points}
            record.write(
                {
                    "checksum": hashlib.sha256(payload).hexdigest(),
                    "line_geojson": json.dumps(line),
                    "point_count": len(points),
                    "parsed_at": fields.Datetime.now(),
                }
            )
        return True
