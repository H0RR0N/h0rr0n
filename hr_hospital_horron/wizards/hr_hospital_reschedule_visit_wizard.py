from datetime import datetime, time

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..utils import normalize_time_value, validate_time_value


class RescheduleVisitWizard(models.TransientModel):
    _name = "hr.hospital.reschedule.visit.wizard"
    _description = "Reschedule Visit"

    current_visit_id = fields.Many2one(
        comodel_name="hr.hospital.visit",
        string="Current Visit",
        required=True,
        readonly=True,
    )
    new_doctor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        string="New Doctor",
    )
    new_date = fields.Date(required=True)
    new_time = fields.Float(
        required=True,
        help="Use HH:MM in the range 00:00-23:59.",
    )
    reason = fields.Text(required=True)

    @api.onchange("new_time")
    def _onchange_new_time(self):
        for rec in self:
            rec.new_time = normalize_time_value(rec.new_time)

    @api.constrains("new_time")
    def _check_new_time(self):
        for rec in self:
            validate_time_value(self.env, rec.new_time)

    def action_reschedule(self):
        self.ensure_one()
        visit = self.current_visit_id
        if visit.state == "done":
            raise ValidationError(self.env._("Completed visits cannot be rescheduled."))
        self.new_time = normalize_time_value(self.new_time)
        validate_time_value(self.env, self.new_time)

        total_minutes = int(round(self.new_time * 60))
        new_hour, new_minute = divmod(total_minutes, 60)
        if new_hour >= 24:
            raise ValidationError(self.env._("Time must be between 00:00 and 23:59."))

        new_datetime = datetime.combine(self.new_date, time(new_hour, new_minute))

        visit.write(
            {
                "state": "cancelled",
            }
        )

        new_visit = self.env["hr.hospital.visit"].create(
            {
                "visit_date": new_datetime,
                "patient_id": visit.patient_id.id,
                "doctor_id": (self.new_doctor_id or visit.doctor_id).id,
                "visit_type": visit.visit_type,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.hospital.visit",
            "res_id": new_visit.id,
            "view_mode": "form",
        }
