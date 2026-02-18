from odoo import models, api


class ReportJournalEntry(models.AbstractModel):
    _name = 'report.l10n_vn_viin.report_account_move_journal_entry'
    _description = 'Journal Entry Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        moves = self.env['account.move'].browse(docids)
        return {
                'doc_ids': docids,
                'doc_model': 'account.move',
                'docs': moves,
                'report_type': data.get('report_type', '') if data else '',
            }
