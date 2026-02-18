from odoo.tests import tagged
from odoo.exceptions import AccessError

from .common import TestCommon


@tagged('post_install', '-at_install')
class TestSecurity(TestCommon):

    def test_01_internal_user_right(self):
        """
        Test: Internal users only have permission to read relative information
        """
        relative_father_a = self.env['hr.employee.relative'].create({
            'employee_id': self.employee_a.id,
            'contact_id': self.partner_1.id,
            'type': 'wife'
        })
        relative_father_a.with_user(self.internal_user).check_access_rule('read')
        EmployeeRelative = self.env['hr.employee.relative'].with_user(self.internal_user)
        with self.assertRaises(AccessError):
            EmployeeRelative.check_access_rights('create')
        with self.assertRaises(AccessError):
            EmployeeRelative.check_access_rights('write')
        with self.assertRaises(AccessError):
            EmployeeRelative.check_access_rights('unlink')

    def test_02_hr_user_right(self):
        """
        Test: HR users have full permission (read, create, write, unlink)
        """
        relative_father_a = self.env['hr.employee.relative'].create({
            'employee_id': self.employee_a.id,
            'contact_id': self.partner_1.id,
            'type': 'wife'
        })
        relative_father_a.with_user(self.hr_user).check_access_rule('read')
        relative_father_a.with_user(self.hr_user).write({
            'employee_id': self.employee_b.id
        })
        relative_father_a.with_user(self.hr_user).unlink()
        self.env['hr.employee.relative'].with_user(self.hr_user).create({
            'employee_id': self.employee_a.id,
            'contact_id': self.partner_3.id,
            'type': 'mother'
        })
