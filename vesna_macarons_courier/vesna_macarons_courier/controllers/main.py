"""Website endpoints for courier map view."""

from __future__ import annotations

import json

from odoo import http
from odoo.http import request


class CourierMapController(http.Controller):
    """Expose map page and geometry payload for courier operations."""

    @http.route("/courier/map", type="http", auth="user", website=True)
    def courier_map_page(self, **kwargs):
        """Render web page with Leaflet-based courier map."""
        return request.render("vesna_macarons_courier.courier_map_page")

    @http.route("/courier/map/data", type="json", auth="user")
    def courier_map_data(self):
        """Return zones, stops and GPX lines for map rendering."""
        zone_model = request.env["courier.zone"].sudo()
        stop_model = request.env["courier.route.stop"].sudo()
        route_model = request.env["courier.route"].sudo()

        zones = []
        for zone in zone_model.search([("active", "=", True)]):
            polygon = []
            if zone.polygon_geojson:
                try:
                    polygon = (json.loads(zone.polygon_geojson).get("coordinates") or [[]])[0]
                except (TypeError, ValueError, KeyError):
                    polygon = []
            zones.append(
                {
                    "id": zone.id,
                    "name": zone.name,
                    "color": zone.color or "#1f6feb",
                    "polygon": polygon,
                }
            )

        stops = []
        for stop in stop_model.search([], order="route_id, sequence"):
            if not stop.latitude or not stop.longitude:
                continue
            stops.append(
                {
                    "id": stop.id,
                    "name": stop.name,
                    "route": stop.route_id.name,
                    "status": stop.status,
                    "lat": stop.latitude,
                    "lon": stop.longitude,
                }
            )

        lines = []
        for route in route_model.search([("track_id", "!=", False)]):
            coords = []
            if route.line_geojson:
                try:
                    coords = json.loads(route.line_geojson).get("coordinates") or []
                except (TypeError, ValueError, KeyError):
                    coords = []
            if coords:
                lines.append(
                    {
                        "id": route.id,
                        "name": route.name,
                        "state": route.state,
                        "coordinates": coords,
                    }
                )

        return {"zones": zones, "stops": stops, "lines": lines}
