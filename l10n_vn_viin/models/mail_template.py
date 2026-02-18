from odoo import models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def generate_email(self, res_ids, fields):
        self.ensure_one()
        if self.model == 'account.payment' and self.report_template == self.env.ref('account.action_report_payment_receipt'):
            account_payment = self.env['account.payment'].browse(res_ids)
            if account_payment.company_id.chart_template in self.env['account.chart.template']._get_installed_vietnam_coa_templates():
                return super(MailTemplate, self.new({'report_template': self.env.ref('l10n_vn_viin.act_report_account_payment').id}, origin=self)).generate_email(res_ids, fields)
        return super(MailTemplate, self).generate_email(res_ids, fields)
