from odoo import models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        # OVERRIDE
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)

        if company.account_fiscal_country_id.code == 'VN':
            # Ensure the newly liquidity accounts have the right account tag in order to be part
            # of the Vietnam financial reports.
            account_vals.setdefault('tag_ids', [])
            if code.startswith('111'):
                account_vals['tag_ids'].append((4, self.env.ref('l10n_vn_viin.account_account_tag_111').id))
            else:
                account_vals['tag_ids'].append((4, self.env.ref('l10n_vn_viin.account_account_tag_112').id))

        return account_vals
