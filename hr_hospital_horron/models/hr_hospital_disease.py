from odoo import fields, models


class HospitalDisease(models.Model):
    _name = "hr.hospital.disease"
    _description = "Disease Type"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    description = fields.Text(translate=True)
    parent_id = fields.Many2one(
        comodel_name="hr.hospital.disease",
        string="Parent Disease",
        ondelete="set null",
    )
    child_ids = fields.One2many(
        comodel_name="hr.hospital.disease",
        inverse_name="parent_id",
        string="Child Diseases",
    )
    icd10_code = fields.Char(string="ICD-10 Code", size=10)
    danger_level = fields.Selection(
        selection=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
    )
    is_contagious = fields.Boolean(string="Contagious")
    symptoms = fields.Text(translate=True)
    region_country_ids = fields.Many2many(
        comodel_name="res.country",
        relation="hr_hospital_disease_region_country_rel",
        column1="disease_id",
        column2="country_id",
        string="Regions",
    )
