from odoo import api, SUPERUSER_ID


def _recompute_company_cost(env):
    payslips = env['hr.payslip'].sudo().search([('company_cost', '=', 0.0)])
    if payslips:
        payslips.sudo()._compute_company_cost()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _recompute_company_cost(env)
