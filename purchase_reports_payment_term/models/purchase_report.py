from odoo import fields, models
from odoo.tools.sql import SQL


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Payment Terms",
        readonly=True,
    )

    def _select(self):
        return SQL("%s, po.payment_term_id as payment_term_id", super()._select())

    def _group_by(self):
        return SQL("%s, po.payment_term_id", super()._group_by())
