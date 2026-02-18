# -*- coding: utf-8 -*-
# Copyright 2018 Openinside co. W.L.L.
{
    "name": "Payslip Batches Type",
    "summary": "Payslip Batches Type, Easier Reporting and Grouping, Payroll Management, Group or Filter Payslip Batches by Type, Report, Salary, Salary Structure, Salary Rule, Payroll, Payslip, Employee, HR",
    "version": "17.0.0.0",
    'category': 'Human Resources',
    "website": "https://www.open-inside.com",
	"description": """
		
		 
    """,
    "author": "Openinside",
    "license": "OPL-1",
    "price" : 0,
    "currency": 'USD',
    "installable": True,
    "depends": [
        'oi_payroll'
    ],
    "data": [
        'security/ir.model.access.csv',
        'view/hr_payslip_run.xml',
        'view/action.xml',
        'view/menu.xml'
    ],
    'odoo-apps' : True,
    'images':[
        'static/description/cover.png'
    ],
}

