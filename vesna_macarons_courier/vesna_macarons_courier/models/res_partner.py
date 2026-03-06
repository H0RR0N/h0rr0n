"""Partner extensions for courier zoning."""

from __future__ import annotations

from odoo import _, api, fields, models


class ResPartner(models.Model):
    """Adds courier geolocation and zone assignment to partners."""

    _inherit = "res.partner"

    courier_latitude = fields.Float(digits=(16, 8))
    courier_longitude = fields.Float(digits=(16, 8))
    courier_zone_id = fields.Many2one(
        "courier.zone",
        compute="_compute_courier_zone_id",
        store=True,
        readonly=False,
        ondelete="set null",
    )
    courier_zone_manual = fields.Boolean(
        string="Manual Zone",
        help="Enable to keep zone unchanged by automatic recalculation.",
    )
    courier_zone_note = fields.Char()

    @api.depends("courier_latitude", "courier_longitude", "courier_zone_manual")
    def _compute_courier_zone_id(self):
        """Assign zone automatically from partner coordinates unless locked manually."""
        zone_model = self.env["courier.zone"]
        for partner in self:
            if partner.courier_zone_manual:
                continue
            partner.courier_zone_id = zone_model._find_zone_for_coordinates(
                partner.courier_latitude,
                partner.courier_longitude,
            )

    def action_recompute_courier_zone(self):
        """Force recalculation even for manually assigned records."""
        zone_model = self.env["courier.zone"]
        for partner in self:
            partner.courier_zone_id = zone_model._find_zone_for_coordinates(
                partner.courier_latitude,
                partner.courier_longitude,
            )

    @api.model
    def cron_recompute_courier_zones(self):
        """Recalculate courier zones for partners with coordinates."""
        partners = self.search(
            [
                ("courier_latitude", "!=", 0.0),
                ("courier_longitude", "!=", 0.0),
                ("courier_zone_manual", "=", False),
            ]
        )
        partners.action_recompute_courier_zone()
