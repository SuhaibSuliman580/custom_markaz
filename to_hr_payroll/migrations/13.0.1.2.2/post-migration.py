from odoo import api, SUPERUSER_ID

SAL_RULE_MAP = {
    'BASIC': """
# Loop over the payslip's working calendar lines for wage calculation
wage = 0.0
for line in payslip.working_month_calendar_ids:
    # daily rate basis
    if contract.salary_computation_mode == 'day_basis':
        wage += contract.wage * line.duty_working_days / line.month_working_days
    # hourly rate basis
    else:
        wage += contract.wage * line.duty_working_hours / line.month_working_hours
result = wage
    """,

    'TRAVEL': """
# Loop over the payslip's working calendar lines for allowance
alw = 0.0
for line in payslip.working_month_calendar_ids:
    if contract.salary_computation_mode == 'day_basis':
        alw += advantages.TRAVEL.amount * line.duty_working_days / line.month_working_days
    else:
        alw += advantages.TRAVEL.amount * line.duty_working_hours / line.month_working_hours
result = alw
    """,

    'PHONE': """
# Loop over the payslip's working calendar lines for allowance
alw = 0.0
for line in payslip.working_month_calendar_ids:
    if contract.salary_computation_mode == 'day_basis':
        alw += advantages.PHONE.amount * line.duty_working_days / line.month_working_days
    else:
        alw += advantages.PHONE.amount * line.duty_working_hours / line.month_working_hours
result = alw
    """,

    'MEAL': """
# Loop over the payslip's working calendar lines for allowance
alw = 0.0
for line in payslip.working_month_calendar_ids:
    if contract.salary_computation_mode == 'day_basis':
        alw += advantages.MEAL.amount * line.duty_working_days / line.month_working_days
    else:
        alw += advantages.MEAL.amount * line.duty_working_hours / line.month_working_hours
result = alw
    """,

    'RESPONSIBILITY': """
# Loop over the payslip's working calendar lines for allowance
alw = 0.0
for line in payslip.working_month_calendar_ids:
    if contract.salary_computation_mode == 'day_basis':
        alw += advantages.RESPONSIBILITY.amount * line.duty_working_days / line.month_working_days
    else:
        alw += advantages.RESPONSIBILITY.amount * line.duty_working_hours / line.month_working_hours
result = alw
    """,

    'HARDWORK': """
# Loop over the payslip's working calendar lines for allowance
alw = 0.0
for line in payslip.working_month_calendar_ids:
    if contract.salary_computation_mode == 'day_basis':
        alw += advantages.HARDWORK.amount * line.duty_working_days / line.month_working_days
    else:
        alw += advantages.HARDWORK.amount * line.duty_working_hours / line.month_working_hours
result = alw
    """,

    'HARMFUL': """
# Loop over the payslip's working calendar lines for allowance
alw = 0.0
for line in payslip.working_month_calendar_ids:
    if contract.salary_computation_mode == 'day_basis':
        alw += advantages.HARMFUL.amount * line.duty_working_days/ line.month_working_days
    else:
        alw += advantages.HARMFUL.amount * line.duty_working_hours/ line.month_working_hours
result = alw
    """
    }


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    codes = list(SAL_RULE_MAP.keys())
    salary_rules = env['hr.salary.rule'].search([('code', 'in', codes)])
    for rule in salary_rules:
        rule.write({
            'amount_python_compute':  SAL_RULE_MAP[rule.code]
            })
