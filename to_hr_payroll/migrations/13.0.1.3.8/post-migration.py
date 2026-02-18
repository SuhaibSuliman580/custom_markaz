from odoo import api, SUPERUSER_ID


def _fix_tax_base_rule(env):
    tax_base_rules = env['hr.salary.rule'].sudo().search([
        ('code', '=', 'TAXBASE'),
        ('amount_python_compute', '=', 'result=categories.GROSS - TBDED')
        ])
    if tax_base_rules:
        tax_base_rules._reset()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_tax_base_rule(env)
