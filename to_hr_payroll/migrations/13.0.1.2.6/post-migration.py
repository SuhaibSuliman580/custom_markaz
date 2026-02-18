from odoo import api, SUPERUSER_ID


def _fix_security(env):
    rule = env.ref('to_hr_payroll.hr_payroll_rule_officer')
    rule.write({
        'domain_force': "['|',('employee_id.department_id', '=', False),('employee_id.department_id.manager_id.user_id', '=', user.id)]",
        'perm_unlink': True,
        'perm_write': True,
        'perm_read': True,
        'perm_create': True,
        })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _fix_security(env)
