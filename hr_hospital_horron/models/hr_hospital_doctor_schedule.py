from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DoctorSchedule(models.Model):
    _name = "hr.hospital.doctor.schedule"
    _description = "Doctor Schedule"
    _order = "doctor_id, date, weekday, time_start"
    _rec_name = "name"

    name = fields.Char(
        compute="_compute_name",
        store=True,
        precompute=True,
        default=lambda self: _("New Schedule"),
    )

    doctor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        required=True,
        domain=[("speciality_id", "!=", False)],
        ondelete="cascade",
    )
    weekday = fields.Selection(
        selection=[
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
    )
    date = fields.Date(string="Specific Date")
    time_start = fields.Float(
        string="Start Time",
        required=True,
        help="Use HH:MM in the range 00:00-23:59.",
    )
    time_end = fields.Float(
        string="End Time",
        required=True,
        help="Use HH:MM in the range 00:00-23:59.",
    )
    schedule_type = fields.Selection(
        selection=[
            ("work", "Work"),
            ("vacation", "Vacation"),
            ("sick", "Sick"),
            ("conference", "Conference"),
        ],
        default="work",
        required=True,
    )
    note = fields.Char(translate=True)

    def _selection_label(self, field_name, value):
        if value in (False, None):
            return ""
        selection = dict(self._fields[field_name]._description_selection(self.env))
        return selection.get(value, "")

    @staticmethod
    def _float_to_hhmm(value):
        if value in (False, None):
            return ""
        total_minutes = int(round(value * 60))
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours:02d}:{minutes:02d}"

    def _build_display_name(self):
        self.ensure_one()
        doctor_name = self.doctor_id.display_name
        if self.date:
            day_label = fields.Date.to_string(self.date)
        else:
            weekday_label = self._selection_label("weekday", self.weekday)
            day_label = weekday_label or _("No date")

        start_time = self._float_to_hhmm(self.time_start)
        end_time = self._float_to_hhmm(self.time_end)
        if start_time and end_time:
            time_label = f"{start_time}-{end_time}"
        elif start_time:
            time_label = start_time
        elif end_time:
            time_label = end_time
        else:
            time_label = _("No time")

        type_label = self._selection_label("schedule_type", self.schedule_type)
        type_label = type_label or _("Schedule")

        if doctor_name:
            return _(
                "%(doctor)s - %(day)s %(time)s (%(type)s)",
                doctor=doctor_name,
                day=day_label,
                time=time_label,
                type=type_label,
            )
        return _("%(day)s %(time)s (%(type)s)", day=day_label, time=time_label, type=type_label)

    @api.depends(
        "doctor_id",
        "doctor_id.name",
        "doctor_id.first_name",
        "doctor_id.last_name",
        "doctor_id.speciality_id",
        "doctor_id.speciality_id.name",
        "date",
        "weekday",
        "time_start",
        "time_end",
        "schedule_type",
    )
    def _compute_name(self):
        for rec in self:
            rec.name = rec._build_display_name()

    @api.depends(
        "name",
        "doctor_id",
        "doctor_id.name",
        "doctor_id.first_name",
        "doctor_id.last_name",
        "doctor_id.speciality_id",
        "doctor_id.speciality_id.name",
        "date",
        "weekday",
        "time_start",
        "time_end",
        "schedule_type",
    )
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.name or rec._build_display_name()

    def name_get(self):
        return [(rec.id, rec.display_name or rec._build_display_name()) for rec in self]

    _time_end_gt_time_start = models.Constraint(
        "CHECK(time_end > time_start)",
        "End time must be later than start time.",
    )
    _time_in_day_bounds = models.Constraint(
        "CHECK(time_start >= 0 AND time_start < 24 AND time_end >= 0 AND time_end < 24)",
        "Time must be between 00:00 and 23:59.",
    )

    @staticmethod
    def _normalize_time_value(value):
        if value in (False, None):
            return value
        max_minutes = 23 * 60 + 59
        minutes = int(round(value * 60))
        minutes = max(0, min(max_minutes, minutes))
        return minutes / 60.0

    @staticmethod
    def _validate_time_value(value, field_label):
        max_time = 23 + (59 / 60)
        if value < 0 or value > max_time:
            raise ValidationError(
                _("%(field)s must be between 00:00 and 23:59.", field=field_label)
            )
        if abs(value * 60 - round(value * 60)) > 1e-6:
            raise ValidationError(
                _("%(field)s must use minute precision (HH:MM).", field=field_label)
            )

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            for field_name in ("time_start", "time_end"):
                if field_name in vals and vals[field_name] not in (False, None):
                    vals[field_name] = self._normalize_time_value(vals[field_name])
            normalized_vals_list.append(vals)
        records = super().create(normalized_vals_list)
        records._validate_schedule_day_definition()
        return records

    def write(self, vals):
        vals = dict(vals)
        for field_name in ("time_start", "time_end"):
            if field_name in vals and vals[field_name] not in (False, None):
                vals[field_name] = self._normalize_time_value(vals[field_name])
        result = super().write(vals)
        self._validate_schedule_day_definition()
        return result

    @api.onchange("time_start", "time_end")
    def _onchange_time_range(self):
        for rec in self:
            rec.time_start = rec._normalize_time_value(rec.time_start)
            rec.time_end = rec._normalize_time_value(rec.time_end)

    @api.constrains("time_start", "time_end")
    def _check_time_range(self):
        for rec in self:
            rec._validate_time_value(rec.time_start, _("Start time"))
            rec._validate_time_value(rec.time_end, _("End time"))
            if rec.time_end <= rec.time_start:
                raise ValidationError(_("End time must be later than start time."))

    @api.constrains("date", "weekday")
    def _check_schedule_day_definition(self):
        self._validate_schedule_day_definition()

    def _validate_schedule_day_definition(self):
        for rec in self:
            if not rec.date and not rec.weekday:
                raise ValidationError(
                    _("Set either a specific date or a weekday for the schedule line.")
                )
            if rec.date and rec.weekday:
                date_weekday = str(rec.date.weekday())
                if rec.weekday != date_weekday:
                    raise ValidationError(
                        _("Weekday must match the selected specific date.")
                    )
