from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import tagged
from odoo import fields
from .common import Common


@tagged('-at_install', 'post_install')
class TestHrPayrollMeal(Common):

    def test_01_payroll_meal(self):
        """
        Case 1: Kiểm tra nhận diện suất ăn với phiếu lương
        - Input:
            + Tạo đơn đặt suất ăn.thời gian đặt suất ăn hợp lệ với phiếu lương ( cùng tháng), ở trạng thái dự/ từ chối bởi nhà bếp/ Huỷ
            + Tạo phiếu lương cho nhân viên, Thực hiện tính toán lại
        - Output: Tạo thành công phiếu lương, dòng đặt suất ăn không được nhận dịên vào phiếu lương
        """
        self.meal_order_1.write({'order_line_ids': [(0, 0, self.meal_line_admin_data)]})
        self.assertEqual(self.meal_order_1.state, 'draft')
        payslip_admin = self.env['hr.payslip'].with_context(tracking_disable=True).create(self.payslip_admin_data)
        payslip_admin.compute_sheet()
        self.assertFalse(payslip_admin.meal_order_line_ids)

        self.meal_order_1.write({'state': 'refused'})
        self.assertEqual(self.meal_order_1.state, 'refused')
        payslip_admin.compute_sheet()
        self.assertFalse(payslip_admin.meal_order_line_ids)

        self.meal_order_1.write({'state': 'cancelled'})
        self.assertEqual(self.meal_order_1.state, 'cancelled')
        payslip_admin.compute_sheet()
        self.assertFalse(payslip_admin.meal_order_line_ids)

    def test_02_payroll_meal(self):
        """
        Case 2: Kiểm tra nhận diện suất ăn với phiếu lương
        - Input:
            + Tạo đơn đặt suất ăn.thời gian đặt suất ăn hợp lệ với phiếu lương ( cùng tháng), ở trạng Đã xác nhận/ Đã phê duyệt
            + Tạo phiếu lương cho nhân viên, Thực hiện tính toán lại
        - Output: Tạo thành công phiếu lương, dòng đặt suất ăn được nhận dịên vào phiếu lương
        """
        self.meal_order_1.write({'order_line_ids': [(0, 0, self.meal_line_admin_data)], 'state': 'confirmed'})
        self.assertEqual(self.meal_order_1.state, 'confirmed')
        payslip_admin = self.env['hr.payslip'].with_context(tracking_disable=True).create(self.payslip_admin_data)
        payslip_admin.compute_sheet()
        self.assertTrue(payslip_admin.meal_order_line_ids)
        self.assertEqual(self.meal_order_1.order_line_ids, payslip_admin.meal_order_line_ids)

        self.meal_order_1.write({'state': 'approved'})
        payslip_admin.compute_sheet()
        self.assertTrue(payslip_admin.meal_order_line_ids)
        self.assertEqual(self.meal_order_1.order_line_ids, payslip_admin.meal_order_line_ids)

    def test_02_payroll_meal_13th(self):
        """
        Case 2: Kiểm tra nhận diện suất ăn với phiếu lương tháng 13
        - Input:
            + Tạo đơn đặt suất ăn.thời gian đặt suất ăn hợp lệ trong năm , ở trạng Đã xác nhận/ Đã phê duyệt
            + Tạo phiếu lương tháng 13 cho nhân viên, Thực hiện tính toán lại
        - Output: Tạo thành công phiếu lương tháng 13, dòng đặt suất ăn không được nhận diện vào phiếu lương
        """
        self.meal_order_1.write({'order_line_ids': [(0, 0, self.meal_line_admin_data)], 'state': 'confirmed'})
        self.assertEqual(self.meal_order_1.state, 'confirmed')
        today = fields.Date.today()
        payslip_13_admin = self.env['hr.payslip'].with_context(tracking_disable=True).create({
            'employee_id': self.employee_admin.id,
            'company_id': self.env.company.id,
            'salary_cycle_id': self.env.ref('to_hr_payroll.hr_salary_cycle_default').id,
            'thirteen_month_pay': True,
            'thirteen_month_pay_year': today.year,
            'date_from': fields.Date.start_of(today, 'year'),
            'date_to': fields.Date.end_of(today, 'year')
        })
        self.assertFalse(payslip_13_admin.meal_order_line_ids)
        payslip_13_admin.compute_sheet()
        self.assertFalse(payslip_13_admin.meal_order_line_ids)
        self.assertFalse(payslip_13_admin.line_ids.filtered(lambda r: r.code == 'MODED'))
        self.meal_order_1.write({'state': 'approved'})
        payslip_13_admin.compute_sheet()
        self.assertFalse(payslip_13_admin.meal_order_line_ids)
        self.assertFalse(payslip_13_admin.line_ids.filtered(lambda r: r.code == 'MODED'))

    def test_03_payroll_meal(self):
        """
        Case 3: Kiểm tra nhận diện suất ăn với phiếu lương
        - Input:
            + Tạo đơn đặt suất ăn.thời gian đặt suất ăn hợp lệ với phiếu lương ( cùng tháng), ở trạng Đã xác nhận/ Đã phê duyệt
            + Tạo phiếu lương cho nhân viên, Không ấn Tính toán lại
        - Output: Tạo thành công phiếu lương, dòng đặt suất ăn chưa được nhận dịên vào phiếu lương
        """
        self.meal_order_1.write({'order_line_ids': [(0, 0, self.meal_line_admin_data)], 'state': 'confirmed'})
        self.assertEqual(self.meal_order_1.state, 'confirmed')
        payslip_admin = self.env['hr.payslip'].with_context(tracking_disable=True).create(self.payslip_admin_data)
        self.assertFalse(payslip_admin.meal_order_line_ids)

    def test_04_payroll_meal(self):
        # Case 4: Huỷ đơn đặt suất ăn có dòng suất ăn liên kết với phiếu lương
        # - Input: Đơn đặt suất ăn ở trạng thái Đã xác nhận/ Đã phê duyệt có dòng suất ăn liên kết với phiếu lương
        # - Output: Huỷ thất bại -> Xảy ra ngoại lệ

        self.meal_order_1.write({'state': 'confirmed'})
        meal_order_line = self.env['hr.meal.order.line'].create({
            'employee_id': self.employee_admin.id,
            'quantity': 1,
            'price': 35000,
            'meal_order_id': self.meal_order_1.id,
            'meal_type_id': self.meal_type_1.id,
            'hr_payslip_id': self.payslip_admin.id
        })
        with self.assertRaises(ValidationError):
            self.meal_order_1.action_cancel()

        # Case 6: Xoá dòng đặt suất ăn đã liên kết đến phiếu lương
        # - Input: Lệnh đặt suất ăn, có dòng đặt suất ăn được liên kết đến phiếu lương, Xóa lệnh/dòng đặt suất ăn
        # - Output: Xoá thất bại. xảy ra ngoại lệ

        with self.assertRaises(ValidationError):
            meal_order_line.unlink()

    def test_05_payroll_meal(self):
        # Case 5: Huỷ đơn đặt suất ăn có dòng suất ăn chưa liên kết với phiếu lương
        # - Input: Đơn đặt suất ăn ở trạng thái Đã xác nhận/ Đã phê duyệt có dòng suất ăn chưa liên kết với phiếu lương
        # - Output: Huỷ thất bại -> Xảy ra ngoại lệ

        self.meal_order_1.write({'state': 'confirmed'})
        meal_order_line = self.env['hr.meal.order.line'].create({
            'employee_id': self.employee_admin.id,
            'quantity': 1,
            'price': 35000,
            'meal_order_id': self.meal_order_1.id,
            'meal_type_id': self.meal_type_1.id,
        })
        self.meal_order_1.action_cancel()

        # Case 7: Xoá dòng đặt suất ăn chưa liên kết đến phiếu lương
        # - Input: Lệnh đặt suất ăn, có dòng đặt suất ăn chưa được liên kết đến phiếu lương ở trạng thái Dự thảo, Xóa lệnh/dòng đặt suất ăn
        # - Output: Xoá thành công

        self.meal_order_1.write({'state': 'draft'})
        meal_order_line.unlink()

    def test_06_payroll_meal(self):
        """
        Case 8: Kiểm tra suất ăn trên phiếu lương
        - Input:
            + Phiếu lương của nhân viên
            + Suất ăn nằm trong khoảng thời gian của phiếu lương và suất ăn không nằm trong khoảng tgian của phiếu lương
        - Output:
            + Suất ăn nằm trong khoảng thời gian của phiếu lương sẽ được tính toán nhận diện vào phiếu lương
            + Suất ăn không nằm trong thời gian của phiếu lương sẽ không được tính toán vào phiếu lương
        """
        self.meal_order_1.write({'state': 'confirmed'})
        self.meal_order_2.write({'state': 'confirmed'})
        meal_order_line_1 = self.env['hr.meal.order.line'].create({
            'employee_id': self.employee_admin.id,
            'quantity': 1,
            'price': 35000,
            'meal_order_id': self.meal_order_1.id,
            'meal_type_id': self.meal_type_1.id,
        })
        meal_order_line_2 = self.env['hr.meal.order.line'].create({
            'employee_id': self.employee_admin.id,
            'quantity': 1,
            'price': 35000,
            'meal_order_id': self.meal_order_2.id,
            'meal_type_id': self.meal_type_1.id,
        })
        self.payslip_admin.compute_sheet()
        self.assertIn(meal_order_line_1, self.payslip_admin.meal_order_line_ids)
        self.assertNotIn(meal_order_line_2, self.payslip_admin.meal_order_line_ids)

    def test_07_payroll_meal(self):
        """
        Case 9: Kiểm tra tổng khấu trừ đặt suất ăn trên phiếu lương
        - Input:
            + Suất ăn nằm trong khoảng thời gian của phiếu lương , tổng nhân viên phải trả là 30000
            + Tạo phiếu lương cho nhân viên, thực hiện tính toán phiếu lương
        - Output:
            + Trên phiếu lương tổng khấu trừ suất ăn là -30000
        """
        meal_order_line_1 = self.env['hr.meal.order.line'].create({
            'employee_id': self.employee_admin.id,
            'quantity': 1,
            'price': 35000,
            'meal_order_id': self.meal_order_1.id,
            'meal_type_id': self.meal_type_1.id,
        })
        self.meal_order_1.write({'state': 'confirmed'})
        self.assertEqual(meal_order_line_1.employee_price, 30000.0)

        self.payslip_admin.compute_sheet()
        self.assertIn(meal_order_line_1, self.payslip_admin.meal_order_line_ids)
        meal_deduction_amount = self.payslip_admin.line_ids.filtered(lambda l: l.code == 'MODED')[:1]
        self.assertEqual(meal_deduction_amount.amount, -30000)

    def test_08_payroll_meal(self):
        """
        Case 10: Huỷ phiếu lương khi có dòng suất ăn đang liên kết tới phiếu lương
        - Input:
            + Phiếu lương cho nhân viên ở trạng thái Xác nhận, có dòng suất ăn
            + Thực hiện huỷ phiếu lương
        - Output:
            + Huỷ thành công, các dòng đặt suất ăn không còn tham chiếu tới phiếu lương
        """
        self.meal_order_1.write({'state': 'confirmed'})
        meal_order_line_1 = self.env['hr.meal.order.line'].create({
            'employee_id': self.employee_admin.id,
            'quantity': 1,
            'price': 35000,
            'meal_order_id': self.meal_order_1.id,
            'meal_type_id': self.meal_type_1.id,
        })
        self.payslip_admin.compute_sheet()
        self.assertIn(meal_order_line_1, self.payslip_admin.meal_order_line_ids)
        self.payslip_admin.action_payslip_verify()
        self.assertEqual(self.payslip_admin.state, 'verify')
        self.payslip_admin.action_payslip_cancel()
        self.assertEqual(self.payslip_admin.state, 'cancel')
        self.assertNotIn(meal_order_line_1, self.payslip_admin.meal_order_line_ids)

    def test_09_payroll_meal(self):
        """
        Case 11: Tạo suất ăn cho nhân viên trong khoảng thời gian phiếu lương của nhân viên đó đã được xác nhận
        - Input:
            + Phiếu lương cho nhân viên ở trạng thái Xác nhận
            + Thực hiện tạo suất ăn cho nhân viên trong khoảng thời gian phiếu lương
        - Output:
            + Tạo thất bại -> xảy ra ngoại lệ
        """
        self.payslip_admin.action_payslip_verify()
        with self.assertRaises(UserError):
            self.env['hr.meal.order.line'].create({
                'employee_id': self.employee_admin.id,
                'quantity': 1,
                'price': 35000,
                'meal_order_id': self.meal_order_1.id,
                'meal_type_id': self.meal_type_1.id,
            })

    def test_10_payroll_meal(self):
        """
        Case 12: Xác nhận suất ăn cho nhân viên trong khoảng thời gian phiếu lương của nhân viên đó đã được xác nhận
        - Input:
            + Phiếu lương cho nhân viên ở trạng thái Xác nhận
            + Thực hiện xác nhận đơn đặt cho nhân viên trong khoảng thời gian phiếu lương
        - Output:
            + Xác nhận thất bại -> xảy ra ngoại lệ
        """
        meal_order_line = self.env['hr.meal.order.line'].create({
                'employee_id': self.employee_admin.id,
                'quantity': 1,
                'price': 35000,
                'meal_order_id': self.meal_order_1.id,
                'meal_type_id': self.meal_type_1.id,
        })
        self.assertIn(meal_order_line, self.meal_order_1.order_line_ids)
        self.payslip_admin.action_payslip_verify()
        with self.assertRaises(UserError):
            self.meal_order_1.action_confirm()
