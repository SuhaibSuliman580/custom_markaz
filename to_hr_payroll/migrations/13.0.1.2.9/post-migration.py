from odoo import api, SUPERUSER_ID, _


def _fix_labor_union_categ(env):
    """
    This modifies category DED to DED_BEFORE_TAX, and create another category named DED_AFTER_TAX
    then change the parent category of the E_LU from DED_BEFORE_TAX to DED_AFTER_TAX
    """
    RuleCateg = env['hr.salary.rule.category'].sudo()
    ded_categs = RuleCateg.search([('code', '=', 'DED')])
    if ded_categs:
        ded_categs.sudo().write({
            'name': _('Deduction (before taxes)'),
            'code': 'DED_BEFORE_TAX'
            })
    for company in env['res.company'].search([]):
        ded_after_tax_categ = RuleCateg.search([('code', '=', 'DED_AFTER_TAX'), ('company_id', '=', company.id)])
        if not ded_after_tax_categ:
            ded_after_tax_categ = RuleCateg.create({
                'name': _('Deduction (after taxes)'),
                'code': 'DED_AFTER_TAX',
                'company_id': company.id
                })
        RuleCateg.search([
            ('code', '=', 'E_LU'),
            ('company_id', '=', company.id),
            ('parent_id', '!=', ded_after_tax_categ.id)
            ]).sudo().write({
                'parent_id': ded_after_tax_categ.id
                })


def _fix_tax_base_deduct_sal_rules(env):
    Rule = env['hr.salary.rule'].sudo()
    rules = Rule.search([('code', '=', 'TBDED')])
    if rules:
        rules.sudo().write({
            'amount_python_compute': 'result = payslip.personal_tax_rule_id.personal_tax_base_ded + payslip.dependent_deduction - categories.DED_BEFORE_TAX'
            })


def _fix_net_sal_rules(env):
    Rule = env['hr.salary.rule'].sudo()
    rules = Rule.search([('code', '=', 'NET')])
    if rules:
        rules.sudo().write({
            'amount_python_compute': 'result = categories.GROSS + categories.ALWNOTAX + categories.DED_BEFORE_TAX + categories.DED_AFTER_TAX + categories.PTAX'
            })


def _recompute_draft_payslips(env):
    all_draft_payslips = env['hr.payslip'].sudo().search([('state', '=', 'draft')])
    if all_draft_payslips:
        all_draft_payslips.sudo().compute_sheet()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # labor union fee is taxable item.
    # the following changes categories and rules so that labor union fee will be applied after personal tax computation
    _fix_labor_union_categ(env)
    _fix_tax_base_deduct_sal_rules(env)
    _fix_net_sal_rules(env)
    _recompute_draft_payslips(env)
