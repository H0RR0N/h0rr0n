from odoo import fields, models


class HospitalDoctor(models.Model):
    _name = "hr.hospital.doctor"
    _description = "Doctor"
    _order = "name"

    name = fields.Char(required=True)
    specialization = fields.Char()
    phone = fields.Char()
    email = fields.Char()
    mentor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        string="Mentor Doctor",
        ondelete="set null",
    )
    intern_ids = fields.One2many(
        comodel_name="hr.hospital.doctor",
        inverse_name="mentor_id",
        string="Interns",
    )
    patient_ids = fields.One2many(
        comodel_name="hr.hospital.patient",
        inverse_name="doctor_id",
        string="Patients",
    )
