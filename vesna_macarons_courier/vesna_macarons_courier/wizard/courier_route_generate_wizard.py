"""Wizard for generating routes from stock pickings."""

from __future__ import annotations

import json
import math

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class CourierRouteGenerateWizard(models.TransientModel):
    """Builds route stops from selected delivery transfers."""

    _name = "courier.route.generate.wizard"
    _description = "Courier Route Generate Wizard"

    route_id = fields.Many2one("courier.route", ondelete="set null")
    zone_id = fields.Many2one("courier.zone", required=True, ondelete="restrict")
    courier_id = fields.Many2one("res.users")
    date_planned = fields.Date(default=fields.Date.context_today)
    track_id = fields.Many2one("courier.gpx.track", ondelete="set null")
    picking_ids = fields.Many2many(
        "stock.picking",
        "courier_wizard_picking_rel",
        "wizard_id",
        "picking_id",
        string="Pickings",
        domain="[('picking_type_code','=','outgoing'),('courier_zone_id','=',zone_id)]",
    )

    def _sequence_by_track(self, pickings):
        """Return pickings sorted by nearest index on the GPX polyline."""
        self.ensure_one()
        if not self.track_id or not self.track_id.line_geojson:
            return pickings.sorted(lambda item: (item.courier_delivery_sequence, item.id))

        try:
            geometry = json.loads(self.track_id.line_geojson)
        except (TypeError, ValueError):
            return pickings.sorted(lambda item: (item.courier_delivery_sequence, item.id))
        coordinates = geometry.get("coordinates") or []
        if not coordinates:
            return pickings.sorted(lambda item: (item.courier_delivery_sequence, item.id))

        def nearest_index(picking):
            lat = picking.partner_id.courier_latitude
            lon = picking.partner_id.courier_longitude
            if not lat or not lon:
                return float("inf")
            min_distance = float("inf")
            min_index = float("inf")
            for index, point in enumerate(coordinates):
                point_lon, point_lat = point
                distance = math.dist((lon, lat), (point_lon, point_lat))
                if distance < min_distance:
                    min_distance = distance
                    min_index = index
            return min_index

        return pickings.sorted(lambda item: (nearest_index(item), item.id))

    def action_generate_route(self):
        """Create or update route and append stops from selected pickings."""
        self.ensure_one()
        if not self.picking_ids:
            raise ValidationError(_("Select at least one picking."))

        route = self.route_id
        if not route:
            route = self.env["courier.route"].create(
                {
                    "zone_id": self.zone_id.id,
                    "courier_id": self.courier_id.id,
                    "date_planned": self.date_planned,
                    "track_id": self.track_id.id,
                }
            )

        if self.track_id and route.track_id != self.track_id:
            route.track_id = self.track_id
        if self.courier_id and route.courier_id != self.courier_id:
            route.courier_id = self.courier_id

        sorted_pickings = self._sequence_by_track(self.picking_ids)
        next_sequence = max(route.stop_ids.mapped("sequence") or [0]) + 10
        stop_model = self.env["courier.route.stop"]

        for picking in sorted_pickings:
            partner = picking.partner_id
            stop = stop_model.create(
                {
                    "route_id": route.id,
                    "sequence": next_sequence,
                    "picking_id": picking.id,
                    "partner_id": partner.id,
                    "latitude": partner.courier_latitude,
                    "longitude": partner.courier_longitude,
                }
            )
            picking.write({"courier_route_id": route.id, "courier_stop_id": stop.id})
            next_sequence += 10

        return {
            "type": "ir.actions.act_window",
            "name": _("Route"),
            "res_model": "courier.route",
            "res_id": route.id,
            "view_mode": "form",
            "target": "current",
        }
