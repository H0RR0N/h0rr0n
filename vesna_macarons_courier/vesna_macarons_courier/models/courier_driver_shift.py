"""Courier driver shift model."""

from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CourierDriverShift(models.Model):
    """Represents a courier shift bound to one zone and time interval."""

    _name = "courier.driver.shift"
    _description = "Courier Driver Shift"
    _order = "start_at desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    user_id = fields.Many2one("res.users", string="Courier", required=True, ondelete="restrict")
    zone_id = fields.Many2one("courier.zone", required=True, ondelete="restrict")
    start_at = fields.Datetime(required=True, default=fields.Datetime.now)
    end_at = fields.Datetime()
    state = fields.Selection(
        [("draft", "Draft"), ("open", "Open"), ("closed", "Closed")],
        default="draft",
        required=True,
    )
    note = fields.Text()

    @api.depends("user_id", "zone_id", "start_at")
    def _compute_name(self):
        """Build a user-friendly shift name."""
        for record in self:
            stamp = fields.Datetime.to_string(record.start_at) if record.start_at else _("No date")
            record.name = f"{record.user_id.display_name} / {record.zone_id.name} / {stamp}"

    @api.constrains("start_at", "end_at")
    def _check_date_range(self):
        """Validate shift boundaries."""
        for record in self:
            if record.end_at and record.end_at < record.start_at:
                raise ValidationError(_("Shift end time cannot be earlier than start time."))

    @api.constrains("user_id", "state", "start_at", "end_at")
    def _check_overlap(self):
        """Avoid overlapping active shifts for the same courier."""
        for record in self.filtered(lambda shift: shift.state in ("draft", "open")):
            domain = [
                ("id", "!=", record.id),
                ("user_id", "=", record.user_id.id),
                ("state", "in", ["draft", "open"]),
            ]
            overlaps = self.search(domain)
            for other in overlaps:
                start_a = record.start_at
                end_a = record.end_at or fields.Datetime.now()
                start_b = other.start_at
                end_b = other.end_at or fields.Datetime.now()
                if start_a <= end_b and start_b <= end_a:
                    raise ValidationError(_("Courier already has an overlapping active shift."))

    def action_open_shift(self):
        """Open a shift when courier starts working."""
        self.write({"state": "open"})

    def action_close_shift(self):
        """Close shift and stamp end datetime when missing."""
        for record in self:
            values = {"state": "closed"}
            if not record.end_at:
                values["end_at"] = fields.Datetime.now()
            record.write(values)
