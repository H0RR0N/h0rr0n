from odoo import fields, models


class HospitalVisit(models.Model):
    _name = "hr.hospital.visit"
    _description = "Patient Visit"
    _order = "visit_date desc"

    name = fields.Char(string="Reference", required=True, default="New")
    visit_date = fields.Datetime(required=True)
    patient_id = fields.Many2one(
        comodel_name="hr.hospital.patient",
        string="Patient",
        required=True,
        ondelete="cascade",
    )
    doctor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        string="Doctor",
        required=True,
        ondelete="restrict",
    )
    disease_id = fields.Many2one(
        comodel_name="hr.hospital.disease",
        string="Disease",
        ondelete="set null",
    )
    notes = fields.Text()
