"""Core model tests for Vesna Macarons Courier."""

from __future__ import annotations

import base64

from odoo.tests.common import TransactionCase


class TestCourierModels(TransactionCase):
    """Validate core courier models and their minimal workflows."""

    @classmethod
    def setUpClass(cls):
        """Build baseline records used by all test methods."""
        super().setUpClass()
        cls.zone = cls.env["courier.zone"].create(
            {
                "name": "Test Zone",
                "code": "test_zone",
                "polygon_geojson": "{\"type\":\"Polygon\",\"coordinates\":[[[30.70,46.40],[30.80,46.40],[30.80,46.50],[30.70,46.50],[30.70,46.40]]]}" ,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Courier Partner",
                "courier_latitude": 46.45,
                "courier_longitude": 30.75,
                "courier_zone_manual": False,
            }
        )

    def test_01_zone_contains_point(self):
        """Zone should correctly include points within its polygon."""
        self.assertTrue(self.zone.contains_point(46.45, 30.75))

    def test_02_gpx_track_parse(self):
        """GPX track parser should build GeoJSON line and checksum."""
        gpx_text = (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<gpx version='1.1' creator='test' xmlns='http://www.topografix.com/GPX/1/1'>"
            "<trk><trkseg>"
            "<trkpt lat='46.45' lon='30.75'></trkpt>"
            "<trkpt lat='46.46' lon='30.76'></trkpt>"
            "</trkseg></trk>"
            "</gpx>"
        )
        track = self.env["courier.gpx.track"].create(
            {
                "name": "Test Track",
                "code": "test_track",
                "zone_id": self.zone.id,
                "source": "manual",
                "gpx_file": base64.b64encode(gpx_text.encode()),
                "gpx_filename": "test.gpx",
            }
        )
        track.action_parse_gpx()
        self.assertTrue(track.line_geojson)
        self.assertEqual(track.point_count, 2)
        self.assertTrue(track.checksum)

    def test_03_dispatch_batch_counts(self):
        """Dispatch batch should expose route and picking counters."""
        batch = self.env["courier.dispatch.batch"].create({"zone_id": self.zone.id})
        self.assertEqual(batch.route_count, 0)
        self.assertEqual(batch.picking_count, 0)

    def test_04_route_stats(self):
        """Route should compute stop statistics from related records."""
        route = self.env["courier.route"].create(
            {
                "zone_id": self.zone.id,
                "courier_id": self.env.user.id,
            }
        )
        self.env["courier.route.stop"].create(
            {
                "route_id": route.id,
                "sequence": 10,
                "partner_id": self.partner.id,
                "latitude": 46.45,
                "longitude": 30.75,
            }
        )
        route._compute_stop_stats()
        self.assertEqual(route.total_stops, 1)
        self.assertEqual(route.delivered_stops, 0)

    def test_05_route_stop_status_actions(self):
        """Route stop state helpers should update delivery status."""
        route = self.env["courier.route"].create(
            {
                "zone_id": self.zone.id,
                "courier_id": self.env.user.id,
            }
        )
        stop = self.env["courier.route.stop"].create(
            {
                "route_id": route.id,
                "sequence": 10,
                "partner_id": self.partner.id,
                "latitude": 46.45,
                "longitude": 30.75,
            }
        )
        stop.action_mark_delivered()
        self.assertEqual(stop.status, "delivered")
        self.assertTrue(stop.delivered_at)

    def test_06_driver_shift_flow(self):
        """Driver shift should transition from draft to open to closed."""
        shift = self.env["courier.driver.shift"].create(
            {
                "user_id": self.env.user.id,
                "zone_id": self.zone.id,
                "start_at": "2026-03-01 08:00:00",
            }
        )
        shift.action_open_shift()
        self.assertEqual(shift.state, "open")
        shift.action_close_shift()
        self.assertEqual(shift.state, "closed")
        self.assertTrue(shift.end_at)
