from odoo import SUPERUSER_ID, api


def _update_account_type_and_fix_reconsile(env):
    """
    Account type of 138 and 338 changed to receivable/payable from odoo 14.0
    But we changed them to current asset and liability from 14.0 (do not know why)
    We need revert them to receivable/payable.
    """
    vn_charts = env['account.chart.template']._get_installed_vietnam_coa_templates()

    # update account type for 138, 338
    account_template_138 = env['account.account.template'].search([
        ('chart_template_id', 'in', vn_charts.ids),
        ('code', '=ilike', '138%')])
    account_template_138.write({'account_type': 'asset_receivable'})

    account_138 = env['account.account'].search([
        ('company_id.chart_template_id', 'in', vn_charts.ids),
        ('code', '=ilike', '138%')])
    account_138.write({'account_type': 'asset_receivable'})

    account_template_338 = env['account.account.template'].search([
        ('chart_template_id', 'in', vn_charts.ids),
        ('code', '=ilike', '338%')])
    account_template_338.write({'account_type': 'liability_payable'})

    account_338 = env['account.account'].search([
        ('company_id.chart_template_id', 'in', vn_charts.ids),
        ('code', '=ilike', '338%')])
    account_338.write({'account_type': 'liability_payable'})

    # set reconcile for 3386
    account_template_3386 = env['account.account.template'].search([
        ('chart_template_id', 'in', vn_charts.ids),
        ('code', '=ilike', '3386%')])
    account_template_3386.write({'reconcile': True})
    account_3386 = env['account.account'].search([
        ('company_id.chart_template_id', 'in', vn_charts.ids),
        ('code', '=ilike', '3386%')])
    account_3386.write({'reconcile': True})


def _set_default_for_account_receivable_c133(env):
    vn_c133_companies = env['res.company'].with_context(active_test=False).search([('chart_template_id', '=', env.ref('l10n_vn_viin.vn_template_c133').id)])
    for company in vn_c133_companies:
        account_131 = env['account.account'].search([
        ('company_id', '=', company.id),
        ('code', '=', '131')])
        if account_131:
            env['ir.property']._set_default('property_account_receivable_id', 'res.partner', account_131, company=company)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_account_type_and_fix_reconsile(env)
    _set_default_for_account_receivable_c133(env)
    env['res.company']._generate_property_accounts()
