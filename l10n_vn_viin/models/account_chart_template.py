from odoo import models, tools
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @tools.ormcache()
    def _get_installed_vietnam_coa_templates(self):
        return ('vn', 'vn_c133')

    @template(template='vn', model='account.group')
    def _get_vn_account_group(self):
        return self._parse_csv('vn', 'account.group', 'l10n_vn_viin')

    @template(model='account.account')
    def _get_account_account(self, template_code):
        res = super()._get_account_account(template_code)
        if template_code == 'vn':
            vn_accounts = self._parse_csv('vn', 'account.account', module='l10n_vn_viin')
            for viin_acc_key, viin_acc_value in vn_accounts.items():
                if viin_acc_key in res:
                    res[viin_acc_key].update(viin_acc_value)
                else:
                    res[viin_acc_key] = viin_acc_value
        return res

    @template(model='account.tax.group')
    def _get_account_tax_group(self, template_code):
        res = super()._get_account_tax_group(template_code)
        if template_code == 'vn':
            vn_taxes = self._parse_csv('vn', 'account.tax.group', module='l10n_vn_viin')
            for viin_tax_key, viin_tax_value in vn_taxes.items():
                if viin_tax_key in res:
                    res[viin_tax_key].update(viin_tax_value)
                else:
                    res[viin_tax_key] = viin_tax_value
            self.env['account.tax.group']._set_tax_group_is_vat_vietnam(res)
        return res

    @template(model='account.tax')
    def _get_account_tax(self, template_code):
        res = super()._get_account_tax(template_code)
        if template_code == 'vn':
            vn_taxes = self._parse_csv('vn', 'account.tax', module='l10n_vn_viin')
            self._deref_account_tags(template_code, vn_taxes)
            for viin_tax_key, viin_tax_value in vn_taxes.items():
                if viin_tax_key in res:
                    res[viin_tax_key].update(viin_tax_value)
                else:
                    res[viin_tax_key] = viin_tax_value
        return res

    @template(template='vn', model='template_data')
    def _get_vn_additional_properties(self):
        return {
            'additional_properties': dict(self._prepare_property_account_to_generate())
        }

    @template(template='vn_c133', model='template_data')
    def _get_vn_c133_additional_properties(self):
        return {
            'additional_properties': dict(self._prepare_property_account_to_generate())
        }

    def _load(self, template_code, company, install_demo):
        reload_template = template_code == company.chart_template
        super()._load(template_code, company, install_demo)
        if not reload_template and template_code in ('vn', 'vn_c133'):
            if template_code == 'vn':
                company._fix_vietnam_coa()
            company._update_show_both_dr_and_cr_trial_balance_vas()
