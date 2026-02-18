from odoo import models, Command
from odoo.addons.account.models.chart_template import template


# pylint: disable=consider-merging-classes-inherited
class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template(template='vn', model='template_data')
    def _get_vn_viin_template_data(self):
        return {
            'name': "VN - Chart of Accounts - Circular No. 200/2014/TT-BTC",
            'property_account_expense_categ_id': 'chart151',
            'property_stock_account_input_categ_id': 'chart151',
            'property_stock_account_output_categ_id': 'chart632',
            'property_stock_valuation_account_id': 'chart1561',
            # New fields added via viin_account
            'property_account_income_refund_categ_id': 'chart5212',
            'property_account_expense_refund_categ_id': None,
            'property_account_other_receivable_id': 'chart1388',
            'property_account_other_payable_id': 'chart3388',
        }

    @template(template='vn', model='res.company')
    def _get_vn_viin_res_company(self):
        return {
            self.env.company.id: {
                'circular_code': 'c200',
                'account_journal_early_pay_discount_loss_account_id': 'chart635',
                'account_journal_early_pay_discount_gain_account_id': 'chart515',
                'default_cash_difference_income_account_id': 'chart711',
                'default_cash_difference_expense_account_id': 'chart811',
                'account_default_pos_receivable_account_id': 'chart1388',
                # New fields added via viin_account
                'vat_ctp_account_id': 'chart1331',
                'general_employee_payable_account_id': 'chart3341',
                'advance_account_id': 'chart141',
                'currency_conversion_diff_income_account_id': 'chart711',
                'currency_conversion_diff_expense_account_id': 'chart811',
                'import_vat_ctp_account_id': 'chart1331',
                'export_vat_ctp_account_id': 'chart1331',
                'borrowing_account_id': 'chart3411',
                'lending_account_id': 'chart1283',
                'deferred_revenue_account_id': 'chart3387',
                'prepaid_expense_account_id': 'chart242',
                'export_tax_ids': [Command.set([
                    'tax_export_0',
                    'tax_sale_vat_exemption',
                ])],
                'import_tax_ids': [Command.set([
                    'tax_import_10',
                    'tax_purchase_import_10',
                ])],
            }
        }
