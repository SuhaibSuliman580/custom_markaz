# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payroll',
    'category': 'Human Resources',
    'sequence': 38,
    'summary': 'Manage your employee payroll records',
    'description': "",
    'version': '17.0.0.0.1',
    'website': "https://www.open-inside.com",
    'author': 'Openinside',
    "license": "OPL-1",
    'depends': [
        'hr_contract',
        'hr_holidays',
    ],
    "excludes": [
        "hr_payroll"
    ],
    'data': [
        'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',
        'wizard/hr_payroll_payslips_by_employees_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_employee_views.xml',
        'data/hr_payroll_sequence.xml',
        'views/hr_payroll_report.xml',
        'data/hr_payroll_data.xml',
        'wizard/hr_payroll_contribution_register_report_views.xml',
        'views/report_contributionregister_templates.xml',
        'views/report_payslip_templates.xml',
        'views/report_payslipdetails_templates.xml',
        'views/payslip_line_report.xml'
    ],
    'images': [
        'static/description/cover.png'
    ],
    'demo': ['data/hr_payroll_demo.xml'],
    'odoo-apps': True,
    "currency": 'USD',
    "price": 9.99,
}
