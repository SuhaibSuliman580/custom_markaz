from odoo import models, api, _
from odoo.exceptions import ValidationError, UserError


class ReportPaymentReceipt(models.AbstractModel):
    _name = 'report.l10n_vn_viin.report_account_move_payment_receipt'
    _inherit = 'report.l10n_vn_viin.report_account_move_journal_entry'
    _description = 'Payment Receipt Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        moves = self.env['account.move'].browse(docids)
        for record in moves:
            if record.state in ('draft', 'cancel'):
                raise ValidationError(_("There are a few Journal Entries not in state Posted. You can post it and try again."))
            if record.journal_id.type not in ('bank', 'cash'):
                raise UserError(_("Only payments could be printed."))
        return super(ReportPaymentReceipt, self)._get_report_values(docids, data)
