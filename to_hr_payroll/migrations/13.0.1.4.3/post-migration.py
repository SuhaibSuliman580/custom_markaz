from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fill_missing_worked_days_line_ids(env)


def _fill_missing_worked_days_line_ids(env):
    missing_worked_days_lines_slips = env['hr.payslip'].search([('worked_days_line_ids', '=', False)])
    if missing_worked_days_lines_slips:
        missing_worked_days_lines_slips._compute_worked_days_line_ids()
