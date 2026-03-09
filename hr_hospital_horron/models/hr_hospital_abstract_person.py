from datetime import date
import re

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


class AbstractPerson(models.AbstractModel):
    """Business model for AbstractPerson records."""
    _name = 'hr.hospital.abstract.person'
    _description = 'Abstract Person'
    _inherit = ['image.mixin']
    _abstract = True

    last_name = fields.Char()
    first_name = fields.Char()
    middle_name = fields.Char()
    phone = fields.Char()
    email = fields.Char()
    gender = fields.Selection(
        selection=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ],
    )
    birth_date = fields.Date()
    age = fields.Integer(compute='_compute_age', store=True)
    full_name = fields.Char(compute='_compute_full_name', store=True)
    citizenship_country_id = fields.Many2one(
        comodel_name='res.country',
    )
    language_id = fields.Many2one(comodel_name='res.lang')

    @api.depends('birth_date')
    def _compute_age(self):
        """Compute age."""
        today = date.today()
        for rec in self:
            if rec.birth_date:
                rec.age = relativedelta(today, rec.birth_date).years
            else:
                rec.age = 0

    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_full_name(self):
        """Compute full name."""
        for rec in self:
            parts = [rec.last_name, rec.first_name, rec.middle_name]
            parts = [p for p in parts if p]
            if parts:
                rec.full_name = ' '.join(parts)
            else:
                rec.full_name = getattr(rec, 'name', '') or ''

    @api.constrains('phone')
    def _check_phone_format(self):
        """Validate phone format."""
        phone_pattern = re.compile(r'^\+?[\d\-\s\(\)]+$')
        for rec in self:
            if rec.phone and not phone_pattern.match(rec.phone):
                raise ValidationError(self.env._('Phone number format is invalid.'))

    @api.constrains('email')
    def _check_email_format(self):
        """Validate email format."""
        for rec in self:
            if rec.email and not email_normalize(rec.email):
                raise ValidationError(self.env._('Email format is invalid.'))

    @api.onchange('citizenship_country_id')
    def _onchange_citizenship_country(self):
        """Handle onchange for citizenship country."""
        if not self.citizenship_country_id or self.language_id:
            return
        country_code = (self.citizenship_country_id.code or '').upper()
        if not country_code:
            return
        lang = self.env['res.lang'].search(
            [('code', 'ilike', f'%_{country_code}')], limit=1,
        )
        if lang:
            self.language_id = lang
