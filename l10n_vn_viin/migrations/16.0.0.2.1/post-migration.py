from odoo import api, SUPERUSER_ID


def _fix_accounts_type(env):
    vn_coa = env['account.chart.template']._get_installed_vietnam_coa_templates()
    vn_companies = env['res.company'].with_context(active_test=False).search([
        ('chart_template_id', 'in', vn_coa.ids)
    ])
    vn_companies._fix_accounts_type({
        'asset_current': ['1381'],
        'liability_current': ['3381'],
    })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_accounts_type(env)
