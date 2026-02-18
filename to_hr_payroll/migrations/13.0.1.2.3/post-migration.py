from odoo import api, SUPERUSER_ID


def _fix_tax_base_rules(env):
    """
    Fix tax base rules' category for version 13.0.1.2.3
    """
    for company in env['res.company'].search([]).sudo():
        tax_base_categ = company._get_salary_rule_categ('TAXBASE')
        if tax_base_categ:
            rules = env['hr.salary.rule'].sudo().search([('company_id', '=', company.id), ('code', '=', 'TAXBASE')])
            if rules:
                rules.write({
                    'category_id': tax_base_categ.id
                    })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.company'].search([]).sudo()._generate_payroll_rules()
    _fix_tax_base_rules(env)
