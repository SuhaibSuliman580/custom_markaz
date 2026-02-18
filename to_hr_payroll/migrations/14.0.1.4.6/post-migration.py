from odoo import api, SUPERUSER_ID


def _update_noupdate_access_rules(env):
    rules_map = {
        'hr_contract_rule_officer': {
            'name': 'Officer - All contracts (View only)',
            'domain_force': "[(1,'=',1)]"
            },
        'hr_contract_rule_admin': {
            'name': 'Administrator - All contracts',
            },
        'hr_payroll_personal_payslip': {
            'name': 'Personal Payslips',
            },
        'hr_payslip_team_leader': {
            'name': 'Team Leader and subordinates Payslips',
            'domain_force': """[
                '|',
                ('employee_id', 'in', (user.employee_id.subordinate_ids | user.employee_ids.subordinate_ids).ids),
                ('employee_id.department_id.manager_id.user_id', '=', user.id)
                ]"""
            },
        'hr_payroll_rule_officer': {
            'name': 'Officer - All Payslips',
            'domain_force': "[(1,'=',1)]"
            },
        'hr_payslip_line_team_leader': {
            'name': 'Team Leader and subordinates Payslip Lines',
            'domain_force': """[
                '|',
                ('employee_id', 'in', (user.employee_id.subordinate_ids | user.employee_ids.subordinate_ids).ids),
                ('employee_id.department_id.manager_id.user_id', '=', user.id)
                ]"""
            },

        'hr_payroll_line_rule_officer': {
            'name': 'Officer - All Payslip Lines',
            'domain_force': "[(1,'=',1)]"
            },
        'payslip_personal_income_tax_analysis_team_leader': {
            'domain_force': """[
                '|',
                ('employee_id', 'in', (user.employee_id.subordinate_ids | user.employee_ids.subordinate_ids).ids),
                ('employee_id.department_id.manager_id.user_id', '=', user.id)
                ]"""
            },
        'payslip_personal_income_tax_analysis_officer': {
            'name': 'Officer - All Income Tax Analysis',
            'domain_force': "[(1,'=',1)]"
            },
        'hr_payroll_analysis_team_leader_rule': {
            'domain_force': """[
                '|',
                ('employee_id', 'in', (user.employee_id.subordinate_ids | user.employee_ids.subordinate_ids).ids),
                ('employee_id.department_id.manager_id.user_id', '=', user.id)
                ]"""
            },
        }
    for xml_id, vals in rules_map.items():
        env.ref('%s.%s' % ('to_hr_payroll', xml_id)).write(vals)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_noupdate_access_rules(env)
