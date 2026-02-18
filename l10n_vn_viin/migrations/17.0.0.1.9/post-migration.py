from odoo import api, SUPERUSER_ID
from odoo.osv import expression

FIXED_TYPE_CODES_MAP = {
    'expense_direct_cost': ('611', '621', '622', '627'),
}


def _fix_accounts_type(env):
    vn_companies = env['res.company'].with_context(active_test=False).search([('chart_template', '=', 'vn')])
    for correct_account_type, account_codes in FIXED_TYPE_CODES_MAP.items():
        domain = expression.AND([
            [('company_id', 'in', vn_companies.ids), ('account_type', '!=', correct_account_type)],
            expression.OR([
                [('code', '=like', f'{code}%')] for code in account_codes
            ])
        ])
        accounts = env['account.account'].search(domain)
        accounts.write({
            'account_type': correct_account_type
        })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_accounts_type(env)
