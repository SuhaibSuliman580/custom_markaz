from odoo import api, SUPERUSER_ID
from odoo.tools.sql import drop_constraint


def _apply_cycle(env):
    cycle = env.ref('to_hr_payroll.hr_salary_cycle_default')
    env['hr.working.month.calendar'].search([]).write({
        'salary_cycle_id': cycle.id
        })
    env['res.company'].search([]).write({
        'salary_cycle_id': cycle.id
        })
    env['hr.payslip'].search([]).write({
        'salary_cycle_id': cycle.id
        })


def migrate(cr, version):
    drop_constraint(cr, 'hr_working_month_calendar_line', 'hr_working_month_calendar_line_month_discrepany_check')
    env = api.Environment(cr, SUPERUSER_ID, {})
    _apply_cycle(env)
