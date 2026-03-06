"""Courier route model."""

from __future__ import annotations

from odoo import _, api, fields, models


class CourierRoute(models.Model):
    """Represents a courier route for a specific day and zone."""

    _name = "courier.route"
    _description = "Courier Route"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_planned desc, id desc"

    name = fields.Char(default="New", readonly=True, copy=False)
    zone_id = fields.Many2one("courier.zone", required=True, ondelete="restrict", tracking=True)
    courier_id = fields.Many2one("res.users", string="Courier", tracking=True)
    batch_id = fields.Many2one("courier.dispatch.batch", ondelete="set null")
    date_planned = fields.Date(default=fields.Date.context_today, tracking=True)
    track_id = fields.Many2one("courier.gpx.track", ondelete="set null")
    line_geojson = fields.Text(related="track_id.line_geojson", readonly=True)
    stop_ids = fields.One2many("courier.route.stop", "route_id")
    total_stops = fields.Integer(compute="_compute_stop_stats", store=True)
    delivered_stops = fields.Integer(compute="_compute_stop_stats", store=True)
    state = fields.Selection(
        [("draft", "Draft"), ("in_progress", "In Progress"), ("done", "Done")],
        default="draft",
        required=True,
        tracking=True,
    )
    note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        """Assign sequence-based route numbers."""
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = sequence.next_by_code("courier.route") or "New"
        return super().create(vals_list)

    @api.depends("stop_ids", "stop_ids.status")
    def _compute_stop_stats(self):
        """Compute total and delivered stop counters."""
        for record in self:
            record.total_stops = len(record.stop_ids)
            record.delivered_stops = len(record.stop_ids.filtered(lambda item: item.status == "delivered"))

    def action_start(self):
        """Move route to in-progress status."""
        self.write({"state": "in_progress"})

    def action_done(self):
        """Complete route when all stops are processed."""
        for record in self:
            pending = record.stop_ids.filtered(lambda item: item.status == "pending")
            if pending:
                pending.action_mark_failed()
        self.write({"state": "done"})

    def action_print_route_sheet(self):
        """Print route sheet report."""
        self.ensure_one()
        return self.env.ref("vesna_macarons_courier.action_report_courier_route").report_action(self)

    def action_open_generate_wizard(self):
        """Open route generation wizard prefilled by current route context."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Generate Route Stops"),
            "res_model": "courier.route.generate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_route_id": self.id,
                "default_zone_id": self.zone_id.id,
                "default_courier_id": self.courier_id.id,
                "default_track_id": self.track_id.id,
            },
        }
