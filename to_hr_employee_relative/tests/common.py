from odoo.tests.common import TransactionCase


class TestCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestCommon, cls).setUpClass()

        # Users
        ResUsers = cls.env['res.users'].with_context({'no_reset_password': True})
        cls.internal_user = ResUsers.create({
            'name': 'Internal User',
            'login': 'internal_user',
            'email': 'internal_user@example.viindoo.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        cls.hr_user = ResUsers.create({
            'name': 'Hr User ',
            'login': 'hr_user',
            'email': 'hr_user@example.viindoo.com',
            'groups_id': [(6, 0, [cls.env.ref('hr.group_hr_user').id])]
        })

        # Partners
        cls.partner_1 = cls.env.ref('base.res_partner_address_32')
        cls.partner_2 = cls.env.ref('base.res_partner_address_1')
        cls.partner_3 = cls.env.ref('base.res_partner_address_31')

        # Employees
        cls.employee_a = cls.env.ref('hr.employee_admin')
        cls.employee_b = cls.env.ref('hr.employee_niv')
