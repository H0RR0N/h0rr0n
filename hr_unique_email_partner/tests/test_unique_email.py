"""Tests for unique partner email constraint."""

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestUniqueEmail(TransactionCase):
    """Test cases for the unique email constraint on res.partner."""

    def test_duplicate_email_blocked(self):
        """Test that creating two partners with the same email raises error."""
        self.env["res.partner"].create({
            "name": "Partner One",
            "email": "unique@example.com",
        })
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create({
                "name": "Partner Two",
                "email": "unique@example.com",
            })

    def test_duplicate_email_case_insensitive(self):
        """Test that email comparison is case-insensitive."""
        self.env["res.partner"].create({
            "name": "Partner One",
            "email": "Test@Example.COM",
        })
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create({
                "name": "Partner Two",
                "email": "test@example.com",
            })

    def test_duplicate_email_trimmed(self):
        """Test that email comparison ignores surrounding whitespace."""
        self.env["res.partner"].create({
            "name": "Partner One",
            "email": "trimmed@example.com",
        })
        with self.assertRaises(ValidationError):
            self.env["res.partner"].create({
                "name": "Partner Two",
                "email": "  trimmed@example.com  ",
            })

    def test_unique_emails_allowed(self):
        """Test that different emails can coexist."""
        p1 = self.env["res.partner"].create({
            "name": "Partner One",
            "email": "first@example.com",
        })
        p2 = self.env["res.partner"].create({
            "name": "Partner Two",
            "email": "second@example.com",
        })
        self.assertTrue(p1.id)
        self.assertTrue(p2.id)

    def test_empty_email_allowed(self):
        """Test that multiple partners without email are allowed."""
        p1 = self.env["res.partner"].create({
            "name": "No Email 1",
        })
        p2 = self.env["res.partner"].create({
            "name": "No Email 2",
        })
        self.assertTrue(p1.id)
        self.assertTrue(p2.id)

    def test_write_duplicate_email_blocked(self):
        """Test that updating a partner to a used email raises error."""
        self.env["res.partner"].create({
            "name": "Partner One",
            "email": "taken@example.com",
        })
        p2 = self.env["res.partner"].create({
            "name": "Partner Two",
            "email": "free@example.com",
        })
        with self.assertRaises(ValidationError):
            p2.write({"email": "taken@example.com"})
