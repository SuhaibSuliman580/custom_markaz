from odoo import api, SUPERUSER_ID


def _fix_personal_income_tax_sal_rules(env):
    Rule = env['hr.salary.rule'].sudo()
    rules = Rule.search([('code', '=', 'PTAX')])
    if rules:
        rules.sudo().write({
'amount_python_compute': """
# DO NOT MODIFY UNLESS YOU KNOW WHAT YOU ARE DOING

# the the base for tax computation from TAXBASE rule
tax_base = TAXBASE

# set the initial value for the tax amount
tax = 0.0

# get the personal income tax rule from payslip
tax_rule = payslip.personal_tax_rule_id

# compute tax amount base on the policy of either Flat Rate or Progressive Tax Table
if tax_rule.personal_tax_policy == 'flat_rate':
    tax += tax_rule.personal_tax_flat_rate * tax_base / 100.0

elif tax_rule.personal_tax_policy == 'escalation':
    for rule in tax_rule.progress_ids.sorted('rate', reverse=True):
        rule_base = rule._get_base(payslip)
        if tax_base > rule_base:
            diff = tax_base - rule.base
            tax += rule.rate * diff / 100.0
            tax_base -= diff
result = -1 * tax
"""
            })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _fix_personal_income_tax_sal_rules(env)
