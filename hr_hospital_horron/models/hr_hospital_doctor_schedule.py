from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..utils import normalize_time_value, validate_time_value


class DoctorSchedule(models.Model):
    _name = "hr.hospital.doctor.schedule"
    _description = "Doctor Schedule"
    _order = "doctor_id, date, weekday, time_start"
    _rec_name = "name"

    name = fields.Char(
        compute="_compute_display_name",
        store=True,
        precompute=True,
        default=lambda self: self.env._("New Schedule"),
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
    def _compute_display_name(self):
        for rec in self:
            doctor_name = rec.doctor_id.display_name
            if rec.date:
                day_label = fields.Date.to_string(rec.date)
            else:
                weekday_label = rec._selection_label("weekday", rec.weekday)
                day_label = weekday_label or self.env._("No date")

            start_time = rec._float_to_hhmm(rec.time_start)
            end_time = rec._float_to_hhmm(rec.time_end)
            if start_time and end_time:
                time_label = f"{start_time}-{end_time}"
            elif start_time:
                time_label = start_time
            elif end_time:
                time_label = end_time
            else:
                time_label = self.env._("No time")

            type_label = rec._selection_label("schedule_type", rec.schedule_type) or self.env._("Schedule")
            if doctor_name:
                display = self.env._(
                    "%(doctor)s - %(day)s %(time)s (%(type)s)",
                    doctor=doctor_name,
                    day=day_label,
                    time=time_label,
                    type=type_label,
                )
            else:
                display = self.env._(
                    "%(day)s %(time)s (%(type)s)",
                    day=day_label,
                    time=time_label,
                    type=type_label,
                )
            rec.name = display
            rec.display_name = display

    _time_end_gt_time_start = models.Constraint(
        "CHECK(time_end > time_start)",
        "End time must be later than start time.",
    )
    _time_in_day_bounds = models.Constraint(
        "CHECK(time_start >= 0 AND time_start < 24 AND time_end >= 0 AND time_end < 24)",
        "Time must be between 00:00 and 23:59.",
    )

    @api.constrains("time_start", "time_end")
    def _check_time_range(self):
        for rec in self:
            validate_time_value(self.env, rec.time_start, self.env._("Start time"))
            validate_time_value(self.env, rec.time_end, self.env._("End time"))
            if rec.time_end <= rec.time_start:
                raise ValidationError(self.env._("End time must be later than start time."))

    @api.constrains("date", "weekday")
    def _check_schedule_day_definition(self):
        self._validate_schedule_day_definition()

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            for field_name in ("time_start", "time_end"):
                if field_name in vals and vals[field_name] not in (False, None):
                    vals[field_name] = normalize_time_value(vals[field_name])
            normalized_vals_list.append(vals)
        records = super().create(normalized_vals_list)
        records._validate_schedule_day_definition()
        return records

    def write(self, vals):
        vals = dict(vals)
        for field_name in ("time_start", "time_end"):
            if field_name in vals and vals[field_name] not in (False, None):
                vals[field_name] = normalize_time_value(vals[field_name])
        result = super().write(vals)
        self._validate_schedule_day_definition()
        return result

    @api.onchange("time_start", "time_end")
    def _onchange_time_range(self):
        for rec in self:
            rec.time_start = normalize_time_value(rec.time_start)
            rec.time_end = normalize_time_value(rec.time_end)

    def _validate_schedule_day_definition(self):
        for rec in self:
            if not rec.date and not rec.weekday:
                raise ValidationError(
                    self.env._("Set either a specific date or a weekday for the schedule line.")
                )
            if rec.date and rec.weekday:
                date_weekday = str(rec.date.weekday())
                if rec.weekday != date_weekday:
                    raise ValidationError(
                        self.env._("Weekday must match the selected specific date.")
                    )
