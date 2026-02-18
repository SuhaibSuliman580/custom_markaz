from odoo import api, SUPERUSER_ID


def _update_current_history_line(env):
    contribution_registers = env['hr.payroll.contribution.register'].search([('state', 'not in', ('draft', 'cancelled'))])
    contribution_registers._compute_current_history_id()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_current_history_line(env)
