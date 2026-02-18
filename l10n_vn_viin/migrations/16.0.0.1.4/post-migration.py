from odoo import SUPERUSER_ID, api


def _update_account_type(env):
    """
    Account type of 214 is always asset_non_current from odoo
    But we changed it to expense_depreciation (do not know why)
    We need revert it to asset_non_current.
    """
    vn_charts = env['account.chart.template']._get_installed_vietnam_coa_templates()

    account_template_214 = env['account.account.template'].search([
        ('chart_template_id', 'in', vn_charts.ids),
        ('code', '=ilike', '214%')])
    account_template_214.write({'account_type': 'asset_non_current'})

    account_214 = env['account.account'].search([
        ('company_id.chart_template_id', 'in', vn_charts.ids),
        ('code', '=ilike', '214%')])
    account_214.write({'account_type': 'asset_non_current'})


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_account_type(env)
