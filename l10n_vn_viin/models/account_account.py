from odoo import models, api, _
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    @api.model_create_multi
    def create(self, vals_list):
        records = super(AccountAccount, self).create(vals_list)
        vn_charts = self.env['account.chart.template']._get_installed_vietnam_coa_templates()
        accounts = records.filtered(lambda r: r.company_id.chart_template in vn_charts)
        accounts._fill_account_tag_for_vn_coa()
        return records

    def _fill_account_tag_for_vn_coa(self):
        """
        Fill account tag for the account if not specified.
        """
        vn_charts = self.env['account.chart.template']._get_installed_vietnam_coa_templates()
        all_account_tags = self.env['account.account.tag'].search([('code', '!=', False)])
        for r in self:
            if r.company_id.chart_template not in vn_charts:
                raise ValidationError(_("Fill account tags only for accounts in the company that use the Vietnam COA."))
            if not r.tag_ids:
                account_tags = all_account_tags.filtered(lambda a: a.code.startswith(r.code[:3]) and a.code in r.code)
                if account_tags:
                    r.write({
                        'tag_ids': [(6, 0, account_tags.ids)]
                    })
