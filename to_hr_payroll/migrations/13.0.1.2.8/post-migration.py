from odoo import api, SUPERUSER_ID


def _fix_payslip_leaves(env):
    all_working_month_calendar_lines = env['hr.working.month.calendar.line'].search([])
    if all_working_month_calendar_lines:
        all_working_month_calendar_lines._compute_leaves()
        all_working_month_calendar_lines.mapped('working_month_calendar_id.payslip_id').filtered(lambda ps: ps.state == 'draft').compute_sheet()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_payslip_leaves(env)
