from odoo import api, SUPERUSER_ID


def _update_salary_rule_categories(env):
    codes = [
        'BASIC',
        'ALW',
        'TRAVEL',
        'PHONE',
        'MEAL',
        'RESPONSIBILITY',
        'HARDWORK',
        'PERFORMANCE',
        'COMP',
        'C_INSURANCE',
        'C_LU',
        'ALWNOTAX',
        'HARMFUL',
        ]
    categories = env['hr.salary.rule.category'].sudo().search([('code', 'in', codes)])
    if categories:
        categories.sudo().write({'paid_by_company': True})


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_salary_rule_categories(env)
