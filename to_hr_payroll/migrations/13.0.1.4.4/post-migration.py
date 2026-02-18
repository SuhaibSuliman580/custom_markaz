from odoo import api, SUPERUSER_ID


def _fix_personal_tax_base_rules(env):
    wrong_code = """
result=categories.GROSS
if payslip.personal_tax_rule_id.apply_tax_base_deduction:
    result -= TBDED
"""
    right_code = """
result=categories.GROSS
if payslip.personal_tax_rule_id.apply_tax_base_deduction:
    result -= TBDED
if result < 0.0:
    result = 0.0
"""
    for company in env['res.company'].search([]).sudo():
        tax_base_categ = company._get_salary_rule_categ('TAXBASE')
        if tax_base_categ:
            rules = env['hr.salary.rule'].sudo().search([
                ('company_id', '=', company.id),
                ('code', '=', 'TAXBASE'),
                ('amount_python_compute', '=', wrong_code)
                ])
            if rules:
                rules.write({
                    'amount_python_compute': right_code
                    })


def _fix_personal_tax(env):
    for company in env['res.company'].search([]).sudo():
        tax_base_categ = company._get_salary_rule_categ('TAXBASE')
        if tax_base_categ:
            rules = env['hr.salary.rule'].sudo().search([
                ('company_id', '=', company.id),
                ('code', '=', 'TAXBASE')
                ])
            ps_lines = env['hr.payslip.line'].sudo().search([
                ('company_id', '=', company.id),
                ('amount', '<', 0.0),
                '|', ('code', '=', 'TAXBASE'), ('salary_rule_id', 'in', rules.ids),
                ])
            if ps_lines:
                ps_lines.write({'amount': 0.0, 'total': 0.0})


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_personal_tax_base_rules(env)
    _fix_personal_tax(env)
