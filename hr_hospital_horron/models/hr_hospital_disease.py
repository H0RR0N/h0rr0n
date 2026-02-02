from odoo import fields, models


class HospitalDisease(models.Model):
    _name = "hr.hospital.disease"
    _description = "Disease Type"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char()
    description = fields.Text()
