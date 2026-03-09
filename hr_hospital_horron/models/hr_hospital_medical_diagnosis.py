from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MedicalDiagnosis(models.Model):
    """Business model for MedicalDiagnosis records."""
    _name = 'hr.hospital.medical.diagnosis'
    _description = 'Medical Diagnosis'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(
        compute='_compute_name',
        store=True,
        precompute=True,
        default=lambda self: self.env._('New Diagnosis'),
    )

    visit_id = fields.Many2one(
        comodel_name='hr.hospital.visit',
        ondelete='cascade',
        required=True,
        domain=lambda self: self._domain_visit_id(),
    )
    patient_id = fields.Many2one(
        comodel_name='hr.hospital.patient',
        related='visit_id.patient_id',
        store=True,
        readonly=True,
    )
    doctor_id = fields.Many2one(
        comodel_name='hr.hospital.doctor',
        related='visit_id.doctor_id',
        store=True,
        readonly=True,
    )
    diagnosis_datetime = fields.Datetime(
        related='visit_id.planned_datetime',
        store=True,
        readonly=True,
    )
    diagnosis_date = fields.Date(
        compute='_compute_diagnosis_date',
        store=True,
        readonly=True,
    )
    disease_id = fields.Many2one(
        comodel_name='hr.hospital.disease',
        domain=[('is_contagious', '=', True), ('danger_level', 'in', ['high', 'critical'])],
    )
    disease_type_id = fields.Many2one(
        comodel_name='hr.hospital.disease',
        related='disease_id.parent_id',
        store=True,
        readonly=True,
    )
    description = fields.Text()
    treatment_html = fields.Html(string='Treatment')
    approved = fields.Boolean(default=False)
    approved_by_doctor_id = fields.Many2one(
        comodel_name='hr.hospital.doctor',
        string='Approved By',
        readonly=True,
    )
    approved_date = fields.Datetime(readonly=True)
    severity = fields.Selection(
        selection=[
            ('light', 'Light'),
            ('medium', 'Medium'),
            ('severe', 'Severe'),
            ('critical', 'Critical'),
        ],
    )

    def _build_display_name(self):
        """Build display name."""
        self.ensure_one()
        disease_name = self.disease_id.display_name
        visit_name = self.visit_id.name
        if disease_name and visit_name:
            return self.env._(
                '%(disease)s (%(visit)s)',
                disease=disease_name,
                visit=visit_name,
            )
        if disease_name:
            return disease_name
        if visit_name:
            return self.env._('Diagnosis for %(visit)s', visit=visit_name)
        return self.env._('New Diagnosis')

    @api.depends('disease_id', 'disease_id.name', 'visit_id', 'visit_id.name')
    def _compute_name(self):
        """Compute name."""
        for rec in self:
            rec.name = rec._build_display_name()

    @api.depends('diagnosis_datetime')
    def _compute_diagnosis_date(self):
        """Compute diagnosis date."""
        for rec in self:
            rec.diagnosis_date = fields.Date.to_date(rec.diagnosis_datetime) if rec.diagnosis_datetime else False

    @api.depends('name', 'disease_id', 'disease_id.name', 'visit_id', 'visit_id.name')
    def _compute_display_name(self):
        """Compute display name."""
        for rec in self:
            rec.display_name = rec.name or rec._build_display_name()

    def _domain_visit_id(self):
        """Only finished visits within the last 30 days."""
        dt_from = fields.Datetime.subtract(fields.Datetime.now(), days=30)
        return [
            ('state', '=', 'done'),
            ('planned_datetime', '>=', dt_from),
        ]

    def _get_current_user_doctor(self):
        """Return current user doctor."""
        doctor = self.env['hr.hospital.doctor'].search(
            [('user_id', '=', self.env.user.id)], limit=1,
        )
        if not doctor:
            raise ValidationError(self.env._('Current user is not linked to a doctor.'))
        return doctor

    def _approval_values_for_current_user(self):
        """Handle approval values for current user."""
        doctor = self._get_current_user_doctor()
        return {
            'approved_by_doctor_id': doctor.id,
            'approved_date': fields.Datetime.now(),
        }

    def write(self, vals):
        """Update records with module-specific business rules."""
        if vals.get('approved') and not vals.get('approved_by_doctor_id'):
            vals = dict(vals)
            vals.update(self._approval_values_for_current_user())
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Create records with module-specific preprocessing."""
        normalized = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get('approved') and not vals.get('approved_by_doctor_id'):
                vals.update(self._approval_values_for_current_user())
            normalized.append(vals)
        return super().create(normalized)

    @api.constrains('approved', 'approved_by_doctor_id', 'visit_id')
    def _check_approval(self):
        """Validate approval."""
        for rec in self:
            if rec.approved and not rec.approved_by_doctor_id:
                raise ValidationError(self.env._('Approved diagnosis must have an approving doctor.'))
            if not rec.approved or not rec.visit_id.doctor_id:
                continue
            if not rec.visit_id.doctor_id.is_intern:
                continue

            mentor = rec.visit_id.doctor_id.mentor_id
            if not mentor:
                raise ValidationError(
                    self.env._('Intern doctor must have a mentor before diagnosis approval.'),
                )
            if rec.approved_by_doctor_id != mentor:
                raise ValidationError(
                    self.env._('Diagnosis for an intern visit can only be approved by the mentor doctor.'),
                )

    def action_approve(self):
        """Execute the approve action."""
        for rec in self:
            if rec.approved:
                continue
            rec.write(
                {
                    'approved': True,
                    **rec._approval_values_for_current_user(),
                },
            )
