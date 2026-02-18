from . import models
from . import reports

from odoo import api, SUPERUSER_ID

import logging

_logger = logging.getLogger(__name__)

try:
    from odoo.addons.account.models.ir_module import IrModule
    func_compute_account_templates = IrModule._compute_account_templates
except Exception:
    func_compute_account_templates = None


def _compute_account_templates_plus(self):
    """ Module l10n_vn_viin is a fix chart account in module for the l10n_vn account system,
        not a module that redefines the system account of the l10n_vn module.
        Therefore, it is necessary to reset the information so that the system can load the CoA l10n_vn
    """
    func_compute_account_templates(self)
    for r in self:
        if 'vn' in r.account_templates:
            r.account_templates['vn']['module'] = 'l10n_vn'


if func_compute_account_templates:
    IrModule._compute_account_templates = _compute_account_templates_plus


def _fix_vn_chart_template(env):
    """ Fix the CoA of the company to comply with the Vietnamese accounting system """

    vn_companies = env['res.company'].with_context(active_test=False).search([('chart_template', '=', 'vn'), ('parent_id', '=', False)])

    # Fix VietNam CoA
    vn_companies._fix_vietnam_coa()

    for company in vn_companies:
        ChartTemplate = env['account.chart.template'].with_company(company)
        _logger.info("Company %s already has the VietNam localization installed, updating...", company.name)

        data = ChartTemplate._get_chart_template_data('vn')
        # Set the tax groups is vat
        account_tax_groups_data = data['account.tax.group']

        # Add tax import
        account_tax_data = env['account.chart.template']._parse_csv('vn', 'account.tax', module='l10n_vn_viin')
        ChartTemplate._deref_account_tags('vn', account_tax_data)

        # Fill default accounts for company
        res_company_data = data['res.company']
        account_account_data = data['account.account']
        account_map_code = company._prepare_account_for_company_map_code()
        for map_field, map_code in account_map_code.items():
            for xml_id, record in account_account_data.items():
                if record['code'] == map_code:
                    account_map_code.update({map_field: xml_id})
                    break
        res_company_data[company.id].update(account_map_code)

        # Generate property accounts
        template_data = data['template_data']
        data = {
            'res.company': res_company_data,
            'account.tax.group': account_tax_groups_data,
            'account.tax': account_tax_data,
            'account.account': account_account_data,
        }

        data = ChartTemplate._pre_load_data('vn', company, template_data, data)
        ChartTemplate._load_data(data)
        ChartTemplate._post_load_data('vn', company, template_data)

        # Update show both dr and cr trial balance vas
        company._update_show_both_dr_and_cr_trial_balance_vas()


def post_init_hook(env):
    _fix_vn_chart_template(env)
