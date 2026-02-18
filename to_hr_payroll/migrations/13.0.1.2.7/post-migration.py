from odoo import api, SUPERUSER_ID


def _fix_contribution_lost(env):
    all_contracts = env['hr.contract'].search([])
    all_contracts._compute_payroll_contribution_registers()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_contribution_lost(env)
