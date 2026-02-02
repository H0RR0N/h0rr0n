from odoo import fields, models


class HospitalPatient(models.Model):
    _name = "hr.hospital.patient"
    _description = "Patient"
    _order = "name"

    name = fields.Char(required=True)
    birthdate = fields.Date()
    phone = fields.Char()
    email = fields.Char()
    doctor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        string="Observing Doctor",
        ondelete="set null",
    )
    visit_ids = fields.One2many(
        comodel_name="hr.hospital.visit",
        inverse_name="patient_id",
        string="Visits",
    )
    notes = fields.Text()
