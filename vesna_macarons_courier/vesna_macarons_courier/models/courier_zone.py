"""Courier delivery zone model."""

from __future__ import annotations

import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CourierZone(models.Model):
    """Defines a geospatial area served by a subset of couriers."""

    _name = "courier.zone"
    _description = "Courier Zone"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    color = fields.Char(default="#1f6feb")
    version = fields.Integer(default=1)
    active_from = fields.Date()
    active_to = fields.Date()
    polygon_geojson = fields.Text(required=True)
    note = fields.Text()

    courier_user_ids = fields.Many2many(
        "res.users",
        "courier_zone_user_rel",
        "zone_id",
        "user_id",
        string="Couriers",
    )
    route_ids = fields.One2many("courier.route", "zone_id")
    courier_count = fields.Integer(compute="_compute_courier_count")

    _sql_constraints = [
        ("courier_zone_code_unique", "unique(code)", "Zone code must be unique."),
    ]

    @api.depends("courier_user_ids")
    def _compute_courier_count(self):
        """Count couriers assigned to each zone."""
        for record in self:
            record.courier_count = len(record.courier_user_ids)

    @api.constrains("polygon_geojson")
    def _check_polygon_geojson(self):
        """Ensure that polygon data is a valid GeoJSON object."""
        for record in self:
            record._get_polygon_coordinates()

    def _get_polygon_coordinates(self):
        """Return polygon coordinates from a GeoJSON Polygon object."""
        self.ensure_one()
        try:
            geojson = json.loads(self.polygon_geojson or "{}")
        except json.JSONDecodeError as error:
            raise ValidationError(_("Zone geometry is not valid JSON.")) from error

        if geojson.get("type") != "Polygon":
            raise ValidationError(_("Zone geometry must be a GeoJSON Polygon."))

        coordinates = geojson.get("coordinates") or []
        if not coordinates or not isinstance(coordinates[0], list) or len(coordinates[0]) < 3:
            raise ValidationError(_("Zone polygon must contain at least 3 points."))

        return coordinates[0]

    def contains_point(self, latitude, longitude):
        """Check if the given latitude/longitude point is inside this zone polygon."""
        self.ensure_one()
        polygon = self._get_polygon_coordinates()
        return self._point_in_polygon(longitude, latitude, polygon)

    @api.model
    def _find_zone_for_coordinates(self, latitude, longitude):
        """Return the first active zone containing the given coordinates."""
        if latitude is None or longitude is None:
            return False
        for zone in self.search([("active", "=", True)], order="version desc, id asc"):
            if zone.contains_point(latitude, longitude):
                return zone.id
        return False

    @staticmethod
    def _point_in_polygon(x, y, polygon):
        """Perform ray-casting point-in-polygon test with longitude/latitude coordinates."""
        inside = False
        count = len(polygon)
        for index in range(count):
            x1, y1 = polygon[index]
            x2, y2 = polygon[(index + 1) % count]
            intersects = ((y1 > y) != (y2 > y)) and (
                x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1
            )
            if intersects:
                inside = not inside
        return inside

    def action_validate_geojson(self):
        """Validate geometry and return a notification message."""
        for record in self:
            record._get_polygon_coordinates()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Zone geometry is valid"),
                "message": _("GeoJSON validation finished successfully."),
                "type": "success",
                "sticky": False,
            },
        }
