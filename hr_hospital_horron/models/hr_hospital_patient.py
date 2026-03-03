from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..utils import fill_name_parts_from_name


class HospitalPatient(models.Model):
    _name = "hr.hospital.patient"
    _description = "Patient"
    _order = "name"
    _inherit = ["hr.hospital.abstract.person"]

    name = fields.Char(
        compute="_compute_name",
        store=True,
        precompute=True,
        default=lambda self: self.env._("Unnamed Patient"),
    )

    doctor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        string="Observing Doctor",
        ondelete="set null",
    )
    personal_doctor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        string="Personal Doctor",
        related="doctor_id",
        store=True,
        readonly=False,
    )
    passport_number = fields.Char(size=10)
    contact_person_id = fields.Many2one(
        comodel_name="hr.hospital.contact.person",
        ondelete="set null",
    )
    blood_group = fields.Selection(
        selection=[
            ("o+", "O+"),
            ("o-", "O-"),
            ("a+", "A+"),
            ("a-", "A-"),
            ("b+", "B+"),
            ("b-", "B-"),
            ("ab+", "AB+"),
            ("ab-", "AB-"),
        ],
    )
    allergies = fields.Text()
    insurance_company_id = fields.Many2one(
        comodel_name="res.partner",
        domain=[("is_company", "=", True)],
    )
    insurance_policy_number = fields.Char()
    doctor_history_ids = fields.One2many(
        comodel_name="hr.hospital.patient.doctor.history",
        inverse_name="patient_id",
    )
    visit_ids = fields.One2many(
        comodel_name="hr.hospital.visit",
        inverse_name="patient_id",
    )
    diagnosis_ids = fields.One2many(
        comodel_name="hr.hospital.medical.diagnosis",
        inverse_name="patient_id",
    )
    visit_count = fields.Integer(compute="_compute_visit_count")

    @api.depends("last_name", "first_name", "middle_name")
    def _compute_name(self):
        for rec in self:
            parts = [rec.last_name, rec.first_name, rec.middle_name]
            parts = [part for part in parts if part]
            fallback_name = rec._origin.name if rec._origin and rec._origin.id else False
            rec.name = " ".join(parts) if parts else (fallback_name or self.env._("Unnamed Patient"))

    def name_get(self):
        return [(rec.id, rec.full_name or rec.name) for rec in self]

    @api.depends("visit_ids")
    def _compute_visit_count(self):
        for rec in self:
            rec.visit_count = len(rec.visit_ids)

    @api.constrains("birth_date")
    def _check_birth_date(self):
        for rec in self:
            if not rec.birth_date or rec.birth_date >= fields.Date.today():
                raise ValidationError(self.env._("Patient age must be greater than 0."))

    def _create_doctor_history(self, doctor_id, assign_date=None, reason=None):
        if not doctor_id:
            return
        vals = {
            "patient_id": self.id,
            "doctor_id": doctor_id,
        }
        if assign_date:
            vals["assign_date"] = assign_date
        if reason:
            vals["change_reason"] = reason
        self.env["hr.hospital.patient.doctor.history"].create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        result = []
        for vals in vals_list:
            result.append(fill_name_parts_from_name(vals))

        records = super().create(result)
        skip = self.env.context.get("skip_doctor_history") or self.env.context.get("install_mode")
        if skip:
            return records
        for rec in records:
            if rec.personal_doctor_id:
                rec._create_doctor_history(rec.personal_doctor_id.id)
        return records

    def write(self, vals):
        if self.env.context.get("skip_doctor_history") or self.env.context.get("install_mode"):
            return super().write(vals)

        tracked = {}
        if "personal_doctor_id" in vals or "doctor_id" in vals:
            for rec in self:
                tracked[rec.id] = rec.personal_doctor_id.id or rec.doctor_id.id

        result = super().write(vals)

        if tracked:
            new_doctor_id = vals.get("personal_doctor_id") or vals.get("doctor_id")
            if new_doctor_id:
                for rec in self:
                    if tracked.get(rec.id) != new_doctor_id:
                        rec._create_doctor_history(
                            new_doctor_id,
                            assign_date=self.env.context.get("history_date"),
                            reason=self.env.context.get("history_reason"),
                        )
        return result

    def action_open_visit_history(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "hr_hospital_horron.hr_hospital_visit_action"
        )
        action["domain"] = [("patient_id", "=", self.id)]
        action["context"] = {
            **{k: v for k, v in self.env.context.items() if k != "group_by"},
            "default_patient_id": self.id,
        }
        return action

    def action_create_visit(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("New Visit"),
            "res_model": "hr.hospital.visit",
            "view_mode": "form",
            "target": "current",
            "context": {
                **self.env.context,
                "default_patient_id": self.id,
                "default_doctor_id": self.personal_doctor_id.id,
                "default_visit_type": "repeat" if self.visit_ids else "first",
            },
        }
