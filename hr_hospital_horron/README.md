# HR Hospital — Odoo module (Module 2 → Module 3)

This module is a continuation of the training project **hr_hospital**.

- **Module 2 (baseline):** core clinic entities and a minimal workflow (patients, doctors, diseases, visits).
- **Module 3 (advanced):** extended functionality using Module 3 topics (inheritance + abstract models, domains/recordsets, constraints, wizards, demo data).

Target version: **Odoo 19**.

---

## What existed in Module 2 (baseline)
The baseline module contained the main entities and the minimal clinic workflow:

- **Patients** (`hr.hospital.patient`): name, birth date, phone/email, observing doctor, visit history, notes.
- **Doctors** (`hr.hospital.doctor`): name, specialization, phone/email, mentor/intern relationship, list of patients.
- **Diseases** (`hr.hospital.disease`): simple disease directory.
- **Visits** (`hr.hospital.visit`): visit reference, visit datetime, patient, doctor, disease, notes.

This Module 3 version builds on top of that baseline.

---

## What was added in Module 3 (advanced)
### 1) Abstract Person model
A shared abstract model (inherits `image.mixin`) used by:
- Patient
- Doctor
- Contact Person

It provides: split name fields, phone/email validation, gender, birth date, computed age, citizenship country, communication language, computed full name.

### 2) Patient improvements
- personal doctor, passport number
- contact person
- blood group, allergies
- insurance company/policy
- **personal doctor history** (created automatically on assignment/change)

### 3) Doctor improvements
- system user (`res.users`), speciality
- intern flag + mentor doctor
- license number (unique), license date, computed experience
- rating 0.00–5.00
- schedule (One2many)
- archive protection (cannot archive doctors with active visits)
- `name_get`: displayed as `Name (Speciality)`

### 4) Visits
- status (planned/done/cancelled/no show)
- planned vs actual datetime
- visit type
- diagnoses (One2many)
- recommendations (HTML)
- monetary fee + currency
- constraints:
  - a patient cannot be scheduled with the same doctor more than once per day
  - visits with diagnoses cannot be deleted
  - doctor/date/time cannot be changed for visits that already happened

### 5) New models
- **Medical diagnosis** (approval fields, severity)
- **Doctor speciality**
- **Doctor schedule** (+ constraint `time_end > time_start`)
- **Patient doctor history** (previous active record is automatically deactivated)

### 6) Disease hierarchy
Diseases are hierarchical (parent/children) + ICD‑10 code, danger level, contagious flag, symptoms, and regions.

### 7) Wizards (TransientModel)
- mass doctor reassignment
- disease report for a period (detailed/summary)
- reschedule a visit
- generate doctor schedules
- export patient medical card (JSON/CSV)

---

## Demo data (scenario-based, not random)
Demo data is prepared to look realistic and to help demonstrate domains/constraints/wizards quickly:

- **5** doctor specialities
- **8** doctors (including **2 interns** with mentors)
- **15** patients + contact persons
- **12** diseases with a 2–3 level hierarchy and regions
- **25** visits with different statuses
- **20** diagnoses (including unapproved intern diagnoses)
- schedules for the current week + history of personal doctor assignments

---

## Note
The original assignment mentioned a rule about "research dates". The baseline hr_hospital (Module 2) does not include a research model, so the rule is not applicable here.
