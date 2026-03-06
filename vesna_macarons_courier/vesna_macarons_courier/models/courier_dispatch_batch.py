"""Dispatch batch model."""

from __future__ import annotations

from odoo import _, api, fields, models


class CourierDispatchBatch(models.Model):
    """Groups deliveries to generate one or multiple courier routes."""

    _name = "courier.dispatch.batch"
    _description = "Courier Dispatch Batch"
    _order = "date_planned desc, id desc"

    name = fields.Char(default="New", readonly=True, copy=False)
    zone_id = fields.Many2one("courier.zone", required=True, ondelete="restrict")
    date_planned = fields.Date(default=fields.Date.context_today)
    state = fields.Selection(
        [("draft", "Draft"), ("assigned", "Assigned"), ("done", "Done")],
        default="draft",
        required=True,
    )
    picking_ids = fields.Many2many(
        "stock.picking",
        "courier_dispatch_batch_picking_rel",
        "batch_id",
        "picking_id",
        string="Delivery Transfers",
    )
    route_ids = fields.One2many("courier.route", "batch_id")
    route_count = fields.Integer(compute="_compute_counts")
    picking_count = fields.Integer(compute="_compute_counts")

    @api.model_create_multi
    def create(self, vals_list):
        """Assign sequence-based identifiers to dispatch batches."""
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = sequence.next_by_code("courier.dispatch.batch") or "New"
        return super().create(vals_list)

    @api.depends("picking_ids", "route_ids")
    def _compute_counts(self):
        """Compute related object counters used in stat buttons."""
        for record in self:
            record.picking_count = len(record.picking_ids)
            record.route_count = len(record.route_ids)

    def action_assign_zone_to_pickings(self):
        """Recompute and apply delivery zone on all pickings in the batch."""
        for record in self:
            record.picking_ids.action_assign_courier_zone()

    def action_mark_assigned(self):
        """Move batch to assigned state."""
        self.write({"state": "assigned"})

    def action_mark_done(self):
        """Move batch to done state."""
        self.write({"state": "done"})

    def action_open_routes(self):
        """Open routes created from the current dispatch batch."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Routes"),
            "res_model": "courier.route",
            "view_mode": "tree,form,kanban",
            "domain": [("batch_id", "=", self.id)],
            "context": {"default_batch_id": self.id, "default_zone_id": self.zone_id.id},
        }
