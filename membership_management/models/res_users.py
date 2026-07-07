from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_cash_journal_ids = fields.Many2many(
        'account.journal',
        'membership_cashier_user_journal_rel',
        'user_id',
        'journal_id',
        string='دفاتر اليومية النقدية المسموحة',
        domain="[('type', '=', 'cash')]",
    )
