from odoo import api, fields, models, _


class ContactPerson(models.Model):
    _name = "hr.hospital.contact.person"
    _description = "Contact Person"
    _inherit = ["hr.hospital.abstract.person"]

    name = fields.Char(
        compute="_compute_name",
        store=True,
        precompute=True,
        default=lambda self: _("Unnamed Contact Person"),
    )
    patient_ids = fields.One2many(
        comodel_name="hr.hospital.patient",
        inverse_name="contact_person_id",
        string="Patients",
    )

    @api.depends("last_name", "first_name", "middle_name")
    def _compute_name(self):
        for rec in self:
            parts = [rec.last_name, rec.first_name, rec.middle_name]
            parts = [part for part in parts if part]
            fallback_name = rec._origin.name if rec._origin and rec._origin.id else False
            rec.name = " ".join(parts) if parts else (fallback_name or _("Unnamed Contact Person"))

    def name_get(self):
        result = []
        for rec in self:
            parts = [rec.last_name, rec.first_name, rec.middle_name]
            parts = [part for part in parts if part]
            display_name = " ".join(parts) if parts else (
                rec.full_name or rec.name or _("Unnamed Contact Person")
            )
            result.append((rec.id, display_name))
        return result

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            raw_name = (vals.get("name") or "").strip()
            has_name_parts = any(
                vals.get(field_name)
                for field_name in ("last_name", "first_name", "middle_name")
            )
            if raw_name and not has_name_parts:
                parts = [part for part in raw_name.split(" ") if part]
                if parts:
                    vals["last_name"] = parts[0]
                    if len(parts) > 1:
                        vals["first_name"] = " ".join(parts[1:])
            normalized_vals_list.append(vals)
        return super().create(normalized_vals_list)

    @api.onchange("language_id", "citizenship_country_id")
    def _onchange_patient_domain(self):
        domain = [("allergies", "!=", False)]
        if self.language_id:
            domain.append(("language_id", "=", self.language_id.id))
        if self.citizenship_country_id:
            domain.append(("citizenship_country_id", "=", self.citizenship_country_id.id))
        return {"domain": {"patient_ids": domain}}
