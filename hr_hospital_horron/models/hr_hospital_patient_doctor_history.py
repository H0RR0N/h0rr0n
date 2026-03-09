from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PatientDoctorHistory(models.Model):
    """Business model for PatientDoctorHistory records."""
    _name = 'hr.hospital.patient.doctor.history'
    _description = 'Patient Doctor History'
    _order = 'assign_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        compute='_compute_name',
        store=True,
        precompute=True,
        default=lambda self: self.env._('New Doctor Assignment'),
    )

    patient_id = fields.Many2one(
        comodel_name='hr.hospital.patient',
        required=True,
        ondelete='cascade',
    )
    doctor_id = fields.Many2one(
        comodel_name='hr.hospital.doctor',
        required=True,
        ondelete='restrict',
    )
    assign_date = fields.Date(required=True, default=fields.Date.today)
    change_date = fields.Date()
    change_reason = fields.Text()
    active = fields.Boolean(default=True)

    def _build_display_name(self):
        """Build display name."""
        self.ensure_one()
        patient_name = self.patient_id.display_name
        doctor_name = self.doctor_id.display_name
        if patient_name and doctor_name:
            return self.env._('%(patient)s -> %(doctor)s', patient=patient_name, doctor=doctor_name)
        if patient_name:
            return self.env._('Assignment for %(patient)s', patient=patient_name)
        if doctor_name:
            return self.env._('Doctor %(doctor)s', doctor=doctor_name)
        return self.env._('New Doctor Assignment')

    @api.depends(
        'patient_id',
        'patient_id.name',
        'doctor_id',
        'doctor_id.name',
        'doctor_id.first_name',
        'doctor_id.last_name',
    )
    def _compute_name(self):
        """Compute name."""
        for rec in self:
            rec.name = rec._build_display_name()

    @api.depends(
        'name',
        'patient_id',
        'patient_id.name',
        'doctor_id',
        'doctor_id.name',
        'doctor_id.first_name',
        'doctor_id.last_name',
    )
    def _compute_display_name(self):
        """Compute display name."""
        for rec in self:
            rec.display_name = rec.name or rec._build_display_name()

    @api.constrains('assign_date', 'change_date')
    def _check_change_date_not_earlier_than_assign_date(self):
        """Validate change date not earlier than assign date."""
        for rec in self:
            if rec.assign_date and rec.change_date and rec.change_date < rec.assign_date:
                raise ValidationError(
                    self.env._('Change date cannot be earlier than assignment date.'),
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Create records with module-specific preprocessing."""
        records = super().create(vals_list)
        for rec in records:
            previous = self.search(
                [
                    ('patient_id', '=', rec.patient_id.id),
                    ('id', '!=', rec.id),
                    ('active', '=', True),
                ],
                order='assign_date desc, id desc',
                limit=1,
            )
            if previous:
                previous.write(
                    {
                        'active': False,
                        'change_date': rec.assign_date or fields.Date.today(),
                    },
                )
        return records
