from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.tests.common import TransactionCase


class Common(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(Common, cls).setUpClass()

        today = fields.Date.today()
        cls.current_year = today.year
        # Employee
        cls.employee_admin = cls.env.ref('hr.employee_admin')
        cls.employee_demo = cls.env.ref('hr.employee_qdp')
        cls.employee_1 = cls.env.ref('hr.employee_stw')

        # Contract
        cls.env.ref('hr_contract.hr_contract_admin_new').state = 'cancel'

        cls.contract_admin = cls.env.ref('hr_contract.hr_contract_admin')
        cls.contract_admin.write({
            'set_pay_per_meal': True,
            'pay_per_meal': 30000,
            'date_end': fields.Date.end_of(today, 'month')
        })
        if cls.contract_admin.state == 'draft':
            cls.contract_admin.state = 'open'

        cls.contract_employee_demo = cls.env.ref('hr_contract.hr_contract_qdp')
        cls.contract_employee_demo.write({
            'set_pay_per_meal': True,
            'pay_per_meal': 30000,
            'date_start': fields.Date.to_date('%s-01-01' % cls.current_year)
        })
        cls.contract_employee_1 = cls.env.ref('hr_contract.hr_contract_stw')
        cls.contract_employee_1.write({
            'set_pay_per_meal': True,
            'pay_per_meal': 30000,
            'date_start': fields.Date.to_date('%s-01-01' % cls.current_year)
        })

        # Meal type
        cls.meal_type_1 = cls.env.ref('to_hr_meal.hr_meal_type_lunch_for_everyone')
        cls.meal_type_1.price = 35000

        # Meal Orders
        cls.meal_order_1 = cls.env['hr.meal.order'].create({
            'meal_type_id': cls.meal_type_1.id,
            'scheduled_hour': 12
        })
        cls.meal_order_2 = cls.env['hr.meal.order'].create({
            'meal_type_id': cls.meal_type_1.id,
            'scheduled_date': date.today() + relativedelta(months=1),
            'scheduled_hour': 12
        })
        # Meal line data
        cls.meal_line_admin_data = {
            'employee_id': cls.employee_admin.id,
            'quantity': 1,
            'price': 35000,
            'meal_type_id': cls.meal_type_1.id
        }

        # Salary structure
        cls.salary_structure = cls.env['hr.payroll.structure'].search([('code', '=', 'BASE')], limit=1)

        # Salary Cycle
        cls.salary_cycle_default = cls.env.ref('to_hr_payroll.hr_salary_cycle_default')

        # Payslip data for this month
        start_month = fields.Date.start_of(today, 'month')
        end_month = fields.Date.end_of(today, 'month')
        cls.payslip_admin_data = {
            'employee_id': cls.employee_admin.id,
            'salary_cycle_id': cls.salary_cycle_default.id,
            'date_from': start_month,
            'date_to': end_month,
            'company_id': cls.env.company.id
        }

        cls.payslip_admin = cls.env['hr.payslip'].create(cls.payslip_admin_data)
