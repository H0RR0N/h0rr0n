from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DoctorScheduleWizard(models.TransientModel):
    _name = "hr.hospital.doctor.schedule.wizard"
    _description = "Doctor Schedule Wizard"

    doctor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        string="Doctor",
        required=True,
    )
    week_start = fields.Date(required=True)
    weeks = fields.Integer(default=1, required=True)
    schedule_mode = fields.Selection(
        selection=[
            ("standard", "Standard"),
            ("even", "Even Weeks"),
            ("odd", "Odd Weeks"),
        ],
        default="standard",
    )
    day_mon = fields.Boolean(string="Mon")
    day_tue = fields.Boolean(string="Tue")
    day_wed = fields.Boolean(string="Wed")
    day_thu = fields.Boolean(string="Thu")
    day_fri = fields.Boolean(string="Fri")
    day_sat = fields.Boolean(string="Sat")
    day_sun = fields.Boolean(string="Sun")
    time_start = fields.Float(
        required=True,
        help="Use HH:MM in the range 00:00-23:59.",
    )
    time_end = fields.Float(
        required=True,
        help="Use HH:MM in the range 00:00-23:59.",
    )
    break_from = fields.Float(
        help="Use HH:MM in the range 00:00-23:59.",
    )
    break_to = fields.Float(
        help="Use HH:MM in the range 00:00-23:59.",
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

    @api.onchange("time_start", "time_end", "break_from", "break_to")
    def _onchange_time_values(self):
        for rec in self:
            rec.time_start = rec._normalize_time_value(rec.time_start)
            rec.time_end = rec._normalize_time_value(rec.time_end)
            rec.break_from = rec._normalize_time_value(rec.break_from)
            rec.break_to = rec._normalize_time_value(rec.break_to)

    def _validate_time_fields(self):
        for rec in self:
            rec._validate_time_value(rec.time_start, _("Start time"))
            rec._validate_time_value(rec.time_end, _("End time"))
            if rec.break_from not in (False, None):
                rec._validate_time_value(rec.break_from, _("Break from"))
            if rec.break_to not in (False, None):
                rec._validate_time_value(rec.break_to, _("Break to"))

            if rec.time_end <= rec.time_start:
                raise ValidationError(_("End time must be after start time."))
            if rec.break_from and rec.break_to:
                if not rec.time_start < rec.break_from < rec.break_to < rec.time_end:
                    raise ValidationError(_("Break time must be within working hours."))

    @api.constrains("time_start", "time_end", "break_from", "break_to")
    def _check_time_fields(self):
        self._validate_time_fields()

    def _get_selected_days(self):
        return [
            (0, self.day_mon),
            (1, self.day_tue),
            (2, self.day_wed),
            (3, self.day_thu),
            (4, self.day_fri),
            (5, self.day_sat),
            (6, self.day_sun),
        ]

    def _validate_selected_days(self):
        for rec in self:
            if not any(enabled for _, enabled in rec._get_selected_days()):
                raise ValidationError(_("Select at least one weekday."))

    @api.constrains("weeks")
    def _check_weeks(self):
        for rec in self:
            if rec.weeks < 1:
                raise ValidationError(_("Weeks must be greater than zero."))

    @api.constrains(
        "day_mon",
        "day_tue",
        "day_wed",
        "day_thu",
        "day_fri",
        "day_sat",
        "day_sun",
    )
    def _check_selected_days(self):
        self._validate_selected_days()

    def action_generate(self):
        self.ensure_one()
        self.time_start = self._normalize_time_value(self.time_start)
        self.time_end = self._normalize_time_value(self.time_end)
        self.break_from = self._normalize_time_value(self.break_from)
        self.break_to = self._normalize_time_value(self.break_to)
        self._validate_time_fields()
        self._validate_selected_days()

        schedule_vals = []
        for week in range(self.weeks or 1):
            week_date = self.week_start + timedelta(days=week * 7)
            week_number = week_date.isocalendar()[1]
            if self.schedule_mode == "even" and week_number % 2 != 0:
                continue
            if self.schedule_mode == "odd" and week_number % 2 == 0:
                continue

            for weekday, enabled in self._get_selected_days():
                if not enabled:
                    continue
                target_date = week_date + timedelta(days=weekday)
                weekday_code = str(weekday)
                if self.break_from and self.break_to:
                    schedule_vals.extend(
                        [
                            {
                                "doctor_id": self.doctor_id.id,
                                "weekday": weekday_code,
                                "date": target_date,
                                "time_start": self.time_start,
                                "time_end": self.break_from,
                                "schedule_type": "work",
                            },
                            {
                                "doctor_id": self.doctor_id.id,
                                "weekday": weekday_code,
                                "date": target_date,
                                "time_start": self.break_to,
                                "time_end": self.time_end,
                                "schedule_type": "work",
                            },
                        ]
                    )
                else:
                    schedule_vals.append(
                        {
                            "doctor_id": self.doctor_id.id,
                            "weekday": weekday_code,
                            "date": target_date,
                            "time_start": self.time_start,
                            "time_end": self.time_end,
                            "schedule_type": "work",
                        }
                    )

        if schedule_vals:
            self.env["hr.hospital.doctor.schedule"].create(schedule_vals)
        return {"type": "ir.actions.act_window_close"}
