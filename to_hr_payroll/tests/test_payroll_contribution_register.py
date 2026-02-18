from odoo import fields
from odoo.exceptions import ValidationError, UserError
from odoo.tests import Form, tagged

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollContributionRegister(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollContributionRegister, cls).setUpClass()
        cls.type = cls.env['hr.payroll.contribution.type'].search([('company_id', '=', cls.env.company.id)], limit=1)

    # 6. Form Đăng ký đóng góp từ lương
    def test_form_change_type_id(self):
        """
        Case 1: Test Thông tin Đăng ký đóng góp từ lương thay đổi khi thay đổi trường Kiểu đóng góp
            TH1: Chọn 1 Kiểu đóng góp
                Ouput: Các thông tin sau sẽ được lấy giống với kiểu đóng góp:
                    Số sô ngày trong tháng
                    Khối tính toán
                    Phương pháp tính toán
                    Số ngày không hưởng lương
                    Tỷ lệ đóng góp của nhân viên
                    Tỷ lệ đóng góp của công ty

            TH2: Xóa kiểu đóng góp / Giá trị mạc định khi mở form
                Output: Các thông tin sau sẽ có giá trị mặc định:
                    Số sô ngày trong tháng là Cố định 28 ngày
                    Khối tính toán là Tháng
                    Phương pháp tính toán là Làm tròn thời gian làm việc
                    Số ngày không hưởng lương bị ẩn đi (giá trị là 14)
                    Tỷ lệ đóng góp của nhân viên là 0
                    Tỷ lệ đóng góp của công ty là 0
        """
        # prepare data
        self.register = self.env['hr.contribution.register'].search([('company_id', '=', self.env.company.id)], limit=1)
        ContributionType = self.env['hr.payroll.contribution.type']
        contribution_type = ContributionType.create({
            'name': 'Type 1',
            'code': 'TT1',
            'employee_contrib_reg_id': self.register.id,
            'employee_contrib_rate': 2,
            'company_contrib_reg_id': self.register.id,
            'company_contrib_rate': 3,
            'computation_block': 'day',  # month, week
            'days_in_months': 'fixed',  # flexible
            'computation_method': 'half_up',  # max_unpaid_days
            'max_unpaid_days': 14
            })

        f = Form(self.env['hr.payroll.contribution.register'])

        # TH2: Xóa kiểu đóng góp / Giá trị mặc định khi mở form
        self.assertEqual(f.employee_contrib_rate, 0, 'Test Change Type not ok')
        self.assertEqual(f.company_contrib_rate, 0, 'Test Change Type not ok')
        self.assertEqual(f.computation_block, 'month', 'Test Change Type not ok')
        self.assertEqual(f.computation_method, 'half_up', 'Test Change Type not ok')
        self.assertEqual(f.max_unpaid_days, 14, 'Test Change Type not ok')
        self.assertEqual(f.days_in_months, 'fixed', 'Test Change Type not ok')

        # TH1: Select a Type
        f.type_id = contribution_type
        self.assertEqual(f.employee_contrib_rate, 2, 'Test Change Type not ok')
        self.assertEqual(f.company_contrib_rate, 3, 'Test Change Type not ok')
        self.assertEqual(f.computation_block, 'day', 'Test Change Type not ok')
        self.assertEqual(f.computation_method, 'half_up', 'Test Change Type not ok')
        self.assertEqual(f.max_unpaid_days, 14, 'Test Change Type not ok')
        self.assertEqual(f.days_in_months, 'fixed', 'Test Change Type not ok')

        # Other
        contribution_type.write({
            'computation_block': 'month',
            'days_in_months': 'flexible',
            'computation_method': 'max_unpaid_days'
            })
        f2 = Form(self.env['hr.payroll.contribution.register'])
        f2.type_id = contribution_type
        self.assertEqual(f2.computation_block, 'month', 'Test Change Type not ok')
        self.assertEqual(f2.computation_method, 'max_unpaid_days', 'Test Change Type not ok')
        self.assertEqual(f2.days_in_months, 'flexible', 'Test Change Type not ok')

    # 11B. Đăng ký đóng góp từ lương
    def test_contrib_register_check_overlap_number(self):
        """
        Case 1: Check trùng lặp theo nhân viên, mã số sổ đăng ký, kiểu đăng ký đóng góp từ lương
            TH1: Trùng cả 3 thông tin kiểu đóng góp, sổ đăng ký, nhân viên đã tồn tại
            TH2: Không trùng cả 3 thông kiểu đóng góp, sổ đăng ký, nhân viên đã tồn tại
        """
        register_1 = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        register_2 = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-2-1'))
        # TH2
        register_1.write({'registered_number': '123456'})
        register_2.write({'registered_number': '123457'})

        # TH1
        self.assertRaises(ValidationError, register_2.write, {'registered_number': '123456'})

    # 11B. Đăng ký đóng góp từ lương
    def test_contrib_register_check_overlap_1(self):
        """
        Case 3: check trùng lặp theo nhân viên, kiểu đóng góp, ngày bắt đầu, trạng thái, ngày kết thúc
            Tạo đăng ký đóng góp (A) và có các TH sau:
                TH1: Đã có đăng ký đóng góp (B), ở trạng thái khác "Đã đóng", chưa có ngày kết thúc
                    TH1.1: Ngày bắt đầu của (A) >= ngày bắt đầu của (B)
                        Output: Tạo không thành công
                    TH1.2: Ngày bắt đầu của (A) < ngày bắt đầu của (B)
                        Output: Tạo thành công
        """
        # (B)
        self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))

        # TH1.1: Ngày bắt đầu của (A) >= ngày bắt đầu của (B)
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))

        # TH1.2: Ngày bắt đầu của (A) < ngày bắt đầu của (B)
        register = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-2-1'))
        self.assertTrue(register, 'Test overlap payroll contribution register not ok')

    # 11B. Đăng ký đóng góp từ lương
    def test_contrib_register_check_overlap_2(self):
        """
        Case 3: check trùng lặp theo nhân viên, kiểu đóng góp, ngày bắt đầu, trạng thái, ngày kết thúc
            Tạo đăng ký đóng góp (A) và có các TH sau:
                TH2: Đã có đăng ký đóng góp (B), ở trạng thái khác "Đã đóng", Đã có ngày kết thúc
                    *Để có trường hợp này: B có luồng trạng thái như sau: Draft -> Confirmed -> Done -> Resume -> ...
                    TH2.1:
                        Ngày bắt đầu của (A) >= ngày bắt đầu của (B) và
                        Ngày bắt đầu của (A) <= ngày kết thúc của (B)
                Output: Không thành công
        """
        # TH2: Đã có đăng ký đóng góp (B), ở trạng thái khác "Đã đóng", Đã có ngày kết thúc
        register_1 = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        register_1.action_confirm()
        register_1.write({'date_to': fields.Date.to_date('2021-4-30')})
        register_1.with_context(call_wizard=False).action_done()
        register_1.write({'date_resumed': fields.Date.to_date('2021-5-1')})
        register_1.with_context(call_wizard=False).action_resume()
        # => register_1: date_from = 1/3/2021, date_to: 30/4/2021

        # TH2.1: Ngày bắt đầu của (A) >= ngày bắt đầu của (B) và Ngày bắt đầu của (A) <= ngày kết thúc của (B)
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-4-1'))

    # 11B. Đăng ký đóng góp từ lương
    def test_contrib_register_current_history(self):
        """
        Case 4: Test Thông tin "Dòng lịch sử hiện tại"
            * với 1 số trường hợp
            TH1: không có các dòng Lịch sử thay đổi tình trạng đóng góp từ lương
            Th2: có các dòng Lịch sử thay đổi tình trạng đóng góp từ lương
        """
        # TH1: không có các dòng Lịch sử thay đổi tình trạng đóng góp từ lương
        register_1 = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        self.assertFalse(register_1.current_history_id, 'Test Current History Line not ok')

        # Th2: có các dòng Lịch sử thay đổi tình trạng đóng góp từ lương
        # confirm
        register_1.action_confirm()
        self.assertEqual(
            register_1.current_history_id,
            register_1.payroll_contribution_history_ids[-1],
            'Test Current History Line not ok')

        # done
        register_1.write({'date_to': fields.Date.to_date('2021-4-30')})
        register_1.with_context(call_wizard=False).action_done()
        self.assertEqual(
            register_1.current_history_id,
            register_1.payroll_contribution_history_ids[-1],
            'Test Current History Line not ok')

    # 12. Lịch sử đăng ký đóng góp từ lương
    def test_contrib_register_history_lines(self):
        """
        Case 2: Test nút Cập nhật ngày kết thúc
            Output: Xuất hiện form cho nhập ngày kết thúc
        Case 3: Test form sau khi nhấn nút Cập nhật ngày kết thúc
            TH1:
                Input:
                    Ngày kết thúc > ngày bắt đầu, và không có dòng lịch sử khác ở sau
                Output: Lưu thành công, trường Ngày kết thúc được cập nhật
            TH2:
                Input:
                    ngày kết thúc < ngày bắt đầu, và không có dòng lịch sử khác ở sau
                Ouput: Lưu không thành công
            TH3:
                Input:
                    ngày kết thúc > ngày bắt đầu của dòng lịch sử hiện tại,
                    ngày kết thúc < ngày bắt đầu của dòng lịch sử tiếp theo
                Output: Lưu thành công, trường Ngày kết thúc được cập nhật
            TH4: Input:
                    ngày kết thúc > ngày bắt đầu của dòng lịch sử hiện tại,
                    ngày kết thúc > ngày bắt đầu của dòng lịch sử tiếp theo
                Ouput: Lưu không thành công
        """
        register_1 = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        register_1.action_confirm()
        register_1.write({'date_suspended': fields.Date.to_date('2021-4-30')})
        register_1.with_context(call_wizard=False).action_suspend()

        # Case 2: Test nút Cập nhật ngày kết thúc
        result = register_1.payroll_contribution_history_ids[-1].action_edit_date_end()
        self.assertIsNone(result, "Test Wizard display: History Contribution Registers not ok.")
        wizard_id = self.env.ref('to_hr_payroll.hr_payroll_contrib_action_edit_date_end_action').id
        result = register_1.payroll_contribution_history_ids[-1].with_context(call_wizard=True).action_edit_date_end()
        self.assertEqual(wizard_id, result.get('id', False), "Test Wizard display: History Contribution Registers not ok.")

        # Case 3: Test form sau khi nhấn nút Cập nhật ngày kết thúc
        # TH1:ngày kết thúc > ngày bắt đầu, và không có dòng lịch sử đằng sau
        wizard_change_date_end = self.env['hr.payroll.contrib.action.edit.date.end'].create({
            'payroll_contribution_history_id': register_1.payroll_contribution_history_ids[-1].id,
            'date_end': fields.Date.to_date('2021-5-30')
        })
        wizard_change_date_end.action_confirm()
        self.assertEqual(
            fields.Date.to_date('2021-5-30'),
            register_1.payroll_contribution_history_ids[-1].date_to,
            'Test change date end of history line not ok')

        # TH2:ngày kết thúc < ngày bắt đầu, và không có dòng lịch sử đằng sau
        wizard_change_date_end = self.env['hr.payroll.contrib.action.edit.date.end'].create({
            'payroll_contribution_history_id': register_1.payroll_contribution_history_ids[-1].id,
            'date_end': fields.Date.to_date('2021-4-29')
        })
        with self.assertRaises(UserError):
            with self.cr.savepoint():
                wizard_change_date_end.action_confirm()

        # TH3:ngày kết thúc > ngày bắt đầu của dòng hiện tại, ngày kết thúc < ngày bắt đầu của dòng lịch sử tiếp theo
        wizard_change_date_end = self.env['hr.payroll.contrib.action.edit.date.end'].create({
            'payroll_contribution_history_id': register_1.payroll_contribution_history_ids[-2].id,
            'date_end': fields.Date.to_date('2021-3-28')
        })
        wizard_change_date_end.action_confirm()
        self.assertEqual(
            fields.Date.to_date('2021-3-28'),
            register_1.payroll_contribution_history_ids[-2].date_to,
            'Test change date end of history line not ok')

        # TH4:ngày kết thúc > ngày bắt đầu của dòng hiện tại, ngày kết thúc > ngày bắt đầu của dòng lịch sử tiếp theo
        wizard_change_date_end = self.env['hr.payroll.contrib.action.edit.date.end'].create({
            'payroll_contribution_history_id': register_1.payroll_contribution_history_ids[-2].id,
            'date_end': fields.Date.to_date('2021-5-2')
        })
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                wizard_change_date_end.action_confirm()

    # Test Flow
    def test_flow_contrib_register_change_rate(self):
        """
        1. Đăng ký đóng góp từ lương
            Case 6A Test nút Thay đổi tỷ lệ
                Output: Xuất hiện form chọn ngày thay đổi, tỷ lệ đóng góp của nhân viên và tỷ lệ đóng góp của công ty
            Case 6B Test Form sau khi nhấn nút Thay đổi tỷ lệ
                TH1: Ngày > ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                    => Thay đổi thành công:
                        Dòng lịch sử hiện tại trước khi được thay đổi sẽ cập nhật trường Ngày kết thúc có giá trị là trước 1 ngày với ngày vừa nhập trên form
                        Tạo thêm dòng lịch sử tình trạng đóng góp mới, ngày bắt đầu là ngày vừa chọn, không có ngày kết thúc
                        Dòng lịch sử đóng góp hiện tại sẽ được thay thế thành dòng lịch sử đóng góp vừa tạo
                        Các thông tin: cơ sở tính toán, tỷ lệ đóng góp, trạng thái được thấy theo đăng ký đóng góp từ lương
                TH2: Ngày = ngày bắt đầu của  của dòng lịch sử hiện tại
                    => Thay đổi thành công, Dòng lịch sử hiện tại sẽ thay đổi tỷ lệ đóng góp vừa nhập
                TH3: Ngày < ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                    => Lưu không thành công, thông báo ngoại lệ
                TH4: Ngày < Trường "Từ ngày" của đăng ký đóng góp này
                    => Lưu không thành công, thông báo ngoại lệ
        """
        # Prepare data
        register = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        register.action_confirm()

        # Case 6A Test nút Thay đổi tỷ lệ
        wizard = self.env.ref('to_hr_payroll.hr_payroll_contrib_action_change_rates_action')
        result = register.with_context(call_wizard=True).action_change_rates()
        self.assertEqual(wizard.id, result.get('id', False), "Test Wizard display: Change Contribution Rates not ok.")

        # Case 6B Test Form sau khi nhấn nút Thay đổi tỷ lệ
        # TH3+4
        wizard_change_rate = self.env['hr.payroll.contrib.action.change.rates'].create({
            'payroll_contribution_reg_ids': [(6, 0, register.ids)],
            'date': fields.Date.to_date('2021-2-28'),
            'employee_contrib_rate': 1.5,
            'company_contrib_rate': 2.5
        })
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                wizard_change_rate.process()

        # TH1
        wizard_change_rate.write({'date': fields.Date.to_date('2021-3-10')})
        wizard_change_rate.process()
        new_history = register.payroll_contribution_history_ids[-1]
        self.assertRecordValues(new_history, [{
            'id': register.current_history_id.id,
            'state': register.state,
            'contribution_base': register.contribution_base,
            'employee_contrib_rate': register.employee_contrib_rate,
            'company_contrib_rate': register.company_contrib_rate,
            'date_from': fields.Date.to_date('2021-3-10'),
            'date_to': False,
        }])
        self.assertEqual(
            register.payroll_contribution_history_ids[-2].date_to,
            fields.Date.to_date('2021-3-9'),
            'Test Change Rate button not ok')

        # TH2:
        register.action_cancel()
        register.action_confirm()
        wizard_change_rate.write({'date': fields.Date.to_date('2021-3-1')})
        wizard_change_rate.process()
        self.assertEqual(1.5, register.current_history_id.employee_contrib_rate, 'Test Change Rate button not ok')
        self.assertEqual(2.5, register.current_history_id.company_contrib_rate, 'Test Change Rate button not ok')

    # Test Flow
    def test_flow_contrib_register_change_base(self):
        """
        1. Đăng ký đóng góp từ lương
            Case 5A: Test nút Thay đổi cơ sở tính toán
                => Output: Xuất hiện form chọn ngày thay đổi và cơ sở tính toán lương

            Case 5B: Test Form sau khi nhấn nút Thay đổi cơ sở tính toán
                TH1: Ngày > ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                    => Lưu thành công,
                        Dòng lịch sử hiện tại trước khi được thay đổi sẽ cập nhật trường  Ngày kết thúc có giá trị là trước 1 ngày với ngày vừa nhập trên form
                        Tạo thêm dòng lịch sử tình trạng đóng góp mới, ngày bắt đầu là ngày vừa chọn, không có ngày kết thúc
                        Dòng lịch sử hiện tại được thay đổi thành dòng lịch sử đóng góp từ lương vừa tạo vừa tạo
                        Các thông tin: cơ sở tính toán, tỷ lệ đóng góp, trạng thái được thấy theo đăng ký đóng góp từ lương

                TH2: Ngày = ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                    => Lưu thành công:
                        Dòng lịch sử hiện tại sẽ thay đổi cơ sở tính toán vừa nhập

                TH3: Ngày < ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                    => Lưu không thành công, thông báo ngoại lệ

                TH4: Ngày < Trường "Từ ngày" của đăng ký đóng góp này
                    => Lưu không thành công, thông báo ngoại lệ
        """
        # prepare data
        register = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        register.action_confirm()

        # Case 5A: Test nút Thay đổi cơ sở tính toán
        wizard = self.env.ref('to_hr_payroll.hr_payroll_contrib_action_change_base_action')
        result = register.with_context(call_wizard=True).action_change_base()
        self.assertEqual(wizard.id, result.get('id', False), "Test Wizard display: Change Computation Base not ok.")

        # Case 5B: Test Form sau khi nhấn nút Thay đổi cơ sở tính toán
        # TH3+4
        wizard_change_rate = self.env['hr.payroll.contrib.action.change.base'].create({
            'payroll_contribution_reg_ids': [(6, 0, register.ids)],
            'date': fields.Date.to_date('2021-2-28'),
            'contribution_base': 750
        })
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                wizard_change_rate.process()

        # TH1:
        wizard_change_rate.write({'date': fields.Date.to_date('2021-3-10')})
        wizard_change_rate.process()
        new_history = register.payroll_contribution_history_ids[-1]
        self.assertEqual(750, register.contribution_base, 'Test Change Computation Base button not ok')
        self.assertRecordValues(new_history, [{
            'id': register.current_history_id.id,
            'state': register.state,
            'contribution_base': register.contribution_base,
            'employee_contrib_rate': register.employee_contrib_rate,
            'company_contrib_rate': register.company_contrib_rate,
            'date_from': fields.Date.to_date('2021-3-10'),
            'date_to': False,
        }])
        self.assertEqual(
            register.payroll_contribution_history_ids[-2].date_to,
            fields.Date.to_date('2021-3-9'),
            'Test Change Computation Base button not ok')

        # TH2:
        register.action_cancel()
        register.action_confirm()
        wizard_change_rate.write({'date': fields.Date.to_date('2021-3-1')})
        wizard_change_rate.process()
        self.assertEqual(750, register.current_history_id.contribution_base, 'Test Change Computation Base button not ok')

    # Test Flow
    def test_flow_contrib_register_draft(self):
        """
        Flow: Draft -> Confirmed -> Suspend -> Resumed -> Done -> Cancelled -> Draft
        1. Đăng ký đóng góp từ lương
            1.1 Đăng ký đóng góp từ lương ở trạng thái Dự thảo :
                Case 0: Test nút Hủy, Tái tham gia, Đặt về Dự thảo (Không hiện thị trên view)
                    => Không thành công

                Case 2: Test nút xác nhận, có hợp đồng hợp lệ
                    => Xác nhận thành công:
                        Sinh ra dòng lịch sử đóng góp từ lương có ngày bắt đầu, cơ sở tính toán, tỷ lệ đóng góp theo các thông tin trên Đăng ký đóng góp từ lương.
                        Dòng lịch sử hiện tại là dòng lịch sử đóng góp từ lương bên trên
                        Thạng thái là Đã xác nhận
                        Bổ sung thêm kiểu đóng góp từ lương trên hợp đồng nhân viên ở trạng thái "Đang chạy / Hết hạn" nếu đăng ký đóng góp này là kiểu chưa có sẵn trên hợp đồng nhân viên

                Case 5: Test nút xác nhận, hợp đồng Đã hủy / dự thảo
                    => Output: Đăng ký đóng góp từ lương thành công nhưng không ghi nhận lên hợp đồng nào

                Case 4: Test xóa Đăng ký Đóng góp từ lương khi ở trạng thái Dự thảo
                    => Output: Xóa thành công
        """
        # Case 4: Test xóa Đăng ký Đóng góp từ lương khi ở trạng thái Dự thảo
        register = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        self.assertTrue(register.unlink())

        # Case 0: Test nút Hủy, Tái tham gia, Đặt về Dự thảo
        register = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register.action_cancel()
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register.action_resume()
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register.action_draft()

        # Case 2: Test nút xác nhận, có hợp đồng hợp lệ
        register.action_confirm()
        new_history = register.payroll_contribution_history_ids[-1]
        self.assertRecordValues(new_history, [{
            'id': register.current_history_id.id,
            'state': register.state,
            'contribution_base': register.contribution_base,
            'employee_contrib_rate': register.employee_contrib_rate,
            'company_contrib_rate': register.company_contrib_rate,
            'date_from': register.date_from,
            'date_to': False,
        }])
        self.assertIn(self.type, self.contract_open_emp_A.payroll_contribution_type_ids, 'Test Confirm button not ok')
        self.assertIn(register, self.contract_open_emp_A.payroll_contribution_register_ids, 'Test Confirm button not ok')

        # Case 5: Test nút xác nhận, hợp đồng Đã hủy / dự thảo
        # => check thông tin của hợp đồng không hợp lệ có cùng khoảng thời gian của đăng ký đóng góp ( Đã hủy/ Dự thảo)
        # self.contract_draft_emp_A is Draft
        # self.contract_cancel_emp_A is Cancel
        self.assertNotIn(self.type, self.contract_draft_emp_A.payroll_contribution_type_ids, 'Test Confirm button not ok')
        self.assertNotIn(register, self.contract_draft_emp_A.payroll_contribution_register_ids, 'Test Confirm button not ok')
        self.assertNotIn(self.type, self.contract_cancel_emp_A.payroll_contribution_type_ids, 'Test Confirm button not ok')
        self.assertNotIn(register, self.contract_cancel_emp_A.payroll_contribution_register_ids, 'Test Confirm button not ok')

    # Test Flow
    def test_flow_contrib_register_confirmed(self):
        """
        Flow: Draft -> Confirmed -> Suspend -> Resumed -> Done -> Cancelled -> Draft

        1. Đăng ký đóng góp từ lương
            1.2 Đăng ký đóng góp từ lương ở trạng thái Đã xác nhận
                Case 0: Test nút Tái tham gia, Đặt về dự thảo
                    => Không thành công

                Case 2A: Test nút Tạm dừng (ở trạng thái Đã xác nhận / Tái tham gia)
                    => Output: Xuất hiện form chọn ngày tạm dừng

                Case 2B: Test Form sau khi nhấn nút Tạm dừng
                    TH1: >= ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                        => Lưu thành công,
                            Tạo thêm dòng lịch sử tình trạng đóng góp, ngày bắt đầu là ngày chọn tạm dừng + 1 ngày, không có ngày kết thúc
                            Dòng lịch sử hiện tại là dòng lịch sử vừa tạo
                            Trường "Đến ngày" là ngày tạm dừng vừa chọn
                            Trường "Ngày tạm dùng" là ngày tạm dừng vừa chọn
                            Trạng thái là Tạm dừng

                    TH2: < ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                        => Lưu không thành công, thông báo ngoại lệ

                    TH3: < Trường "Từ ngày" của đăng ký đóng góp này
                        => Lưu không thành công, thông báo ngoại lệ

                Case 8: Xóa Đăng ký đóng góp từ lương ở trạng thái "Đã xác nhận"
                    => Output: Xóa không thành công
        """
        register = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        register.action_confirm()

        # Case 8: Xóa Đăng ký đóng góp từ lương ở trạng thái "Đã xác nhận"
        self.assertRaises(UserError, register.unlink)

        # Case 0: Test nút Tái tham gia, Đặt về dự thảo => Không thành công
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register.write({"date_resumed": fields.Date.today()})
                register.action_resume()
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register.action_draft()

        # Case 2A: Test nút Tạm dừng (ở trạng thái Đã xác nhận / Tái tham gia)
        wizard = self.env.ref('to_hr_payroll.hr_payroll_contrib_action_suspend_action')
        result = register.with_context(call_wizard=True).action_suspend()
        self.assertEqual(wizard.id, result.get('id', False), "Test Wizard display: Suspend Contribution Registers not ok.")

        # Case 2B: Test Form sau khi nhấn nút Tạm dừng
        # Case 2B / TH 2+3
        wizard_suspend = self.env['hr.payroll.contrib.action.suspend'].create({
            'payroll_contribution_reg_ids': [(6, 0, register.ids)]
        })
        with self.assertRaises(UserError):
            wizard_suspend.write({
                'date': fields.Date.to_date('2021-2-28')
            })

        # Case 2B: Test Form sau khi nhấn nút Tạm dừng
        # Case 2B / TH 1
        wizard_suspend.write({'date': fields.Date.to_date('2021-3-30')})
        wizard_suspend.process()
        new_history = register.payroll_contribution_history_ids[-1]
        self.assertRecordValues(new_history, [{
            'id': register.current_history_id.id,
            'state': register.state,
            'contribution_base': register.contribution_base,
            'employee_contrib_rate': register.employee_contrib_rate,
            'company_contrib_rate': register.company_contrib_rate,
            'date_from': fields.Date.to_date('2021-3-30'),
            'date_to': False,
        }])
        self.assertRecordValues(register, [{
            'date_suspended': fields.Date.to_date('2021-3-30'),
            'state': 'suspended',
        }])
        self.assertEqual(
            register.payroll_contribution_history_ids[-2].date_to,
            fields.Date.to_date('2021-3-29'),
            'Test Change Suspend button not ok')

    # Test Flow
    def test_flow_contrib_register_suspended(self):
        """
        1. Đăng ký đóng góp từ lương
            1.3 Đăng ký đóng góp từ lương ở trạng thái Tạm dừng
                Case 0: Test nút Đặt về dự thảo
                    => Không thành công

                Case 2: Test nút Tái tham gia
                    => Output: Xuất hiện form chọn ngày thay đổi, tỷ lệ đóng góp, cơ sở tính toán

                Case 3: Test Form sau khi nhấn nút Tái tham gia
                    TH1: Đăng ký đóng góp ở trạng thái khác "Tạm dừng" / "Đã đóng"
                        => không thành công, thông báo ngoại lệ

                    TH2: Ngày <= ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                        => không thành công, thông báo ngoại lệ

                    TH3 : Đăng ký đóng góp ở trạng thái "Tạm dừng" / "Đã đóng" và
                            Ngày vừa chọn  >  Ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                        => Lưu thành công:
                            Dòng lịch sử hiện tại được cập nhật trường "Đến ngày" là  trước 1 ngày vừa nhập
                            Tạo dòng lịch sử mới , ngày bắt đầu, tỷ lệ đóng góp, cơ sở tính toán là các giá trị vừa nhập, trạng thái là trạng thái của đăng ký đóng góp
                            Dòng lịch sử hiện tại sẽ được thay đổi thành dòng lịch sử mới vừa tạo, trạng thái chuyển sang Tái tham gia

                Case 5: Xóa Đăng ký đóng góp từ lương ở trạng thái "Tạm dừng"
                    => Output: Sinh ra Error

                Case 6: Tạm dừng đóng góp từ lương ở các trạng thái khác trạng thái "Đã xác nhận", "Đã đóng", "Tái tham gia"
                    => Output: Sinh ra Error
        """
        # prepare data
        register = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        register.action_confirm()
        register.write({'date_suspended': fields.Date.to_date('2021-3-30')})
        register.with_context(call_wizard=False).action_suspend()

        # Case 5
        self.assertRaises(UserError, register.unlink)

        # Case 0
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register.action_draft()

        # Case 2: Test nút Tái tham gia
        wizard = self.env.ref('to_hr_payroll.hr_payroll_contrib_action_resume_action')
        result = register.with_context(call_wizard=True).action_resume()
        self.assertEqual(wizard.id, result.get('id', False), "Test Wizard display: Resume Contribution Registers not ok.")

        # Case 3: Test Form sau khi nhấn nút Tái tham gia
        # Case 3 / TH2
        wizard_resume = self.env['hr.payroll.contrib.action.resume'].create({
            'payroll_contribution_reg_ids': [(6, 0, register.ids)],
            'contribution_base': 1000,
            'employee_contrib_rate': 3.5,
            'company_contrib_rate': 7
        })
        with self.assertRaises(UserError):
            wizard_resume.write({
                'date': fields.Date.to_date('2021-2-28'),
            })

        # Case 3: Test Form sau khi nhấn nút Tái tham gia
        # Case 3 / TH3
        wizard_resume.write({'date': fields.Date.to_date('2021-4-1')})
        wizard_resume.process()
        new_history = register.payroll_contribution_history_ids[-1]
        self.assertRecordValues(new_history, [{
            'id': register.current_history_id.id,
            'state': register.state,
            'contribution_base': register.contribution_base,
            'employee_contrib_rate': register.employee_contrib_rate,
            'company_contrib_rate': register.company_contrib_rate,
            'date_from': fields.Date.to_date('2021-4-1'),
            'date_to': False,
        }])
        self.assertRecordValues(register, [{
            'date_resumed': fields.Date.to_date('2021-4-1'),
            'state': 'resumed',
        }])
        self.assertEqual(
            register.payroll_contribution_history_ids[-2].date_to,
            fields.Date.to_date('2021-3-31'),
            'Test Resume button not ok')

        # Case 6
        register_2 = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-2-1'))
        with self.assertRaises(ValidationError, msg="test_flow_contrib_register_suspended case 6"):
            register_2.action_suspend()

    # Test Flow
    def test_flow_contrib_register_resumed(self):
        """
        1. Đăng ký đóng góp từ lương
            1.4 Đăng ký đóng góp từ lương ở trạng thái Tái tham gia
                Case 0: Test nút Đặt về dự thảo, Tái tham gia
                    => Không thành công

                Case 3A: Test nút Đóng (Đã xác nhận / Tạm dừng)
                    => Output: Xuất hiện form chọn ngày để đóng đăng ký đóng góp

                Case 3B: Test Form sau khi nhấn nút Đóng
                    TH1: >= ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                        => Lưu thành công,
                            Tạo thêm dòng lịch sử tình trạng đóng góp, ngày bắt đầu là ngày vừa chọn, không có ngày kết thúc
                            Dòng lịch sử hiện tại là dòng lịch sử vừa tạo
                            Trường "Đến ngày" là ngày vừa chọn
                            Trạng thái là Đã đóng

                    TH2: < ngày bắt đầu của lần thay đổi trạng thái cuối cùng của đăng ký đóng góp này
                        => Lưu không thành công, thông báo ngoại lệ

                    TH3: < Trường "Từ ngày" của đăng ký đóng góp này
                        => Lưu không thành công, thông báo ngoại lệ

                Case 3: Xóa đăng ký đóng góp từ lương trạng thái :" Tái tham gia"
                    => Output: Xóa không thành công, hiển thị message cảnh báo.
        """
        # prepare data
        register = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        register.action_confirm()
        register.write({'date_suspended': fields.Date.to_date('2021-3-30')})
        register.with_context(call_wizard=False).action_suspend()
        register.write({'date_resumed': fields.Date.to_date('2021-4-1')})
        register.with_context(call_wizard=False).action_resume()

        # Case 3
        self.assertRaises(UserError, register.unlink)

        # Case 0
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register.action_resume()
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register.action_draft()

        # Case 3A: Test nút Đóng (ở trạng thái Tái tham gia / Đã xác nhận / Tạm dừng)
        wizard = self.env.ref('to_hr_payroll.hr_payroll_contrib_action_done_action')
        result = register.with_context(call_wizard=True).action_done()
        self.assertEqual(wizard.id, result.get('id', False), "Test Wizard display: Close Contribution Registers not ok.")

        # Case 3B: Test Form sau khi nhấn nút Đóng
        # TH 2+3
        wizard_done = self.env['hr.payroll.contrib.action.done'].create({
            'payroll_contribution_reg_ids': [(6, 0, register.ids)],
        })
        with self.assertRaises(UserError):
            wizard_done.write({
                'date': fields.Date.to_date('2021-3-30'),
            })

        # Case 3B: Test Form sau khi nhấn nút Đóng
        # TH 1
        wizard_done.write({'date': fields.Date.to_date('2021-5-1')})
        wizard_done.process()
        new_history = register.payroll_contribution_history_ids[-1]
        self.assertRecordValues(new_history, [{
            'id': register.current_history_id.id,
            'state': register.state,
            'contribution_base': register.contribution_base,
            'employee_contrib_rate': register.employee_contrib_rate,
            'company_contrib_rate': register.company_contrib_rate,
            'date_from': fields.Date.to_date('2021-5-1'),
            'date_to': False,
        }])
        self.assertRecordValues(register, [{
            'date_resumed': fields.Date.to_date('2021-4-1'),
            'state': 'done',
        }])
        self.assertEqual(
            register.payroll_contribution_history_ids[-2].date_to,
            fields.Date.to_date('2021-4-30'),
            'Test Close button not ok')

    # Test Flow
    def test_flow_contrib_register_done(self):
        """
        1. Đăng ký đóng góp từ lương
            1.5 Đăng ký đóng góp từ lương ở trạng thái Đã đóng
                Case 0: Test nút Đặt về dự thảo
                    => Không thành công

                Case 4: Test nút Hủy (Đã xác nhận/ Tạm dừng / Tái tham gia)
                    => Hủy thành công:
                        Tất cả dòng lịch sử thay đỏi bị xóa
                        ngày tạm dừng = Fasle
                        ngày tái tham gia = False
                        Đến ngày = False
                        Trạng thái là đã hủy
        """
        # prepare data
        register_1 = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        register_1.action_confirm()
        register_1.write({'date_to': fields.Date.to_date('2021-4-1')})
        register_1.with_context(call_wizard=False).action_done()

        # Case 0
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register_1.action_draft()

        # Case 4: Test nút Hủy (ở trạng thái Đã xác nhận/ Tạm dừng / Tái tham gia / Đã đóng)
        register_1.action_cancel()
        self.assertFalse(register_1.date_to, 'Test Cancel button not ok')
        self.assertFalse(register_1.date_suspended, 'Test Cancel button not ok')
        self.assertFalse(register_1.date_resumed, 'Test Cancel button not ok')
        self.assertEqual(register_1.state, 'cancelled', 'Test Cancel button not ok')
        self.assertFalse(register_1.payroll_contribution_history_ids, 'Test Cancel button not ok')

    # Test Flow
    def test_flow_contrib_register_cancel(self):
        """
        1. Đăng ký đóng góp từ lương
            1.6 Đăng ký đóng góp từ lương ở trạng thái Đã hủy
                Case 0: Test nút hủy, tái tham gia
                    => Không thành công

                Case 2: Test nút Đặt về dự thảo
                    => Thành công, trạng thái thay đổi thành dự thảo
        """
        # prepare data
        register_1 = self.create_contrib_register(self.product_emp_A, self.type, fields.Date.to_date('2021-3-1'))
        register_1.action_confirm()
        register_1.action_cancel()

        # Case 0
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register_1.action_cancel()
        with self.assertRaises(ValidationError):
            with self.cr.savepoint():
                register_1.action_resume()

        # Case 2
        register_1.action_draft()
        self.assertEqual(register_1.state, 'draft', 'Test Draft button not ok')
