from datetime import datetime, time

from odoo import api, fields, models, _
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
    country_ids = fields.Many2many(
        comodel_name="res.country",
        string="Countries",
    )
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    report_type = fields.Selection(
        selection=[("detailed", "Detailed"), ("summary", "Summary")],
        default="detailed",
        required=True,
    )
    group_by = fields.Selection(
        selection=[
            ("doctor", "Doctor"),
            ("disease", "Disease"),
            ("month", "Month"),
            ("country", "Country"),
        ],
        default="doctor",
        required=True,
    )
    summary_result = fields.Text(readonly=True)

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(_("End date must be after start date."))

    @api.onchange("country_ids")
    def _onchange_country_ids(self):
        if self.country_ids:
            return {
                "domain": {
                    "doctor_ids": [
                        ("education_country_id", "in", self.country_ids.ids)
                    ]
                }
            }
        return {}

    def _get_domain(self):
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
        if self.country_ids:
            domain.append(
                (
                    "visit_id.patient_id.citizenship_country_id",
                    "in",
                    self.country_ids.ids,
                )
            )
        return domain

    def get_report_data(self):
        self.ensure_one()
        diagnosis_model = self.env["hr.hospital.medical.diagnosis"]
        if self.report_type == "detailed":
            return diagnosis_model.search(self._get_domain())

        groupby_map = {
            "doctor": "visit_id.doctor_id",
            "disease": "disease_id",
            "month": "visit_id.planned_datetime:month",
            "country": "visit_id.patient_id.citizenship_country_id",
        }
        groupby = groupby_map.get(self.group_by)
        data = diagnosis_model.read_group(
            self._get_domain(), ["id"], [groupby], lazy=False
        )
        summary = []
        for entry in data:
            label = entry.get(groupby)
            if isinstance(label, (list, tuple)):
                label = label[1]
            summary.append({"group": label or _("Undefined"), "count": entry["__count"]})
        return summary

    def action_generate(self):
        self.ensure_one()
        if self.report_type == "detailed":
            diagnoses = self.get_report_data()
            return {
                "type": "ir.actions.act_window",
                "name": _("Diagnoses"),
                "res_model": "hr.hospital.medical.diagnosis",
                "view_mode": "list,form",
                "domain": [("id", "in", diagnoses.ids)],
            }

        summary = self.get_report_data()
        lines = [f"{item['group']}: {item['count']}" for item in summary]
        self.summary_result = "\n".join(lines)
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.hospital.disease.report.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
