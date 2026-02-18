from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged
from odoo.tools.misc import mute_logger
from .test_hr_meal_common import TestHrMealCommon


@tagged('post_install', '-at_install')
class TestToHrMeal(TestHrMealCommon):

    def setUp(self):
        super(TestToHrMeal, self).setUp()
        Department = self.env['hr.department'].with_context(tracking_disable=True)
        self.department_1 = Department.create({
            'name': 'department 1',
            'member_ids': [(6, 0, [self.employee_1.id, self.employee_2.id])]
        })
        self.department_2 = Department.create({
            'name': 'department 2',
        })
        self.department_3 = Department.create({
            'name': 'department 3',
            'parent_id': self.department_2.id,
            'member_ids': [(6, 0, [self.employee_3.id, self.employee_4.id])]
        })
        self.department_4 = Department.create({
            'name': 'department 4',
            'parent_id': self.department_2.id,
            'member_ids': [(6, 0, [self.employee_5.id])]
        })
        self.meal_order_1 = self.create_meal_order(self.meal_type_lunch, 'internal', [self.employee_1, self.employee_2])

    def test_01_meal_type_unique_name(self):
        """
        Test: Trùng lặp tên kiểu suất ăn
        Input:
            - Đã có kiểu suất ăn tên 'Lunch for Everyone'
            - Tạo kiểu suất ăn mới tên 'Lunch for Everyone'
        Output:
            - Ngoại lệ
        """
        self.assertEqual(self.env.ref('to_hr_meal.hr_meal_type_lunch_for_everyone').name, 'Lunch for Everyone')
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['hr.meal.type'].create({
                'name': 'Lunch for Everyone'
            })

    def test_02_scheduled_hour_check(self):
        """
        Test: Giờ đặt bữa ăn không hợp lệ (nằm ngoài khoảng 0 -> 23)
        """
        # scheduled_hour_check_positive
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['hr.meal.order'].create({
                'meal_type_id': self.meal_type_lunch.id,
                'scheduled_hour': -1
            })
        # scheduled_hour_check_less_than_24
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['hr.meal.order'].create({
                'meal_type_id': self.meal_type_lunch.id,
                'scheduled_hour': 24
            })

    def test_04_compute_partners_count(self):
        """
        Test _compute_partners_count: số lượng đối tác của đơn suất ăn
        Input:
            Đơn suất ăn:
                - dòng 1: 1 đối tác
                - dòng 2: 2 đối tác
        Output: Đơn suất ăn có tổng 3 đối tác
        """
        self.meal_order_1.order_line_ids[0].partner_ids = self.env.ref('base.res_partner_1')
        self.meal_order_1.order_line_ids[1].partner_ids = self.env.ref('base.res_partner_2') | self.env.ref('base.res_partner_3')
        self.assertEqual(self.meal_order_1.partners_count, 3)

    def test_05_compute_order_lines_count(self):
        """
        Test _compute_order_lines_count: tổng số dòng suất ăn
        Input:
            - Đơn suất ăn: có 2 dòng suất ăn
            - xóa 1 dòng suất ăn
        Output: Đơn suất ăn có tổng 1 dòng
        """
        self.assertEqual(self.meal_order_1.order_lines_count, 2)
        self.meal_order_1.order_line_ids[0].unlink()
        self.assertEqual(self.meal_order_1.order_lines_count, 1)

    def test_06_compute_scheduled_hour(self):
        """
        Test compute_scheduled_hour: Giờ suất ăn được lấy theo kiểu suất ăn
        """
        self.meal_type_lunch.scheduled_hour = 11
        self.meal_order_1.meal_type_id = self.meal_type_lunch
        self.assertEqual(self.meal_order_1.scheduled_hour, 11)

    def test_07_compute_total_01(self):
        """
        Test _compute_total: Tổng suất ăn và giá tiền của dòng suất ăn và đơn suất ăn
        Input:
            - Đơn suất ăn có 2 dòng suất ăn, các dòng chưa có đối tác => 2 suất, giá mỗi suất là 10$
            - Thêm 2 đối tác vào dòng suất ăn 1
        Output:
            - Dòng suất ăn 1: 3 suất => 30$
            - Đơn suất ăn: 4 suất => 40$
        """
        self.assertEqual(self.meal_order_1.total_qty, 2)
        self.assertEqual(self.meal_order_1.total_price, 20)

        self.meal_order_1.order_line_ids[0].partner_ids = self.env.ref('base.res_partner_1') + self.env.ref('base.res_partner_2')
        self.assertEqual(self.meal_order_1.order_line_ids[0].quantity, 3)
        self.assertEqual(self.meal_order_1.order_line_ids[0].total_price, 30)
        self.assertEqual(self.meal_order_1.total_qty, 4)
        self.assertEqual(self.meal_order_1.total_price, 40)

    def test_08_compute_applied_department_ids(self):
        """
        Test _compute_applied_department_ids: Tất cả phòng ban liên quan đến nhân viên đặt suất ăn
        """
        meal_order = Form(self.env['hr.meal.order'])
        meal_order.meal_type_id = self.meal_type_dinner
        meal_order.load_employee = 'load_all'
        meal_order = meal_order.save()
        self.assertEqual(meal_order.order_line_ids.department_id, meal_order.applied_department_ids)

    def test_09_onchange_department_id_01(self):
        """
        Tets _onchange_department_id: tất cả dòng suất ăn đều thuộc về phòng ban được chọn
        """
        meal_order = Form(self.env['hr.meal.order'])
        meal_order.meal_type_id = self.meal_type_dinner
        meal_order.department_id = self.department_1
        meal_order = meal_order.save()

        self.assertTrue(meal_order.order_line_ids.employee_id == self.department_1.member_ids)

    def test_09_onchange_department_id_02(self):
        """
        Tets _onchange_department_id: tất cả dòng suất ăn đều thuộc về phòng ban được chọn (bao gồm cả phòng ban cấp dưới)
        Choose a department that have lower-level department
        Expected result : Show all employees which belong to that department
        EX : Department BOD have 2 lower-level department
        (BOD/Marketing - 10 employees and BOD/Technical - 5 employees)
        The total employees should be 10 + 5 = 15
        """
        meal_order = Form(self.env['hr.meal.order'])
        meal_order.meal_type_id = self.meal_type_dinner
        meal_order.department_id = self.department_2
        meal_order = meal_order.save()

        self.assertEqual(meal_order.order_line_ids.employee_id, self.department_3.member_ids | self.department_4.member_ids)

    def test_10_onchange_load_employee(self):
        """
        Test _onchange_load_employee: Xóa tất cả dòng suất ăn cho nhân viên
        """
        meal_order = Form(self.env['hr.meal.order'])
        meal_order.meal_type_id = self.meal_type_dinner
        with meal_order.order_line_ids.new() as line:
            line.employee_id = self.employee_1
        meal_order.load_employee = 'clear_all'

        meal_order = meal_order.save()
        self.assertEqual(len(meal_order.order_line_ids), 0)

    def test_11_action_confirm_01(self):
        """
        Test: Xác nhận suất ăn không có dòng suất ăn nào không thành công
        """
        self.meal_order_1.order_line_ids = False
        with self.assertRaises(UserError):
            self.meal_order_1.action_confirm()

    def test_11_action_confirm_02(self):
        """
        Test: Xác nhận suất ăn khác trạng thái dự thảo không thành công
        """
        with self.assertRaises(UserError):
            self.meal_order_1.state = 'confirmed'
            self.meal_order_1.action_confirm()
        with self.assertRaises(UserError):
            self.meal_order_1.state = 'approved'
            self.meal_order_1.action_confirm()
        with self.assertRaises(UserError):
            self.meal_order_1.state = 'refused'
            self.meal_order_1.action_confirm()
        with self.assertRaises(UserError):
            self.meal_order_1.state = 'cancelled'
            self.meal_order_1.action_confirm()

    def test_11_action_confirm_03(self):
        """
        Test: Xác nhận suất ăn dự thảo thành công
        """
        self.meal_order_1.action_confirm()
        self.assertEqual(self.meal_order_1.state, 'confirmed')

    def test_12_action_approve_01(self):
        """
        Test: Phê duyệt suất ăn khác trạng thái đã xác nhận không thành công
        """
        with self.assertRaises(UserError):
            self.meal_order_1.action_approve()
        with self.assertRaises(UserError):
            self.meal_order_1.state = 'approved'
            self.meal_order_1.action_approve()
        with self.assertRaises(UserError):
            self.meal_order_1.state = 'refused'
            self.meal_order_1.action_approve()
        with self.assertRaises(UserError):
            self.meal_order_1.state = 'cancelled'
            self.meal_order_1.action_approve()

    def test_12_action_approve_02(self):
        """
        Test: Nhóm người dùng có thể phê duyệt suất ăn ở trạng thái đã xác nhận
        Input:
            - Suất ăn đã được xác nhận
            1. Người dùng suất ăn phê duyệt
            2. Quản lý suất ăn phê duyệt
        Output:
            1. Phê duyệt không thành công
            2. Phê duyệt không thành công
        """
        self.meal_order_1.state = 'confirmed'
        # 1.
        with self.assertRaises(UserError):
            self.meal_order_1.with_user(self.user_meal_user).action_approve()
        # 2.
        self.meal_order_1.with_user(self.user_meal_manager).action_approve()

    def test_13_action_confirm_approve_01(self):
        """
        Test: Suất ăn Tự động được phê duyệt khi xác nhận bởi người phụ trách nhà bếp
        Input:
            - Nguồn suất ăn: nội bộ
            - Người xác nhận là người phụ trách của nhà bếp
        Output:
            - Xác nhận thành công, tự động phê duyệt
        """
        self.meal_order_1.order_source = 'internal'
        self.meal_order_1.kitchen_id = self.kitchen
        self.meal_order_1.with_user(self.user_meal_user_responsible).action_confirm()

        self.assertEqual(self.meal_order_1.state, 'approved')

    def test_13_action_confirm_approve_02(self):
        """
        Test: Suất ăn Tự động được phê duyệt khi xác nhận bởi người phụ trách nhà bếp
        Input:
            - Nguồn suất ăn: bên ngoài
            - Người xác nhận là đối tác suất ăn được thiết lập trên đơn suất ăn
        Output:
            - Xác nhận thành công, tự động phê duyệt
        """
        self.meal_order_1.order_source = 'external'
        self.meal_order_1.vendor_id = self.user_meal_user.partner_id
        self.meal_order_1.with_user(self.user_meal_user).action_confirm()

        self.assertEqual(self.meal_order_1.state, 'approved')

    def test_14_action_refuse_01(self):
        """
        Test: Từ chối suất ăn
        Input:
            - Suất ăn được xác nhận
            1. Người dùng suất ăn từ chối
            2. quản lý suất ăn từ chối
        Ouput:
            1. Từ chối không thành công
            2. Từ chối thành công
        """
        self.meal_order_1.action_confirm()
        # 1.
        with self.assertRaises(UserError):
            self.meal_order_1.with_user(self.user_meal_user).action_refuse()
        # 2.
        self.meal_order_1.with_user(self.user_meal_manager).action_refuse()

    def test_14_action_refuse_02(self):
        """
        Test: Từ chối suất ăn ở trạng thái khác 'đã xác nhận' không thành công
        Input:
            - Từ chối xuất ăn ở trạng thái dự thảo
            - Từ chối xuất ăn ở trạng thái được phê duyệt
            - Từ chối xuất ăn ở trạng thái đã từ chối
        Ouput:
            - Từ chối không thành công
        """
        with self.assertRaises(UserError):
            self.meal_order_1.with_user(self.user_meal_manager).action_refuse()
        with self.assertRaises(UserError):
            self.meal_order_1.action_confirm()
            self.meal_order_1.action_approve()
            self.meal_order_1.with_user(self.user_meal_manager).action_refuse()
        with self.assertRaises(UserError):
            self.meal_order_1.action_confirm()
            self.meal_order_1.action_refuse()
            self.meal_order_1.with_user(self.user_meal_manager).action_refuse()

    def test_15_action_cancel_01(self):
        """
        Test: Hủy suất ăn
        Input:
            1. Suất ăn dự thảo
            2. Suất ăn được xác nhận
            3. Suất ăn đã bị hủy
        Output:
            1 & 3: hủy không thành công
            2. hủy thành công
        """
        # 1.
        with self.assertRaises(UserError):
            self.meal_order_1.action_cancel()
        # 2.
        self.meal_order_1.action_confirm()
        self.meal_order_1.action_cancel()
        self.assertEqual(self.meal_order_1.state, 'cancelled')
        # 3.
        with self.assertRaises(UserError):
            self.meal_order_1.action_cancel()

    def test_15_action_cancel_02(self):
        """
        Test: Hủy lệnh suất ăn ở trạng thái phê duyệt
        Input:
            - Suất ăn đã được phê duyệt
            1. Người dùng suất ăn hủy suất ăn
            2. Quản lý suất ăn hủy suất ăn
        Output:
            1. Hủy không thành công
            2. Hủy thành công
        """
        self.meal_order_1.state = 'approved'
        # 1.
        with self.assertRaises(UserError):
            self.meal_order_1.with_user(self.user_meal_user).action_cancel()
        # 2.
        self.meal_order_1.with_user(self.user_meal_manager).action_cancel()
        self.assertEqual(self.meal_order_1.state, 'cancelled')

    def test_16_unlink_01(self):
        """
        Test: Xóa lệnh suất ăn không phải trong trạng thái dự thảo không thành công
        Input:
            - Xác nhận suất ăn -> Xóa xuất ăn
            - Xác nhận suất ăn -> phê duyệt -> Xóa xuất ăn
            - Hủy suất ăn -> Xóa xuất ăn
        Output:
            - Xóa không thành công
        """
        with self.assertRaises(UserError):
            self.meal_order_1.action_confirm()
            self.meal_order_1.unlink()
        with self.assertRaises(UserError):
            self.meal_order_1.action_confirm()
            self.meal_order_1.action_approve()
            self.meal_order_1.unlink()
        with self.assertRaises(UserError):
            self.meal_order_1.action_cancel()
            self.meal_order_1.unlink()

    def test_17_unlink_02(self):
        """
        Test: Xóa lệnh suất ăn dự thảo thành công
        Input:
            - Xóa xuất ăn ở trạng thái dự thảo
        Output:
            - Xóa thành công
        """
        self.meal_order_1.unlink()
        self.assertFalse(bool(self.meal_order_1.exists()))

    def test_18_compute_total_price(self):
        """
        Test compute_total_price: tổng số tiền = Số lượng * đơn giá
        """
        self.meal_order_1.order_line_ids[0].write({
            'price': 20000,
            'quantity': 3
        })
        self.assertEqual(self.meal_order_1.order_line_ids[0].total_price, 60000)

    def test_19_compute_price(self):
        """
        Test _compute_price: Đơn giá lấy theo giá của kiểu suất ăn
        """
        self.meal_type_lunch.price = 20000
        self.meal_order_1.meal_type_id = self.meal_type_lunch
        self.assertEqual(self.meal_order_1.order_line_ids[0].price, 20000)

    def test_20_compute_department(self):
        """
        Test _compute_department: Phòng ban mặc định lấy theo nhân viên
        """
        for line in self.meal_order_1.order_line_ids:
            self.assertEqual(line.department_id, line.employee_id.department_id)

    def test_21_overlap_meal_order_lines(self):
        """
        Test constrains_employee_id_and_meal_date: trùng thời gian suất ăn của nhân viên
        => Xác nhận không thành công
        """
        meal_order_1 = self.create_meal_order(self.meal_type_lunch, 'external', [self.employee_1, self.employee_2])
        meal_order_2 = self.create_meal_order(self.meal_type_lunch, 'external', [self.employee_1])
        meal_order_3 = self.create_meal_order(self.meal_type_dinner, 'external', [self.employee_1, self.employee_1])

        with self.assertRaises(ValidationError), self.cr.savepoint():
            meal_order_1.action_confirm()
            meal_order_1.flush_recordset()
            meal_order_2.action_confirm()
            meal_order_2.flush_recordset()

        with self.assertRaises(ValidationError), self.cr.savepoint():
            meal_order_3.with_user(self.user_meal_manager).action_confirm()

    def test_22_employee_price_01(self):
        """
        Test: Giá suất ăn của nhân viên không áp dụng theo giá suất ăn trên công ty
        Input:
            - Giá trên kiểu suất ăn: 45$
            - Không dáp dụng giá suất ăn nhân viên trên công ty:
            - Lệnh suất ăn với 2 dòng suất ăn cho 2 nhân viên
        Output:
            - Giá suất ăn nhân viên phải trả là 45$
            - Tổng giá tiền suất ăn là: 2 suất * 45$ = 90$
            - Tổng số tiền nhân viên phải trả là 2 suất * 45$ = 90$
            - Tổng số tiền công ty phải trả là 90$ - 90$ = 0$
        """
        self.meal_type_dinner.price = 45.0
        self.assertFalse(self.env.company.set_meal_employee_price)
        self.meal_order_1.meal_type_id = self.meal_type_dinner

        self.assertRecordValues(
            self.meal_order_1.order_line_ids,
            [{
                'quantity': 1,
                'price': 45.0,
                'total_price': 45.0,
                'employee_price': 45.0,
                'employee_amount': 45.0,
                'company_amount': 0.0
            },
            {
                'quantity': 1,
                'price': 45.0,
                'total_price': 45.0,
                'employee_price': 45.0,
                'employee_amount': 45.0,
                'company_amount': 0.0
            }])
        self.assertRecordValues(
            self.meal_order_1,
            [{
                'total_price': 90.0,
                'total_employee_pay': 90.0,
                'total_company_pay': 0.0
            }])

    def test_22_employee_price_02(self):
        """
        Test: Giá suất ăn của nhân viên là giá trị nhỏ nhất giữa giá trênkiểu suất ăn và giá tiền nhân viên trả trên công ty
        Input:
            - Giá trên kiểu suất ăn: 45$
            - Ap dụng giá suất ăn nhân viên và đặt giá trị là 0$ trên công ty
            - Lệnh suất ăn với 2 dòng suất ăn cho 2 nhân viên
        Output:
            - Giá suất ăn nhân viên phải trả là 0$
            - Tổng giá tiền suất ăn là: 2 suất * 45$ = 90$
            - Tổng số tiền nhân viên phải trả là 2 suất * 0$ = 0$
            - Tổng số tiền công ty phải trả là 90$ - 0$ = 90$
        """
        self.meal_type_dinner.price = 45.0
        self.env.company.write({
            'set_meal_employee_price': True,
            'meal_emp_price': 0.0
        })
        self.meal_order_1.meal_type_id = self.meal_type_dinner

        self.assertRecordValues(
            self.meal_order_1.order_line_ids,
            [{
                'quantity': 1,
                'price': 45.0,
                'total_price': 45.0,
                'employee_price': 0.0,
                'employee_amount': 0.0,
                'company_amount': 45.0
            },
            {
                'quantity': 1,
                'price': 45.0,
                'total_price': 45.0,
                'employee_price': 0.0,
                'employee_amount': 0.0,
                'company_amount': 45.0
            }])
        self.assertRecordValues(
            self.meal_order_1,
            [{
                'total_price': 90.0,
                'total_employee_pay': 0.0,
                'total_company_pay': 90.0
            }])

    def test_22_employee_price_03(self):
        """
        Test: Giá suất ăn của nhân viên là giá trị nhỏ nhất giữa giá trênkiểu suất ăn và giá tiền nhân viên trả trên công ty
        Input:
            - Giá trên kiểu suất ăn: 45$
            - Ap dụng giá suất ăn nhân viên và đặt giá trị là 25$ trên công ty
            - Lệnh suất ăn với 2 dòng suất ăn cho 2 nhân viên
        Output:
            - Giá suất ăn nhân viên phải trả là 25$
            - Tổng giá tiền suất ăn là: 2 suất * 45$ = 90$
            - Tổng số tiền nhân viên phải trả là 2 suất * 25$ = 50$
            - Tổng số tiền công ty phải trả là 90$ - 50$ = 40$
        """
        self.meal_type_dinner.price = 45.0
        self.env.company.write({
            'set_meal_employee_price': True,
            'meal_emp_price': 25.0
        })
        self.meal_order_1.meal_type_id = self.meal_type_dinner

        self.assertRecordValues(
            self.meal_order_1.order_line_ids,
            [{
                'quantity': 1,
                'price': 45.0,
                'total_price': 45.0,
                'employee_price': 25.0,
                'employee_amount': 25.0,
                'company_amount': 20.0
            },
            {
                'quantity': 1,
                'price': 45.0,
                'total_price': 45.0,
                'employee_price': 25.0,
                'employee_amount': 25.0,
                'company_amount': 20.0
            }])
        self.assertRecordValues(
            self.meal_order_1,
            [{
                'total_price': 90.0,
                'total_employee_pay': 50.0,
                'total_company_pay': 40.0
            }])

    def test_22_employee_price_04(self):
        """
        Test: Giá suất ăn của nhân viên là giá trị nhỏ nhất giữa giá trênkiểu suất ăn và giá tiền nhân viên trả trên công ty
        Input:
            - Giá trên kiểu suất ăn: 45$
            - Ap dụng giá suất ăn nhân viên và đặt giá trị là 55$ trên công ty
            - Lệnh suất ăn với 2 dòng suất ăn cho 2 nhân viên
        Output:
            - Giá suất ăn nhân viên phải trả là 45$
            - Tổng giá tiền suất ăn là: 2 suất * 45$ = 90$
            - Tổng số tiền nhân viên phải trả là 2 suất * 45$ = 90$
            - Tổng số tiền công ty phải trả là 90$ - 90$ = 00$
        """
        self.meal_type_dinner.price = 45.0
        self.env.company.write({
            'set_meal_employee_price': True,
            'meal_emp_price': 55.0
        })
        self.meal_order_1.meal_type_id = self.meal_type_dinner

        self.assertRecordValues(
            self.meal_order_1.order_line_ids,
            [{
                'quantity': 1,
                'price': 45.0,
                'total_price': 45.0,
                'employee_price': 45.0,
                'employee_amount': 45.0,
                'company_amount': 0.0
            },
            {
                'quantity': 1,
                'price': 45.0,
                'total_price': 45.0,
                'employee_price': 45.0,
                'employee_amount': 45.0,
                'company_amount': 0.0
            }])
        self.assertRecordValues(
            self.meal_order_1,
            [{
                'total_price': 90.0,
                'total_employee_pay': 90.0,
                'total_company_pay': 0.0
            }])
