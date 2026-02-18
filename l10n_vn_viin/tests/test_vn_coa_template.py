from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestChartAccountVN(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='vn'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def _account_vn_skip_check(self):
        return ['1131', '132', '9993', '9994']

    def test_vn_coa_template_001(self):
        vn_template = self.env['account.chart.template']._get_account_account('vn')
        vn_demo_company = self.env.ref('l10n_vn.demo_company_vn')
        vn_new_company = self.setup_company_data('VN New Company', chart_template='vn')['company']
        Account = self.env['account.account'].sudo().with_context(active_test=False)

        for comp in [vn_demo_company, vn_new_company]:
            account_vals_list = Account.search_read(
                [('company_id', '=', comp.id), ('deprecated', '=', False)],
                ['code', 'reconcile', 'account_type']
            )
            for _xml, acc_template_data in vn_template.items():
                if acc_template_data['code'] in self._account_vn_skip_check():
                    continue
                acc_vals = next(filter(lambda x: x['code'] == acc_template_data['code'], account_vals_list), {'reconcile': False, 'account_type': ''})
                self.assertEqual(acc_template_data.setdefault('reconcile', False), acc_vals['reconcile'], acc_template_data['code'])
                self.assertEqual(acc_template_data.setdefault('account_type', ''), acc_vals['account_type'], acc_template_data['code'])
