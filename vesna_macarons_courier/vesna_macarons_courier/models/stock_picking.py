"""Stock picking extensions for courier routing."""

from __future__ import annotations

from odoo import api, fields, models


class StockPicking(models.Model):
    """Adds route-related fields and zone assignment methods to deliveries."""

    _inherit = "stock.picking"

    courier_zone_id = fields.Many2one(
        "courier.zone",
        compute="_compute_courier_zone_id",
        store=True,
        readonly=False,
        ondelete="set null",
    )
    courier_route_id = fields.Many2one("courier.route", ondelete="set null")
    courier_stop_id = fields.Many2one("courier.route.stop", ondelete="set null")
    courier_courier_id = fields.Many2one("res.users", related="courier_route_id.courier_id", store=True)
    courier_delivery_sequence = fields.Integer(default=10)
    courier_route_state = fields.Selection(related="courier_route_id.state", store=True)

    @api.depends("partner_id", "partner_id.courier_zone_id")
    def _compute_courier_zone_id(self):
        """Compute delivery zone from customer partner zone assignment."""
        for picking in self:
            picking.courier_zone_id = picking.partner_id.courier_zone_id

    def action_assign_courier_zone(self):
        """Recompute courier zone on linked partners and pickings."""
        partners = self.mapped("partner_id")
        partners.action_recompute_courier_zone()
        for picking in self:
            picking.courier_zone_id = picking.partner_id.courier_zone_id
        return True
