from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HospitalDoctor(models.Model):
    """Business model for HospitalDoctor records."""
    _name = 'hr.hospital.doctor'
    _description = 'Doctor'
    _order = 'name'
    _inherit = ['hr.hospital.abstract.person']

    name = fields.Char(required=True)
    user_id = fields.Many2one(
        comodel_name='res.users',
        ondelete='set null',
    )
    speciality_id = fields.Many2one(
        comodel_name='hr.hospital.doctor.speciality',
        ondelete='set null',
    )
    is_intern = fields.Boolean(string='Intern')
    mentor_id = fields.Many2one(
        comodel_name='hr.hospital.doctor',
        string='Mentor Doctor',
        ondelete='set null',
        domain=[('is_intern', '=', False)],
    )
    intern_ids = fields.One2many(
        comodel_name='hr.hospital.doctor',
        inverse_name='mentor_id',
        string='Interns',
    )
    intern_names = fields.Char(
        compute='_compute_intern_names',
        string='Interns',
    )
    license_number = fields.Char(required=True, copy=False)
    license_date = fields.Date()
    experience_years = fields.Integer(
        compute='_compute_experience_years', store=True, string='Experience (Years)',
    )
    rating = fields.Float(digits=(3, 2))
    schedule_ids = fields.One2many(
        comodel_name='hr.hospital.doctor.schedule',
        inverse_name='doctor_id',
    )
    education_country_id = fields.Many2one(
        comodel_name='res.country',
    )
    patient_ids = fields.One2many(
        comodel_name='hr.hospital.patient',
        inverse_name='doctor_id',
    )
    active = fields.Boolean(default=True)

    _license_number_unique = models.Constraint(
        'UNIQUE(license_number)',
        'License number must be unique.',
    )
    _rating_range = models.Constraint(
        'CHECK(rating >= 0 AND rating <= 5)',
        'Rating must be between 0 and 5.',
    )

    def get_print_datetime(self):
        """Handle get print datetime."""
        now_utc = fields.Datetime.to_datetime(fields.Datetime.now())
        now_local = fields.Datetime.context_timestamp(self, now_utc)
        return now_local.strftime('%d.%m.%Y %H:%M')

    @api.depends('last_name', 'first_name', 'middle_name', 'name')
    def _compute_full_name(self):
        """Compute full name."""
        for rec in self:
            parts = [rec.last_name, rec.first_name, rec.middle_name]
            parts = [p for p in parts if p]
            rec.full_name = ' '.join(parts) if parts else (rec.name or '')

    @api.depends('intern_ids', 'intern_ids.full_name', 'intern_ids.name')
    def _compute_intern_names(self):
        """Compute intern names."""
        for rec in self:
            names = [intern.full_name or intern.name for intern in rec.intern_ids]
            names = [name for name in names if name]
            rec.intern_names = ', '.join(names)

    @api.depends('license_date')
    def _compute_experience_years(self):
        """Compute experience years."""
        today = date.today()
        for rec in self:
            if rec.license_date:
                rec.experience_years = relativedelta(today, rec.license_date).years
            else:
                rec.experience_years = 0

    @api.constrains('mentor_id', 'is_intern')
    def _check_mentor(self):
        """Validate mentor."""
        for rec in self:
            if rec.mentor_id and not rec.is_intern:
                raise ValidationError(self.env._('Only interns can have a mentor assigned.'))
            if rec.mentor_id and rec.mentor_id.is_intern:
                raise ValidationError(self.env._('Mentor cannot be an intern.'))
            if rec.mentor_id and rec.mentor_id == rec:
                raise ValidationError(self.env._('Doctor cannot be their own mentor.'))

    @api.depends('full_name', 'name', 'speciality_id', 'speciality_id.name')
    def _compute_display_name(self):
        """Compute display name."""
        for rec in self:
            speciality = rec.speciality_id.name or ''
            base_name = rec.full_name or rec.name
            rec.display_name = f'{base_name} ({speciality})' if speciality else base_name

    @api.onchange('is_intern')
    def _onchange_is_intern(self):
        """Handle onchange for is intern."""
        if not self.is_intern:
            self.mentor_id = False
        elif not self.mentor_id:
            domain = [('is_intern', '=', False)]
            if self.speciality_id:
                domain.append(('speciality_id', '=', self.speciality_id.id))
            mentor = self.env['hr.hospital.doctor'].search(domain, limit=1)
            if mentor:
                self.mentor_id = mentor

    def action_archive(self):
        """Execute the archive action."""
        active_visits = self.env['hr.hospital.visit'].search_count(
            [
                ('doctor_id', 'in', self.ids),
                ('state', '=', 'planned'),
            ],
        )
        if active_visits:
            raise ValidationError(self.env._('Cannot archive doctors with active visits.'))
        return super().action_archive()

    def action_create_visit(self):
        """Execute the create visit action."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('New Visit'),
            'res_model': 'hr.hospital.visit',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                **self.env.context,
                'default_doctor_id': self.id,
                'default_visit_type': 'first',
            },
        }
