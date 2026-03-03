from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MassReassignDoctorWizard(models.TransientModel):
    _name = "hr.hospital.mass.reassign.doctor.wizard"
    _description = "Mass Reassign Doctor"

    old_doctor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        string="Old Doctor",
        required=True,
    )
    new_doctor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        string="New Doctor",
        required=True,
    )
    patient_ids = fields.Many2many(
        comodel_name="hr.hospital.patient",
        string="Patients",
    )
    change_date = fields.Date(default=fields.Date.today)
    reason = fields.Text(required=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids") or []
        if active_ids and "patient_ids" in fields_list:
            values["patient_ids"] = [(6, 0, active_ids)]
        if active_ids and "old_doctor_id" in fields_list:
            doctors = self.env["hr.hospital.patient"].browse(active_ids).mapped(
                "personal_doctor_id"
            )
            if len(doctors) == 1:
                values["old_doctor_id"] = doctors.id
        return values

    @api.onchange("old_doctor_id")
    def _onchange_old_doctor_id(self):
        if self.old_doctor_id:
            return {
                "domain": {
                    "patient_ids": [
                        ("personal_doctor_id", "=", self.old_doctor_id.id)
                    ]
                }
            }
        return {"domain": {"patient_ids": []}}

    @api.constrains("old_doctor_id", "new_doctor_id")
    def _check_doctors(self):
        for rec in self:
            if rec.old_doctor_id and rec.old_doctor_id == rec.new_doctor_id:
                raise ValidationError(self.env._("Old doctor and new doctor must be different."))

    def action_reassign(self):
        self.ensure_one()
        patients = self.patient_ids
        if self.old_doctor_id:
            patients = patients.filtered(
                lambda p: p.personal_doctor_id == self.old_doctor_id
            )
        if not patients:
            raise ValidationError(
                self.env._("Please select at least one patient assigned to the old doctor.")
            )
        ctx = dict(self.env.context)
        ctx.update(
            {
                "history_reason": self.reason,
                "history_date": self.change_date,
            }
        )
        patients.with_context(**ctx).write({"personal_doctor_id": self.new_doctor_id.id})
        return {"type": "ir.actions.act_window_close"}
