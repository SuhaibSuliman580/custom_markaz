from odoo import api, SUPERUSER_ID


def _fill_contract_pay_per_meal(env):
    contracts = env['hr.contract'].with_context(active_test=False).search([('state', 'in', ('draft', 'open', 'close'))])
    for company in contracts.with_context(active_test=False).mapped('company_id').filtered(lambda comp: comp.default_meal_emp_price):
        contracts.filtered(lambda c: c.company_id == company).write({
            'pay_per_meal': company.default_meal_emp_price
            })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fill_contract_pay_per_meal(env)
