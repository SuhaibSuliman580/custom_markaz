from odoo import fields, models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    no_of_origin = fields.Char(string='No. of Origin', size=256,
                                  help="Number of the origin documents (e.g. Purchase Voucher number, Invoice Number, etc), to be displayed on the PDF printed version of this document.")
    recipient_payer = fields.Char(string='Recipient / Payer', size=256, compute='_compute_recipient_payer', readonly=False, store=True,
                                  help='The name of the person who pay/receive the payment. If empty, the corresponding partner name will be used instead.')

    @api.depends('partner_id')
    def _compute_recipient_payer(self):
        for r in self:
            if r.partner_id and r.partner_id.company_type == 'person':
                r.recipient_payer = r.partner_id.name
            else:
                r.recipient_payer = False

    def _get_reconciled_statement_move(self):
        return self.move_id._get_reconciled_statement_move()
