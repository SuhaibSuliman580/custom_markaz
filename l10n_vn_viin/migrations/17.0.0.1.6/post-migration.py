from odoo import SUPERUSER_ID, api


def _change_account_types(env):
    """This function changes all 133 tax accounts from non-reconcile to reconcilable (reconcile=True).
    In tax-related activities, we often need to check input taxes to deduct taxes payable to the state. Hence,
    make all the tax journal items reconcilable is necessary.
    Note, the output tax accounts (accounts 333*) is already reconcilable.
    """
    companies = env['res.company'].with_context(active_test=False).search([
        ('chart_template', 'in', env['account.chart.template']._get_installed_vietnam_coa_templates())
        ])
    accounts = env['account.account'].search([
        ('company_id', 'in', companies.ids)
        ]).filtered(
            lambda acc: acc.code.startswith('133') and not acc.reconcile
            )
    if accounts:
        accounts.reconcile = True


def _fix_vietnam_user_defined_sub_accounts_income_financial_income_deduction(env):
    env['res.company'].with_context(active_test=False).search([])._fix_vietnam_user_defined_sub_accounts_income_financial_income_deduction()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _change_account_types(env)
    _fix_vietnam_user_defined_sub_accounts_income_financial_income_deduction(env)
