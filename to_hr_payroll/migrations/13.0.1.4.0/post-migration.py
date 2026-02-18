from odoo import api, SUPERUSER_ID


def _update_no_update_access_rules(env):
    rules = {
        'hr_contract_rule_officer': {
            'domain_force': "['|',('employee_id', 'in', user.employee_id.subordinate_ids.ids),('employee_id.department_id.manager_id.user_id', '=', user.id)]",
            },
        'hr_payroll_rule_officer': {
            'domain_force': "['|',('employee_id', 'in', user.employee_id.subordinate_ids.ids),('employee_id.department_id.manager_id.user_id', '=', user.id)]",
            },
        'hr_payroll_line_rule_officer': {
            'domain_force': "['|',('employee_id', 'in', user.employee_id.subordinate_ids.ids),('employee_id.department_id.manager_id.user_id', '=', user.id)]",
            },
        'payslip_personal_income_tax_analysis_officer': {
            'domain_force': "['|',('employee_id', 'in', user.employee_id.subordinate_ids.ids),('employee_id.department_id.manager_id.user_id', '=', user.id)]",
            },
        }
    for rule_name, vals in rules.items():
        env.ref('to_hr_payroll.' + rule_name).write(vals)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_no_update_access_rules(env)
