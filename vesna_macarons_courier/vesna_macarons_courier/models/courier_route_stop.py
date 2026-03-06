"""Route stop model."""

from __future__ import annotations

from odoo import _, api, fields, models


class CourierRouteStop(models.Model):
    """Represents one delivery point on a courier route."""

    _name = "courier.route.stop"
    _description = "Courier Route Stop"
    _order = "route_id, sequence, id"

    name = fields.Char(compute="_compute_name", store=True)
    route_id = fields.Many2one("courier.route", required=True, ondelete="cascade")
    zone_id = fields.Many2one(related="route_id.zone_id", store=True)
    sequence = fields.Integer(default=10)
    picking_id = fields.Many2one("stock.picking", ondelete="set null")
    partner_id = fields.Many2one("res.partner", ondelete="set null")
    latitude = fields.Float(digits=(16, 8))
    longitude = fields.Float(digits=(16, 8))
    status = fields.Selection(
        [("pending", "Pending"), ("delivered", "Delivered"), ("failed", "Failed")],
        default="pending",
        required=True,
    )
    delivered_at = fields.Datetime()
    note = fields.Text()

    @api.depends("route_id.name", "sequence", "partner_id")
    def _compute_name(self):
        """Generate a readable stop name."""
        for record in self:
            partner_name = record.partner_id.display_name or _("Unknown customer")
            route_name = record.route_id.name or _("Route")
            record.name = f"{route_name} / {record.sequence} / {partner_name}"

    @api.onchange("picking_id")
    def _onchange_picking_id(self):
        """Copy delivery coordinates from stock picking partner."""
        for record in self:
            if not record.picking_id:
                continue
            partner = record.picking_id.partner_id
            record.partner_id = partner
            record.latitude = partner.courier_latitude
            record.longitude = partner.courier_longitude

    def action_mark_delivered(self):
        """Set stop status to delivered and update timestamp."""
        self.write({"status": "delivered", "delivered_at": fields.Datetime.now()})

    def action_mark_failed(self):
        """Set stop status to failed."""
        self.write({"status": "failed"})
