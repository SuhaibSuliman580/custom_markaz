from odoo.tests import tagged
from odoo.tools.misc import mute_logger
from odoo.exceptions import UserError

try:
    # try to use UniqueViolation if psycopg2's version >= 2.8
    from psycopg2 import errors
    UniqueViolation = errors.UniqueViolation
except Exception:
    import psycopg2
    UniqueViolation = psycopg2.IntegrityError

from .common import TestCommon


@tagged('post_install', '-at_install')
class HrEmployeeRelative(TestCommon):

    @mute_logger('odoo.sql_db')
    def test_01_employee_relative_duplicate(self):
        """
        Test employee_contact_unique: ràng buộc mỗi người thân là duy nhất trên nhân viên
        Input:
            - nhân viên a chưa có người thân
            - 1. Tạo người thân, liên kết đến liên hệ 1
            - 2. Tiếp tục tạo người thân bằng liên hệ 1
        Ouput:
            1. Tạo thành công
            2. Ngoại lệ.
        """
        # 1.
        self.env['hr.employee.relative'].create({
            'employee_id': self.employee_a.id,
            'contact_id': self.partner_1.id,
            'type': 'father'
            })
        # 2.
        with self.assertRaises(UniqueViolation):
            self.relative_a = self.env['hr.employee.relative'].create({
                'employee_id': self.employee_a.id,
                'contact_id': self.partner_1.id,
                'type': 'friend',
                })

    def test_02_partner_01(self):
        """
        Test: thông tin của đối tác khi được thiết lập làm người thân của nhân viên
        Input:
            1. đối tác 1: chưa làm người thân của nhân viên nào
            2. Thiết lập làm người thân của nhân viên a
            3. thiết lập làm người thân của nhân viên a & nhân viên b
        Output:
            1. các thông tin liên quan dến người thân là False
            2. có thông tin người thân là nhân viên a
            3. Có thông tin người thân là nhân viên a và b
        """
        # 1.
        self.assertFalse(self.partner_1.is_employee_relative)
        self.assertFalse(self.partner_1.relative_employee_ids)
        self.assertFalse(self.partner_1.employee_relative_ids)
        # 2.
        relative_wife_a = self.env['hr.employee.relative'].create({
            'employee_id': self.employee_a.id,
            'contact_id': self.partner_1.id,
            'type': 'wife'
        })
        self.assertTrue(self.partner_1.is_employee_relative)
        self.assertEqual(self.partner_1.relative_employee_ids, self.employee_a)
        self.assertEqual(self.partner_1.employee_relative_ids, relative_wife_a)
        # 3.
        relative_father_b = self.env['hr.employee.relative'].create({
            'employee_id': self.employee_b.id,
            'contact_id': self.partner_1.id,
            'type': 'father'
        })
        self.assertTrue(self.partner_1.is_employee_relative)
        self.assertEqual(self.partner_1.relative_employee_ids, self.employee_a | self.employee_b)
        self.assertEqual(self.partner_1.employee_relative_ids, relative_wife_a | relative_father_b)

    def test_02_partner_02(self):
        """
        Test: Chỉ nhóm quyền Cán bộ nhân sự mới có thể xóa thông tin liên hệ được đánh dấu là người thân nhân viên
        Input:
            - Liên hệ 1 là người thân của nhân viên a
            1. Người dùng không phải cán bộ nhân sự, là quản lý liên hệ. Xóa liên hệ 1
            2. cán bộ nhân sự và là quản lý liên hệ xóa liên hệ 1
        Output:
            1. Ngoại lệ
            2. xóa thành công
        """
        relative_father_a = self.env['hr.employee.relative'].create({
            'employee_id': self.employee_a.id,
            'contact_id': self.partner_1.id,
            'type': 'wife'
        })
        self.assertEqual(self.employee_a.relative_ids, relative_father_a)
        # 1. Ngoại lệ
        self.internal_user.write({
            'groups_id': [(6, 0, [self.env.ref('base.group_partner_manager').id])]
        })
        with self.assertRaises(UserError):
            self.partner_1.with_user(self.internal_user).unlink()
        # 2. Xóa thành công
        self.hr_user.write({
            'groups_id': [(4, self.env.ref('base.group_partner_manager').id)]
        })
        self.partner_1.with_user(self.hr_user).unlink()
        self.assertFalse(self.employee_a.relative_ids)

    def test_03_employee_01(self):
        """
        Test thông tin vợ/chồng, đã kết hôn, ràng buộc trên nhân viên
        (_compute_marital & _compute_spouse_name & _check_marital_partner)
        Input:
            - Nhân viên a chưa có thông tin người thân, chưa đánh dấu kết hôn, chưa có thông tin vợ chồng
            1. Thêm 1 người thân đánh dấu là vợ/chồng
            2. Thêm 1 người thân đánh dấu là chồng/vợ
            3. Xóa thông tin người thân của nhân viên
        Ouput:
            1. Nhân viên: thông tin kết hôn, tên vợ/chồng được cập nhật tự động
            2. Ngoại lệ
            3. Tên vơ/chồng, thông tin kết hôn giữ nguyên
        """
        self.employee_a.write({'marital': False})
        self.assertFalse(self.employee_a.spouse_complete_name)
        # 1.Nhân viên: thông tin kết hôn, tên vợ/chồng được cập nhật tự động
        self.env['hr.employee.relative'].create({
            'employee_id': self.employee_a.id,
            'contact_id': self.partner_1.id,
            'type': 'wife'
        })
        self.assertTrue(self.employee_a.marital)
        self.assertEqual(self.employee_a.spouse_complete_name, self.partner_1.name)
        # 2.Ngoại lệ
        with self.assertRaises(UserError):
            self.env['hr.employee.relative'].create({
                'employee_id': self.employee_a.id,
                'contact_id': self.partner_2.id,
                'type': 'husband'
            })
        # 3. Tên vơ/chồng, thông tin kết hôn giữ nguyên
        self.employee_a.relative_ids.unlink()
        self.assertTrue(self.employee_a.marital)
        self.assertEqual(self.employee_a.spouse_complete_name, self.partner_1.name)

    def test_03_employee_02(self):
        """
        Test: Số lượng phụ thuộc của nhân viên
        Input:
            - nhân viên a chưa có người thân
            - thêm 1 người thân là vơ/chồng
            - thêm 1 người thân là con cái, có đánh dấu phụ thuộc
            - Thêm 1 người thân là bố/mẹ, có đánh dấu phụ thuộc
        Ouput:
            - số lượng con cái phụ thuộc: 1
            - Số lượng phụ thuộc khác: 1
            - Tổng phụ thuộc: 2
        """
        self.env['hr.employee.relative'].create([
            {
                'employee_id': self.employee_a.id,
                'contact_id': self.partner_1.id,
                'type': 'wife'
            },
            {
                'employee_id': self.employee_a.id,
                'contact_id': self.partner_3.id,
                'type': 'children',
                'is_dependant': True
            },
            {
                'employee_id': self.employee_a.id,
                'contact_id': self.partner_2.id,
                'type': 'father',
                'is_dependant': True
            }
        ])
        self.assertRecordValues(
            self.employee_a,
            [{
                'children': 1,
                'other_dependant': 1,
                'total_dependant': 2
            }])
