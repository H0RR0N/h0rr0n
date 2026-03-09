"""Extension of res.partner to enforce unique email addresses."""

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize


class ResPartner(models.Model):
    """Extend res.partner to prevent duplicate email addresses.

    Adds a constraint that ensures no two partners share the same
    normalized email address. Email comparison is case-insensitive
    and whitespace-trimmed.
    """

    _inherit = "res.partner"

    hr_unique_email_normalized = fields.Char(
        index=True,
        readonly=True,
        copy=False,
    )

    _email_normalized_unique = models.Constraint(
        "UNIQUE(hr_unique_email_normalized)",
        "Each partner must have a unique email address.",
    )

    @api.model
    def _normalize_email_value(self, email):
        """Return a normalized email or False for empty and invalid values."""
        return email_normalize(email) or False

    def _raise_duplicate_email(self, email, partner_name):
        """Raise a friendly validation error for a duplicate email."""
        raise ValidationError(
            self.env._(
                "The email address '%(email)s' is already used by "
                "partner '%(partner)s'. Each partner must have a "
                "unique email address.",
                email=email,
                partner=partner_name,
            ),
        )

    def _find_duplicate_partner(self, normalized_email, exclude_partner=None):
        """Return an existing partner with the same normalized email, if any."""
        if not normalized_email:
            return self.env["res.partner"]

        domain = [("hr_unique_email_normalized", "=", normalized_email)]
        if exclude_partner:
            domain.append(("id", "!=", exclude_partner.id))
        return self.env["res.partner"].sudo().search(domain, limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        """Normalize email values and block duplicates before insert."""
        prepared_vals_list = []
        seen_in_batch = {}

        for vals in vals_list:
            vals = dict(vals)
            normalized = self._normalize_email_value(vals.get("email"))
            vals["hr_unique_email_normalized"] = normalized

            if normalized:
                duplicate = self._find_duplicate_partner(normalized)
                if duplicate:
                    self._raise_duplicate_email(vals.get("email"), duplicate.display_name)

                if normalized in seen_in_batch:
                    self._raise_duplicate_email(vals.get("email"), seen_in_batch[normalized])

                seen_in_batch[normalized] = vals.get("name") or self.env._("another partner")

            prepared_vals_list.append(vals)

        return super().create(prepared_vals_list)

    def write(self, vals):
        """Normalize email values and block duplicates before update."""
        if "email" not in vals:
            return super().write(vals)

        vals = dict(vals)
        normalized = self._normalize_email_value(vals.get("email"))

        if normalized and len(self) > 1:
            raise ValidationError(
                self.env._(
                    "The email address '%(email)s' cannot be assigned to multiple partners in one operation.",
                    email=vals.get("email"),
                ),
            )

        for partner in self:
            duplicate = self._find_duplicate_partner(normalized, exclude_partner=partner)
            if duplicate:
                self._raise_duplicate_email(vals.get("email"), duplicate.display_name)

        vals["hr_unique_email_normalized"] = normalized
        return super().write(vals)

    @api.constrains("email")
    def _check_unique_email(self):
        """Validate that the partner's email is unique across all partners.

        Normalizes the email (lowercase, strip whitespace) and checks
        for existing partners with the same normalized email.

        Raises:
            ValidationError: If another partner with the same email exists.
        """
        for partner in self:
            normalized = self._normalize_email_value(partner.email)
            duplicate = self._find_duplicate_partner(normalized, exclude_partner=partner)
            if duplicate:
                self._raise_duplicate_email(partner.email, duplicate.display_name)
