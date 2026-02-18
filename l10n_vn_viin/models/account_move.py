from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    in_out_payment = fields.Selection(string='Payment In/Out', selection=[('in', 'In'), ('out', 'Out')], compute='_compute_in_out_payment',
        help="This is technical field, use to specify this move is payment in or payment out.")

    def _compute_in_out_payment(self):
        for r in self:
            r.in_out_payment = False
            if r.journal_id.type in ('bank', 'cash'):
                if r.payment_id:
                    if r.payment_id.payment_type == 'inbound':
                        r.in_out_payment = 'in'
                    elif r.payment_id.payment_type == 'outbound':
                        r.in_out_payment = 'out'
                elif r.statement_line_id:
                    r.in_out_payment = 'out' if r.statement_line_id.amount < 0 else 'in'
