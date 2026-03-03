from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HospitalVisit(models.Model):
    _name = "hr.hospital.visit"
    _description = "Patient Visit"
    _order = "visit_date desc"

    name = fields.Char(string="Reference", required=True, default="/")
    visit_date = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
    )
    planned_datetime = fields.Datetime(
        related="visit_date",
        store=True,
        readonly=False,
        string="Planned Date",
    )
    state = fields.Selection(
        selection=[
            ("planned", "Planned"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
            ("no_show", "No Show"),
        ],
        default="planned",
        required=True,
    )
    actual_datetime = fields.Datetime(string="Actual Date")
    patient_id = fields.Many2one(
        comodel_name="hr.hospital.patient",
        required=True,
        ondelete="cascade",
    )
    doctor_id = fields.Many2one(
        comodel_name="hr.hospital.doctor",
        required=True,
        ondelete="restrict",
        domain=[("license_number", "!=", False)],
    )
    visit_type = fields.Selection(
        selection=[
            ("first", "First"),
            ("repeat", "Repeat"),
            ("preventive", "Preventive"),
            ("emergency", "Emergency"),
        ],
    )
    diagnosis_ids = fields.One2many(
        comodel_name="hr.hospital.medical.diagnosis",
        inverse_name="visit_id",
    )
    recommendations = fields.Html()
    fee = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id.id,
    )

    @api.model_create_multi
    def create(self, vals_list):
        normalized = []
        for vals in vals_list:
            vals = dict(vals)
            if not vals.get("visit_date") and vals.get("planned_datetime"):
                vals["visit_date"] = vals["planned_datetime"]
            normalized.append(vals)
        return super().create(normalized)

    def _localize_datetime(self, dt):
        """Return dt in user's timezone (naive local dt)."""
        if not dt:
            return dt
        return fields.Datetime.context_timestamp(self, dt)

    def _local_day_bounds_utc(self, dt):
        """Compute UTC bounds for the user's local day containing dt."""
        if not dt:
            return None, None
        tzname = self.env.context.get("tz") or self.env.user.tz or "UTC"
        tz = pytz.timezone(tzname)
        local_dt = self._localize_datetime(dt)
        local_date = local_dt.date()
        start_local = tz.localize(datetime.combine(local_date, time.min))
        end_local = tz.localize(datetime.combine(local_date, time.max))
        start_utc = start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        end_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)
        return start_utc, end_utc

    def _build_day_exclusion_domain(self, target_date):
        day_start = datetime.combine(target_date, time.min)
        day_end = datetime.combine(target_date, time.max)
        return [
            "!",
            "&",
            ("planned_datetime", ">=", day_start),
            ("planned_datetime", "<=", day_end),
        ]

    def _get_blocked_schedule_dates(self, start_date, end_date):
        blocked_types = ["vacation", "sick", "conference"]
        schedule_model = self.env["hr.hospital.doctor.schedule"]
        blocked_dates = set()

        specific_blocks = schedule_model.search(
            [
                ("doctor_id", "=", self.doctor_id.id),
                ("schedule_type", "in", blocked_types),
                ("date", ">=", start_date),
                ("date", "<=", end_date),
            ]
        )
        blocked_dates.update(d for d in specific_blocks.mapped("date") if d)

        weekday_blocks = schedule_model.search(
            [
                ("doctor_id", "=", self.doctor_id.id),
                ("schedule_type", "in", blocked_types),
                ("date", "=", False),
                ("weekday", "!=", False),
            ]
        )
        blocked_weekdays = {int(code) for code in weekday_blocks.mapped("weekday")}

        if blocked_weekdays:
            cursor = start_date
            while cursor <= end_date:
                if cursor.weekday() in blocked_weekdays:
                    blocked_dates.add(cursor)
                cursor += timedelta(days=1)

        return blocked_dates

    def _get_available_doctor_domain(self):
        domain = [("license_number", "!=", False)]
        if self.patient_id and self.patient_id.personal_doctor_id.speciality_id:
            domain.append(
                ("speciality_id", "=", self.patient_id.personal_doctor_id.speciality_id.id)
            )
        if self.planned_datetime:
            local_dt = self._localize_datetime(self.planned_datetime)
            target_date = local_dt.date()
            weekday = str(target_date.weekday())
            time_float = local_dt.hour + local_dt.minute / 60.0
            schedules = self.env["hr.hospital.doctor.schedule"].search(
                [
                    ("schedule_type", "=", "work"),
                    ("time_start", "<=", time_float),
                    ("time_end", ">=", time_float),
                    "|",
                    ("date", "=", target_date),
                    "&",
                    ("date", "=", False),
                    ("weekday", "=", weekday),
                ]
            )
            doctor_ids = schedules.mapped("doctor_id").ids
            if doctor_ids:
                domain.append(("id", "in", doctor_ids))
            else:
                domain.append(("id", "=", 0))
        return domain

    def _get_available_dates_domain(self):
        domain = [("planned_datetime", ">=", fields.Datetime.now())]
        if not self.doctor_id:
            return domain

        start_date = fields.Date.to_date(fields.Date.context_today(self))
        end_date = start_date + timedelta(days=90)

        blocked_dates = self._get_blocked_schedule_dates(start_date, end_date)

        cursor = start_date
        while cursor <= end_date:
            if cursor.weekday() >= 5:
                blocked_dates.add(cursor)
            cursor += timedelta(days=1)

        for blocked_date in sorted(blocked_dates):
            domain += self._build_day_exclusion_domain(blocked_date)
        return domain

    @api.onchange("patient_id", "planned_datetime")
    def _onchange_patient_or_datetime(self):
        if self.patient_id and self.patient_id.allergies:
            return {
                "warning": {
                    "title": self.env._("Allergies"),
                    "message": self.patient_id.allergies,
                },
                "domain": {"doctor_id": self._get_available_doctor_domain()},
            }
        return {"domain": {"doctor_id": self._get_available_doctor_domain()}}

    @api.onchange("doctor_id")
    def _onchange_doctor(self):
        if not self.doctor_id or not self.planned_datetime:
            return {"domain": {"planned_datetime": self._get_available_dates_domain()}}

        local_dt = self._localize_datetime(self.planned_datetime)
        target_date = local_dt.date()
        weekday = str(target_date.weekday())
        time_float = local_dt.hour + local_dt.minute / 60.0
        block = self.env["hr.hospital.doctor.schedule"].search_count(
            [
                ("doctor_id", "=", self.doctor_id.id),
                ("schedule_type", "in", ["vacation", "sick", "conference"]),
                ("time_start", "<=", time_float),
                ("time_end", ">=", time_float),
                "|",
                ("date", "=", target_date),
                "&",
                ("date", "=", False),
                ("weekday", "=", weekday),
            ]
        )
        if block or weekday in ("5", "6"):
            return {
                "warning": {
                    "title": self.env._("Unavailable Date"),
                    "message": self.env._("Selected date/time is not available for this doctor."),
                }
            }
        return {"domain": {"planned_datetime": self._get_available_dates_domain()}}

    @api.constrains("patient_id", "doctor_id", "planned_datetime", "state")
    def _check_unique_visit_per_day(self):
        for rec in self:
            if not rec.patient_id or not rec.doctor_id or not rec.planned_datetime:
                continue
            start, end = rec._local_day_bounds_utc(rec.planned_datetime)
            if not start or not end:
                continue
            duplicate = self.search_count(
                [
                    ("id", "!=", rec.id),
                    ("patient_id", "=", rec.patient_id.id),
                    ("doctor_id", "=", rec.doctor_id.id),
                    ("state", "!=", "cancelled"),
                    ("planned_datetime", ">=", start),
                    ("planned_datetime", "<=", end),
                ]
            )
            if duplicate:
                raise ValidationError(
                    self.env._("Patient cannot be scheduled with the same doctor more than once per day.")
                )

    @api.constrains("planned_datetime", "doctor_id")
    def _check_doctor_availability(self):
        for rec in self:
            if not rec.planned_datetime or not rec.doctor_id:
                continue
            local_dt = rec._localize_datetime(rec.planned_datetime)
            weekday = local_dt.weekday()
            if weekday >= 5:
                raise ValidationError(self.env._("Visits cannot be scheduled on weekends."))

            time_float = local_dt.hour + local_dt.minute / 60.0
            target_date = local_dt.date()
            blocked = self.env["hr.hospital.doctor.schedule"].search_count(
                [
                    ("doctor_id", "=", rec.doctor_id.id),
                    ("schedule_type", "in", ["vacation", "sick", "conference"]),
                    ("time_start", "<=", time_float),
                    ("time_end", ">=", time_float),
                    "|",
                    ("date", "=", target_date),
                    "&",
                    ("date", "=", False),
                    ("weekday", "=", str(weekday)),
                ]
            )
            if blocked:
                raise ValidationError(
                    self.env._("Selected date/time is not available for this doctor.")
                )

    @api.constrains("state", "planned_datetime", "actual_datetime")
    def _check_actual_datetime_rules(self):
        for rec in self:
            if rec.actual_datetime and rec.state != "done":
                raise ValidationError(
                    self.env._("Actual visit datetime can be set only for completed visits.")
                )
            if (
                rec.actual_datetime
                and rec.planned_datetime
                and rec.actual_datetime < rec.planned_datetime
            ):
                raise ValidationError(
                    self.env._("Actual visit datetime cannot be earlier than planned datetime.")
                )

    @api.constrains("doctor_id", "planned_datetime", "visit_date", "actual_datetime", "state")
    def _check_past_visit_protected_field_changes(self):
        old_values = self.env.context.get("visit_old_values") or {}
        if not old_values:
            return

        now = fields.Datetime.now()
        for rec in self:
            previous = old_values.get(rec.id)
            if not previous:
                continue

            doctor_changed = rec.doctor_id.id != previous["doctor_id"]
            planned_changed = rec.planned_datetime != previous["planned_datetime"]
            visit_date_changed = rec.visit_date != previous["visit_date"]
            actual_datetime_changed = rec.actual_datetime != previous["actual_datetime"]

            if previous["state"] == "done" and (
                doctor_changed
                or planned_changed
                or visit_date_changed
                or actual_datetime_changed
            ):
                raise ValidationError(
                    self.env._("Cannot change doctor or date/time for completed visits.")
                )

            previous_planned_dt = previous["planned_datetime"] or previous["visit_date"]
            if previous_planned_dt and previous_planned_dt < now and previous["state"] != "cancelled":
                if doctor_changed or planned_changed or visit_date_changed:
                    raise ValidationError(
                        self.env._("Cannot change doctor or planned date/time for visits that already occurred.")
                    )

    def write(self, vals):
        vals = dict(vals)
        tracked_fields = {"doctor_id", "planned_datetime", "visit_date", "actual_datetime"}
        if not tracked_fields.intersection(vals):
            return super().write(vals)

        old_values = {}
        for rec in self:
            old_values[rec.id] = {
                "state": rec.state,
                "doctor_id": rec.doctor_id.id,
                "planned_datetime": rec.planned_datetime,
                "visit_date": rec.visit_date,
                "actual_datetime": rec.actual_datetime,
            }
        return super(HospitalVisit, self.with_context(visit_old_values=old_values)).write(vals)

    def unlink(self):
        for rec in self:
            if rec.diagnosis_ids:
                raise ValidationError(
                    self.env._("Cannot delete visits that have diagnoses attached.")
                )
        return super().unlink()
