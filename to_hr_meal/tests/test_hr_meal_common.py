from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestHrMealCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestHrMealCommon, cls).setUpClass()

        group_internal_user = cls.env.ref('base.group_user')
        group_hr_meal_user = cls.env.ref('to_hr_meal.hr_meal_group_user')
        group_hr_meal_manager = cls.env.ref('to_hr_meal.hr_meal_group_admin')

        # Users
        Users = cls.env['res.users'].with_context({'no_reset_password': True})
        cls.user_meal_user = Users.create({
            'name': 'Sarah MealUser',
            'login': 'sarah_mealuser',
            'email': 'sarah.mealuser@example.viindoo.com',
            'groups_id': [(6, 0, [group_internal_user.id, group_hr_meal_user.id])]
        })

        cls.user_meal_user_responsible = Users.create({
            'name': 'Peter MealUser',
            'login': 'Peter_mealuser',
            'email': 'peter.mealuser@example.viindoo.com',
            'groups_id': [(6, 0, [group_internal_user.id, group_hr_meal_user.id])]
        })

        cls.user_meal_manager = Users.create({
            'name': 'Gordon MealManager',
            'login': 'gordon_mealmanager',
            'email': 'gordon.mealmanager@example.viindoo.com',
            'groups_id': [(6, 0, [group_internal_user.id, group_hr_meal_manager.id])]
        })

        cls.user_1 = Users.create({
            'name': 'May Employee',
            'login': 'may_employee',
            'email': 'may.employee@example.viindoo.com',
            'groups_id': [(6, 0, [group_internal_user.id])],
        })

        cls.user_2 = Users.create({
            'name': 'Milia Employeee',
            'login': 'milia_employee',
            'email': 'milia.employee@example.viindoo.com',
            'groups_id': [(6, 0, [group_internal_user.id])],
        })

        # Employees
        Employee = cls.env['hr.employee'].with_context(tracking_disable=True)
        cls.employee_1 = Employee.create({
            'name': 'John Employee',
            'work_email': 'John.employee@example.viindoo.com',
            'user_id': cls.user_1.id
        })

        cls.employee_2 = Employee.create({
            'name': 'Milia Employee',
            'work_email': 'milia.employee@example.viindoo.com',
            'user_id': cls.user_2.id
        })

        cls.employee_3 = Employee.create({
            'name': 'Maria Employee',
            'work_email': 'maria.employee@example.viindoo.com',
        })

        cls.employee_4 = Employee.create({
            'name': 'David Employee',
            'work_email': 'david.employee@example.viindoo.com',
        })

        cls.employee_5 = Employee.create({
            'name': 'Larry Employee',
            'work_email': 'larry.employee@example.viindoo.com',
        })

        # Test kitchens
        cls.kitchen = cls.env['hr.kitchen'].with_user(cls.user_meal_manager).create({
            'name': 'Awesome Kitchen',
            'responsible_id': cls.user_meal_user_responsible.partner_id.id
        })

        # Test meal type
        cls.meal_type_lunch = cls.env['hr.meal.type'].with_user(cls.user_meal_manager).create({
            'name': 'Lunch Meal',
            'price': 10.0,
            'description': 'This is a lunch meal'
        })

        cls.meal_type_dinner = cls.env['hr.meal.type'].with_user(cls.user_meal_manager).create({
            'name': 'Dinner Meal',
            'price': 10.0,
            'description': 'This is a dinner meal'
        })

    def create_meal_order(self, meal_type, order_source, employees):
        MealOrder = self.env['hr.meal.order'].with_user(self.user_meal_manager).with_context({'mail_create_nolog': True})
        meal_order_form = Form(MealOrder)
        meal_order_form.order_source = order_source

        if order_source == 'external':
            meal_order_form.vendor_id = self.user_meal_user_responsible.partner_id
        elif order_source == 'internal':
            meal_order_form.kitchen_id = self.kitchen

        for employee in employees:
            with meal_order_form.order_line_ids.new() as line:
                line.employee_id = employee

        meal_order_form.meal_type_id = meal_type  # The mechanism of 'Form' on odoo 14 is slightly changed, causing an error if set value of type first
        meal_order = meal_order_form.save()
        return meal_order
