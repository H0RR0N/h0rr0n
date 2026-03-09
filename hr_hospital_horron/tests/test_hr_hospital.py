"""Tests for HR Hospital module.

Covers:
- HospitalVisit: _check_unique_visit_per_day, _check_doctor_availability,
  _check_actual_datetime_rules, unlink protection
- HospitalPatient: _check_birth_date, _create_doctor_history,
  _compute_name, write doctor history tracking
- DoctorSchedule: _validate_schedule_day_definition, _check_time_range,
  normalize_time_value
- HospitalDoctor: _check_mentor, _compute_experience_years, action_archive
- MedicalDiagnosis: _check_approval, _build_display_name
"""

from datetime import date, datetime, time, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestHospitalVisit(TransactionCase):
    """Test cases for hr.hospital.visit model."""

    @classmethod
    def setUpClass(cls):
        """Set up test data for visit tests."""
        super().setUpClass()
        cls.speciality = cls.env["hr.hospital.doctor.speciality"].create({
            "name": "General",
            "code": "GEN",
        })
        cls.doctor = cls.env["hr.hospital.doctor"].create({
            "name": "Test Doctor",
            "first_name": "Test",
            "last_name": "Doctor",
            "license_number": "TST-001",
            "speciality_id": cls.speciality.id,
        })
        cls.doctor2 = cls.env["hr.hospital.doctor"].create({
            "name": "Test Doctor 2",
            "first_name": "Test",
            "last_name": "Doctor2",
            "license_number": "TST-002",
            "speciality_id": cls.speciality.id,
        })
        cls.patient = cls.env["hr.hospital.patient"].with_context(
            skip_doctor_history=True,
        ).create({
            "first_name": "Test",
            "last_name": "Patient",
            "birth_date": date(1990, 1, 15),
        })

    def _make_visit(self, **kwargs):
        """Helper to create a visit with sensible defaults."""
        # Next Monday at 10:00
        target = datetime.now() + timedelta(days=(7 - datetime.now().weekday()) % 7 or 7)
        planned = datetime.combine(target.date(), time(10, 0))
        vals = {
            "patient_id": self.patient.id,
            "doctor_id": self.doctor.id,
            "visit_date": planned,
            "planned_datetime": planned,
            "state": "planned",
        }
        vals.update(kwargs)
        return self.env["hr.hospital.visit"].create(vals)

    def test_unique_visit_per_day_constraint(self):
        """Test _check_unique_visit_per_day prevents duplicate visits."""
        self._make_visit()
        with self.assertRaises(ValidationError):
            self._make_visit()

    def test_actual_datetime_only_for_done(self):
        """Test _check_actual_datetime_rules: actual_datetime only on done."""
        visit = self._make_visit()
        with self.assertRaises(ValidationError):
            visit.write({
                "actual_datetime": datetime.now() + timedelta(days=14),
            })

    def test_actual_datetime_not_before_planned(self):
        """Test _check_actual_datetime_rules: actual cannot precede planned."""
        visit = self._make_visit()
        with self.assertRaises(ValidationError):
            visit.write({
                "state": "done",
                "actual_datetime": datetime(2020, 1, 1, 8, 0),
            })

    def test_unlink_with_diagnosis_blocked(self):
        """Test unlink() raises error when visit has diagnoses."""
        visit = self._make_visit()
        visit.write({"state": "done"})
        self.env["hr.hospital.medical.diagnosis"].with_context(
            skip_doctor_history=True,
        ).create({
            "visit_id": visit.id,
            "disease_id": self.env["hr.hospital.disease"].create({
                "name": "Test Disease",
                "code": "TST",
                "is_contagious": True,
                "danger_level": "high",
            }).id,
        })
        with self.assertRaises(ValidationError):
            visit.unlink()

    def test_weekend_visit_blocked(self):
        """Test _check_doctor_availability blocks weekend visits."""
        # Find next Saturday
        today = datetime.now()
        days_ahead = (5 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        saturday = today + timedelta(days=days_ahead)
        planned = datetime.combine(saturday.date(), time(10, 0))
        with self.assertRaises(ValidationError):
            self.env["hr.hospital.visit"].create({
                "patient_id": self.patient.id,
                "doctor_id": self.doctor.id,
                "visit_date": planned,
                "planned_datetime": planned,
            })


class TestHospitalPatient(TransactionCase):
    """Test cases for hr.hospital.patient model."""

    @classmethod
    def setUpClass(cls):
        """Set up test data for patient tests."""
        super().setUpClass()
        cls.speciality = cls.env["hr.hospital.doctor.speciality"].create({
            "name": "Surgeon",
            "code": "SUR",
        })
        cls.doctor = cls.env["hr.hospital.doctor"].create({
            "name": "Dr Surgeon",
            "first_name": "Surgeon",
            "last_name": "Dr",
            "license_number": "SUR-001",
            "speciality_id": cls.speciality.id,
        })

    def test_birth_date_future_blocked(self):
        """Test _check_birth_date: future birth date raises error."""
        with self.assertRaises(ValidationError):
            self.env["hr.hospital.patient"].with_context(
                skip_doctor_history=True,
            ).create({
                "first_name": "Future",
                "last_name": "Baby",
                "birth_date": date.today() + timedelta(days=1),
            })

    def test_compute_name(self):
        """Test _compute_name builds full name from parts."""
        patient = self.env["hr.hospital.patient"].with_context(
            skip_doctor_history=True,
        ).create({
            "first_name": "Іван",
            "last_name": "Петренко",
            "middle_name": "Олексійович",
            "birth_date": date(1985, 6, 20),
        })
        self.assertEqual(patient.name, "Петренко Іван Олексійович")

    def test_doctor_history_created_on_assign(self):
        """Test _create_doctor_history on patient creation."""
        patient = self.env["hr.hospital.patient"].create({
            "first_name": "History",
            "last_name": "Test",
            "birth_date": date(1990, 3, 10),
            "personal_doctor_id": self.doctor.id,
        })
        history = self.env["hr.hospital.patient.doctor.history"].search([
            ("patient_id", "=", patient.id),
        ])
        self.assertTrue(history, "Doctor history should be created on patient creation.")

    def test_doctor_history_on_reassign(self):
        """Test write() creates history when personal doctor changes."""
        doctor2 = self.env["hr.hospital.doctor"].create({
            "name": "Dr Other",
            "first_name": "Other",
            "last_name": "Dr",
            "license_number": "OTH-001",
            "speciality_id": self.speciality.id,
        })
        patient = self.env["hr.hospital.patient"].create({
            "first_name": "Reassign",
            "last_name": "Test",
            "birth_date": date(1988, 7, 7),
            "personal_doctor_id": self.doctor.id,
        })
        patient.write({"personal_doctor_id": doctor2.id})
        history_count = self.env["hr.hospital.patient.doctor.history"].search_count([
            ("patient_id", "=", patient.id),
        ])
        self.assertGreaterEqual(history_count, 2)


class TestDoctorSchedule(TransactionCase):
    """Test cases for hr.hospital.doctor.schedule model."""

    @classmethod
    def setUpClass(cls):
        """Set up test data for schedule tests."""
        super().setUpClass()
        cls.speciality = cls.env["hr.hospital.doctor.speciality"].create({
            "name": "Therapist",
            "code": "THE",
        })
        cls.doctor = cls.env["hr.hospital.doctor"].create({
            "name": "Dr Schedule",
            "first_name": "Schedule",
            "last_name": "Dr",
            "license_number": "SCH-001",
            "speciality_id": cls.speciality.id,
        })

    def test_schedule_requires_date_or_weekday(self):
        """Test _validate_schedule_day_definition: no date and no weekday."""
        with self.assertRaises(ValidationError):
            self.env["hr.hospital.doctor.schedule"].create({
                "doctor_id": self.doctor.id,
                "time_start": 9.0,
                "time_end": 17.0,
                "schedule_type": "work",
            })

    def test_time_end_must_exceed_start(self):
        """Test _check_time_range: end <= start raises error."""
        with self.assertRaises(ValidationError):
            self.env["hr.hospital.doctor.schedule"].create({
                "doctor_id": self.doctor.id,
                "weekday": "0",
                "time_start": 17.0,
                "time_end": 9.0,
                "schedule_type": "work",
            })

    def test_time_normalization(self):
        """Test time values are normalized to minute precision."""
        schedule = self.env["hr.hospital.doctor.schedule"].create({
            "doctor_id": self.doctor.id,
            "weekday": "1",
            "time_start": 9.005,
            "time_end": 17.005,
            "schedule_type": "work",
        })
        # normalize_time_value rounds to nearest minute
        self.assertAlmostEqual(schedule.time_start, 9.0, places=2)
        self.assertAlmostEqual(schedule.time_end, 17.0, places=2)

    def test_weekday_date_mismatch(self):
        """Test _validate_schedule_day_definition: weekday doesn't match date."""
        # 2026-03-02 is Monday (weekday 0)
        with self.assertRaises(ValidationError):
            self.env["hr.hospital.doctor.schedule"].create({
                "doctor_id": self.doctor.id,
                "date": date(2026, 3, 2),
                "weekday": "2",  # Wednesday, but date is Monday
                "time_start": 9.0,
                "time_end": 17.0,
                "schedule_type": "work",
            })


class TestHospitalDoctor(TransactionCase):
    """Test cases for hr.hospital.doctor model."""

    @classmethod
    def setUpClass(cls):
        """Set up test data for doctor tests."""
        super().setUpClass()
        cls.speciality = cls.env["hr.hospital.doctor.speciality"].create({
            "name": "Cardiology",
            "code": "CAR",
        })

    def test_mentor_must_be_non_intern(self):
        """Test _check_mentor: mentor cannot be an intern."""
        intern1 = self.env["hr.hospital.doctor"].create({
            "name": "Intern1",
            "first_name": "Intern",
            "last_name": "One",
            "license_number": "INT-001",
            "is_intern": True,
            "speciality_id": self.speciality.id,
        })
        with self.assertRaises(ValidationError):
            self.env["hr.hospital.doctor"].create({
                "name": "Intern2",
                "first_name": "Intern",
                "last_name": "Two",
                "license_number": "INT-002",
                "is_intern": True,
                "mentor_id": intern1.id,
                "speciality_id": self.speciality.id,
            })

    def test_experience_years_computed(self):
        """Test _compute_experience_years from license_date."""
        doc = self.env["hr.hospital.doctor"].create({
            "name": "Experienced",
            "first_name": "Exp",
            "last_name": "Doc",
            "license_number": "EXP-001",
            "license_date": date.today() - timedelta(days=365 * 5 + 1),
            "speciality_id": self.speciality.id,
        })
        self.assertGreaterEqual(doc.experience_years, 5)

    def test_archive_blocked_with_planned_visits(self):
        """Test action_archive raises error with planned visits."""
        doc = self.env["hr.hospital.doctor"].create({
            "name": "Archivable",
            "first_name": "Arch",
            "last_name": "Doc",
            "license_number": "ARC-001",
            "speciality_id": self.speciality.id,
        })
        patient = self.env["hr.hospital.patient"].with_context(
            skip_doctor_history=True,
        ).create({
            "first_name": "Arch",
            "last_name": "Patient",
            "birth_date": date(1990, 5, 5),
        })
        # Next Monday at 10:00
        target = datetime.now() + timedelta(days=(7 - datetime.now().weekday()) % 7 or 7)
        planned = datetime.combine(target.date(), time(10, 0))
        self.env["hr.hospital.visit"].create({
            "patient_id": patient.id,
            "doctor_id": doc.id,
            "visit_date": planned,
            "planned_datetime": planned,
            "state": "planned",
        })
        with self.assertRaises(ValidationError):
            doc.action_archive()

    def test_non_intern_cannot_have_mentor(self):
        """Test _check_mentor: non-intern with mentor raises error."""
        mentor = self.env["hr.hospital.doctor"].create({
            "name": "Mentor",
            "first_name": "Men",
            "last_name": "Tor",
            "license_number": "MEN-001",
            "speciality_id": self.speciality.id,
        })
        with self.assertRaises(ValidationError):
            self.env["hr.hospital.doctor"].create({
                "name": "RegDoc",
                "first_name": "Reg",
                "last_name": "Doc",
                "license_number": "REG-001",
                "is_intern": False,
                "mentor_id": mentor.id,
                "speciality_id": self.speciality.id,
            })


class TestMedicalDiagnosis(TransactionCase):
    """Test cases for hr.hospital.medical.diagnosis model."""

    @classmethod
    def setUpClass(cls):
        """Set up test data for diagnosis tests."""
        super().setUpClass()
        cls.speciality = cls.env["hr.hospital.doctor.speciality"].create({
            "name": "Neurology",
            "code": "NEU",
        })
        cls.user_doctor = cls.env["res.users"].create({
            "name": "DiagDoctor",
            "login": "diagdoc@test.com",
            "email": "diagdoc@test.com",
        })
        cls.doctor = cls.env["hr.hospital.doctor"].create({
            "name": "DiagDoctor",
            "first_name": "Diag",
            "last_name": "Doctor",
            "license_number": "DIG-001",
            "speciality_id": cls.speciality.id,
            "user_id": cls.user_doctor.id,
        })
        cls.patient = cls.env["hr.hospital.patient"].with_context(
            skip_doctor_history=True,
        ).create({
            "first_name": "Diag",
            "last_name": "Patient",
            "birth_date": date(1985, 2, 14),
        })
        cls.disease = cls.env["hr.hospital.disease"].create({
            "name": "Test Neuro Disease",
            "code": "TND",
            "is_contagious": True,
            "danger_level": "high",
        })
        # Create a visit
        target = datetime.now() + timedelta(days=(7 - datetime.now().weekday()) % 7 or 7)
        planned = datetime.combine(target.date(), time(10, 0))
        cls.visit = cls.env["hr.hospital.visit"].create({
            "patient_id": cls.patient.id,
            "doctor_id": cls.doctor.id,
            "visit_date": planned,
            "planned_datetime": planned,
            "state": "done",
        })

    def test_build_display_name(self):
        """Test _build_display_name returns meaningful name."""
        diag = self.env["hr.hospital.medical.diagnosis"].with_user(
            self.user_doctor,
        ).create({
            "visit_id": self.visit.id,
            "disease_id": self.disease.id,
        })
        self.assertIn(self.disease.name, diag.name)

    def test_approval_without_doctor_raises(self):
        """Test _check_approval: approved without approved_by raises."""
        diag = self.env["hr.hospital.medical.diagnosis"].with_user(
            self.user_doctor,
        ).create({
            "visit_id": self.visit.id,
            "disease_id": self.disease.id,
        })
        # Directly write approved=True but clear approved_by to trigger constraint
        with self.assertRaises(ValidationError):
            diag.write({
                "approved": True,
                "approved_by_doctor_id": False,
            })
