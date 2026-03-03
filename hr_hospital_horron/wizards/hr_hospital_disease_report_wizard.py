from datetime import datetime, time

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DiseaseReportWizard(models.TransientModel):
    _name = "hr.hospital.disease.report.wizard"
    _description = "Disease Report"

    doctor_ids = fields.Many2many(
        comodel_name="hr.hospital.doctor",
        string="Doctors",
    )
    disease_ids = fields.Many2many(
        comodel_name="hr.hospital.disease",
        string="Diseases",
    )
    date_start = fields.Date(
        required=True,
        default=lambda self: fields.Date.start_of(
            fields.Date.context_today(self), "month"
        ),
    )
    date_end = fields.Date(
        required=True,
        default=lambda self: fields.Date.end_of(
            fields.Date.context_today(self), "month"
        ),
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or []
        if not active_ids and self.env.context.get("active_id"):
            active_ids = [self.env.context["active_id"]]
        if active_model == "hr.hospital.doctor" and active_ids and "doctor_ids" in fields_list:
            vals["doctor_ids"] = [(6, 0, active_ids)]
        return vals

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(self.env._("End date must be after start date."))

    def _get_domain(self):
        self.ensure_one()
        start_dt = datetime.combine(self.date_start, time.min)
        end_dt = datetime.combine(self.date_end, time.max)
        domain = [
            ("visit_id.planned_datetime", ">=", start_dt),
            ("visit_id.planned_datetime", "<=", end_dt),
        ]
        if self.doctor_ids:
            domain.append(("visit_id.doctor_id", "in", self.doctor_ids.ids))
        if self.disease_ids:
            domain.append(("disease_id", "in", self.disease_ids.ids))
        return domain

    def action_generate(self):
        self.ensure_one()
        diagnoses = self.env["hr.hospital.medical.diagnosis"].search(self._get_domain())
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Diagnoses"),
            "res_model": "hr.hospital.medical.diagnosis",
            "view_mode": "list,form,pivot,graph",
            "domain": [("id", "in", diagnoses.ids)],
            "context": {
                **self.env.context,
                "search_default_group_by_disease": 1,
            },
        }
