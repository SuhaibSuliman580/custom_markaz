from datetime import date
from odoo import api, SUPERUSER_ID


def _fix_access_rules(env):
    payslip_personal_income_tax_analysis_officer_rule = env.ref('to_hr_payroll.payslip_personal_income_tax_analysis_officer')
    payslip_personal_income_tax_analysis_officer_rule.write({
        'groups': [(6, 0, [env.ref('to_hr_payroll.group_hr_payroll_user').id])]
        })


def _update_13th_month_slips_dates(env):
    all_13th_month_payslips = env['hr.payslip'].sudo().search([('thirteen_month_pay', '=', True)])
    for year in set(all_13th_month_payslips.mapped('thirteen_month_pay_year')):
        date_from = date(year, 1, 1)
        date_to = date(year, 12, 31)
        slips = all_13th_month_payslips.filtered(
            lambda ps:
                ps.thirteen_month_pay_year == year
                and (ps.date_from != date_from or ps.date_to != date_to)
                )
        if slips:
            slips.write({
                'date_from': date_from,
                'date_to': date_to,
                })


def _fill_missing_contract_in_working_month_calendar_lines(env):
    lines = env['hr.working.month.calendar.line'].sudo().search([
        ('contract_id', '=', False),
        ('working_month_calendar_id.payslip_id.thirteen_month_pay', '=', False)
        ])
    payslips = lines.working_month_calendar_id.payslip_id
    for payslip in payslips:
        lines_to_fix = lines.filtered(lambda l: l.working_month_calendar_id.payslip_id == payslip)
        # apply the context post_contract_discrepancy_error to post error message instead of raising error
        lines_to_fix.with_context(post_contract_discrepancy_error=True, log_contract_discrepancy_error=True).write({
            'contract_id': payslip.contract_id.id
            })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_access_rules(env)
    # the call order of the functions below is IMPORTANT
    # Do NOT change it
    _update_13th_month_slips_dates(env)
    _fill_missing_contract_in_working_month_calendar_lines(env)
