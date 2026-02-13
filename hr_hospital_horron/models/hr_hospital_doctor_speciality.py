from odoo import fields, models


class DoctorSpeciality(models.Model):
    _name = "hr.hospital.doctor.speciality"
    _description = "Doctor Speciality"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(size=10, required=True)
    description = fields.Text(translate=True)
    active = fields.Boolean(default=True)
    doctor_ids = fields.One2many(
        comodel_name="hr.hospital.doctor",
        inverse_name="speciality_id",
        string="Doctors",
    )
