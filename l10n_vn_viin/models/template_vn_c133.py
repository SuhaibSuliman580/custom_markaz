from odoo import models, Command
from odoo.addons.account.models.chart_template import template


# pylint: disable=consider-merging-classes-inherited
class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template(template='vn_c133', model='template_data')
    def _get_vn_c133_template_data(self):
        return {
            'name': "VN - Chart of Accounts - Circular No. 133/2016/TT-BTC",
            'code_digits': '0',
            'property_account_receivable_id': 'c133_chart131',
            'property_account_payable_id': 'c133_chart331',
            'property_account_income_categ_id': 'c133_chart5111',
            'property_account_expense_categ_id': 'c133_chart151',
            'property_stock_account_input_categ_id': 'c133_chart151',
            'property_stock_account_output_categ_id': 'c133_chart632',
            'property_stock_valuation_account_id': 'c133_chart156',
            'property_account_income_refund_categ_id': 'c133_chart5111',
            'property_account_other_receivable_id': 'c133_chart1388',
            'property_account_other_payable_id': 'c133_chart3388',
        }

    @template(template='vn_c133', model='res.company')
    def _get_vn_c133_res_company(self):
        return {
            self.env.company.id: {
                'circular_code': 'c133',
                'account_fiscal_country_id': 'base.vn',
                'bank_account_code_prefix': '112',
                'cash_account_code_prefix': '111',
                'transfer_account_code_prefix': '113',
                'income_currency_exchange_account_id': 'c133_chart515',
                'expense_currency_exchange_account_id': 'c133_chart635',
                'account_sale_tax_id': 'c133_tax_sale_vat10',
                'account_purchase_tax_id': 'c133_tax_purchase_vat10',
                'account_default_pos_receivable_account_id': 'c133_chart1388',
                'default_cash_difference_income_account_id': 'c133_chart711',
                'default_cash_difference_expense_account_id': 'c133_chart811',
                'account_journal_early_pay_discount_loss_account_id': 'c133_chart635',
                'account_journal_early_pay_discount_gain_account_id': 'c133_chart515',
                # New fields added via viin_account
                'vat_ctp_account_id': 'c133_chart1331',
                'general_employee_payable_account_id': 'c133_chart334',
                'advance_account_id': 'c133_chart141',
                'currency_conversion_diff_income_account_id': 'c133_chart711',
                'currency_conversion_diff_expense_account_id': 'c133_chart811',
                'import_vat_ctp_account_id': 'c133_chart1331',
                'export_vat_ctp_account_id': 'c133_chart1331',
                'borrowing_account_id': 'c133_chart3411',
                'lending_account_id': 'c133_chart1288',
                'deferred_revenue_account_id': 'c133_chart3387',
                'prepaid_expense_account_id': 'c133_chart242',
                'export_tax_ids': [Command.set([
                    'c133_tax_export_0',
                    'c133_tax_sale_vat_exemption',
                ])],
                'import_tax_ids': [Command.set([
                    'c133_tax_import_10',
                    'c133_tax_purchase_import_10',
                ])],
            },
        }
