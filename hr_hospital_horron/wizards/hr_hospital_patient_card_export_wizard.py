import base64
import csv
import io
import json
from datetime import datetime, time

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PatientCardExportWizard(models.TransientModel):
    _name = "hr.hospital.patient.card.export.wizard"
    _description = "Patient Card Export"

    patient_id = fields.Many2one(
        comodel_name="hr.hospital.patient",
        string="Patient",
        required=True,
    )
    date_start = fields.Date()
    date_end = fields.Date()
    include_diagnoses = fields.Boolean(default=True)
    include_recommendations = fields.Boolean(default=True)
    language_id = fields.Many2one(
        comodel_name="res.lang",
        string="Language",
    )
    export_format = fields.Selection(
        selection=[("json", "JSON"), ("csv", "CSV")],
        default="json",
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        patient_id = self.env.context.get("default_patient_id")
        if patient_id and "language_id" in fields_list:
            patient = self.env["hr.hospital.patient"].browse(patient_id)
            values["language_id"] = patient.language_id.id
        return values

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(self.env._("End date must be after start date."))

    def _get_visits_domain(self):
        domain = [("patient_id", "=", self.patient_id.id)]
        if self.date_start:
            start_dt = datetime.combine(self.date_start, time.min)
            domain.append(("planned_datetime", ">=", start_dt))
        if self.date_end:
            end_dt = datetime.combine(self.date_end, time.max)
            domain.append(("planned_datetime", "<=", end_dt))
        return domain

    def _build_json(self, visits):
        payload = {
            "patient": {
                "id": self.patient_id.id,
                "name": self.patient_id.full_name or self.patient_id.name,
                "birth_date": str(self.patient_id.birth_date or ""),
                "gender": self.patient_id.gender,
                "phone": self.patient_id.phone,
                "email": self.patient_id.email,
            },
            "visits": [],
        }
        for visit in visits:
            item = {
                "date": fields.Datetime.to_string(visit.planned_datetime),
                "doctor": visit.doctor_id.name,
                "state": visit.state,
                "type": visit.visit_type,
            }
            if self.include_recommendations:
                item["recommendations"] = visit.recommendations
            if self.include_diagnoses:
                item["diagnoses"] = [
                    {
                        "disease": diag.disease_id.name,
                        "severity": diag.severity,
                        "approved": diag.approved,
                    }
                    for diag in visit.diagnosis_ids
                ]
            payload["visits"].append(item)
        return json.dumps(payload, ensure_ascii=True, indent=2)

    def _build_csv(self, visits):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Visit Date",
                "Doctor",
                "State",
                "Visit Type",
                "Disease",
                "Severity",
                "Approved",
                "Recommendations",
            ]
        )
        for visit in visits:
            if self.include_diagnoses and visit.diagnosis_ids:
                for diag in visit.diagnosis_ids:
                    writer.writerow(
                        [
                            fields.Datetime.to_string(visit.planned_datetime),
                            visit.doctor_id.name,
                            visit.state,
                            visit.visit_type,
                            diag.disease_id.name,
                            diag.severity,
                            diag.approved,
                            visit.recommendations if self.include_recommendations else "",
                        ]
                    )
            else:
                writer.writerow(
                    [
                        fields.Datetime.to_string(visit.planned_datetime),
                        visit.doctor_id.name,
                        visit.state,
                        visit.visit_type,
                        "",
                        "",
                        "",
                        visit.recommendations if self.include_recommendations else "",
                    ]
                )
        return output.getvalue()

    def action_export(self):
        self.ensure_one()
        visits = self.env["hr.hospital.visit"].search(
            self._get_visits_domain(), order="planned_datetime"
        )
        if self.export_format == "json":
            content = self._build_json(visits)
            filename = f"patient_{self.patient_id.id}_card.json"
            mimetype = "application/json"
        else:
            content = self._build_csv(visits)
            filename = f"patient_{self.patient_id.id}_card.csv"
            mimetype = "text/csv"

        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "datas": base64.b64encode(content.encode("utf-8")),
                "res_model": "hr.hospital.patient",
                "res_id": self.patient_id.id,
                "mimetype": mimetype,
            }
        )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
