from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError, UserError
from odoo.tests import Form
from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollPayslip(TestPayrollCommon):

    def test_01_form_payslip_date_from(self):
        """
        Test Ngày kết thúc thay đổi khi sửa ngày bắt đầu của phiếu lương
            => Ngày kết thúc thay đổi thành ngày tương ứng của tháng sau nhưng trừ đi 1 ngày.
        """
        f = Form(self.env['hr.payslip'])
        f.date_from = fields.Date.to_date('2021-07-01')
        self.assertEqual(fields.Date.to_date('2021-07-31'), f.date_to, 'Test default date from, date to not ok')

        f.date_from = fields.Date.to_date('2021-06-01')
        self.assertEqual(fields.Date.to_date('2021-06-30'), f.date_to, 'Test default date from, date to not ok')

    def test_02_form_payslip_cycle(self):
        """
        Case 12: Test trường Chu kỳ lương
            Output: Trường Chu kỳ lương lấy đúng theo Chu kỳ lương được thiết lập trên công ty
        """
        salalry_cycle_1 = self.env['hr.salary.cycle'].search([], limit=1)
        salalry_cycle_2 = self.env['hr.salary.cycle'].create({'name': 'Slalary Cycle 2'})

        self.env.company.write({'salary_cycle_id': salalry_cycle_2.id})
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertEqual(payslip_1.salary_cycle_id, salalry_cycle_2, 'Test default salary_cycle_id field not ok')

        self.env.company.write({'salary_cycle_id': salalry_cycle_1.id})
        payslip_2 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertEqual(payslip_2.salary_cycle_id, salalry_cycle_1, 'Test default salary_cycle_id field not ok')

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-4'))
    def test_03_form_payslip_default_date_1(self):
        """
        Test: Mặc định ngày bắt đầu, ngày kết thúc khi mở form phiếu lương là của chu kỳ trước
        Input:
            Chu kỳ lương không lệch chuẩn, trường `Độ lệch ngày bắt đầu` = 0
        Ouput
            Chu kỳ lương là ngày đầu tháng, cuối tháng của tháng trước
        """
        f = Form(self.env['hr.payslip'])
        self.assertEqual(
            fields.Date.to_date('2021-6-1'),
            fields.Date.to_date(f.date_from),
            'Test default date from not ok')
        self.assertEqual(
            fields.Date.to_date('2021-6-30'),
            fields.Date.to_date(f.date_to),
            'Test default date from not ok')

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-4'))
    def test_03_form_payslip_default_date_2(self):
        """
        Test: Mặc định ngày bắt đầu, ngày kết thúc khi mở form phiếu lương là của chu kỳ trước
        Input:
            Chu kỳ lương không lệch chuẩn, trường `Độ lệch ngày bắt đầu` = 0
            Đánh dấu phiếu lương tháng 13
        Ouput
            Chu kỳ lương là ngày đầu năm, cuối năm của năm trước
        """
        f = Form(self.env['hr.payslip'])
        f.thirteen_month_pay = True
        self.assertEqual(
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date(f.date_from),
            'Test default date from not ok')
        self.assertEqual(
            fields.Date.to_date('2020-12-31'),
            fields.Date.to_date(f.date_to),
            'Test default date from not ok')
        self.assertEqual(f.thirteen_month_pay_year, 2020, 'Test default thirteen_month_pay_year to not ok')

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-4'))
    def test_03_form_payslip_default_date_3(self):
        """
        Test: Mặc định ngày bắt đầu, ngày kết thúc khi mở form phiếu lương là của chu kỳ trước
        Input:
            Chu kỳ lương lệch chuẩn, trường `Độ lệch ngày bắt đầu` = 5
            Ngày hiện tại 4/7/2021
                => Chu kỳ hiện tại 6/6/2021 -> 6/7/2021
        Ouput
            Chu kỳ lương thuộc chu kỳ trước: 6/5/2021 -> 5/6/2021
        """
        self.env.company.salary_cycle_id.start_day_offset = 5
        f = Form(self.env['hr.payslip'])
        self.assertEqual(
            fields.Date.to_date('2021-5-6'),
            fields.Date.to_date(f.date_from),
            'Test default date from, date to not ok')
        self.assertEqual(
            fields.Date.to_date('2021-6-5'),
            fields.Date.to_date(f.date_to),
            'Test default date from, date to not ok')

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-7'))
    def test_03_form_payslip_default_date_4(self):
        """
        Test: Mặc định ngày bắt đầu, ngày kết thúc khi mở form phiếu lương là của chu kỳ trước
        Input:
            Chu kỳ lương lệch chuẩn, trường `Độ lệch ngày bắt đầu` = 5
            Ngày hiện tại 7/7/2021
                => Chu kỳ hiện tại 6/7/2021 -> 5/8/2021
        Ouput
            Chu kỳ lương thuộc chu kỳ trước: 6/6/2021 -> 5/7/2021
        """
        self.env.company.salary_cycle_id.start_day_offset = 5
        f = Form(self.env['hr.payslip'])
        self.assertEqual(
            fields.Date.to_date('2021-6-6'),
            fields.Date.to_date(f.date_from),
            'Test default date from, date to not ok')
        self.assertEqual(
            fields.Date.to_date('2021-7-5'),
            fields.Date.to_date(f.date_to),
            'Test default date from, date to not ok')

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-4'))
    def test_03_form_payslip_default_date_5(self):
        """Test: Mặc định ngày bắt đầu, ngày kết thúc khi mở form phiếu lương là của chu kỳ trước
        Input:
            Chu kỳ lương lệch chuẩn, trường `Độ lệch ngày bắt đầu` = 5
            Đánh dấu phiếu lương tháng 13
        Ouput
            Chu kỳ lương thuộc chu kỳ trước: 6/1/2020 -> 5/1/2021
        """
        self.env.company.salary_cycle_id.start_day_offset = 5
        f = Form(self.env['hr.payslip'])
        f.thirteen_month_pay = True
        self.assertEqual(
            fields.Date.to_date(f.date_from),
            fields.Date.to_date('2020-1-6'),
            'Test default date from, date to not ok')
        self.assertEqual(
            fields.Date.to_date(f.date_to),
            fields.Date.to_date('2021-1-5'),
            'Test default date from, date to not ok')
        self.assertEqual(f.thirteen_month_pay_year, 2020, 'Test default thirteen_month_pay_year to not ok')

    def test_04_payslip_name_1(self):
        """
        Test: trường Tên phiếu lương khi thay đổi Chu kỳ (Từ ngày - Đến ngày)
            Output: "Đến ngày" rơi vào tháng nào thì Tên phiếu lương thay đổi bằng tháng đó.
        """
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))

        self.assertEqual(payslip_1.name, 'Salary Slip of Product Employee A for July-2021', 'Test name field not ok')
        payslip_1.write({
            'date_from': fields.Date.to_date('2021-5-1'),
            'date_to': fields.Date.to_date('2021-6-30')
        })
        self.assertEqual(payslip_1.name, 'Salary Slip of Product Employee A for June-2021', 'Test name field not ok')

    def test_05_payslip_name_2(self):
        """
        Test: trường Tên phiếu lương khi thay đổi Nhân viên
            Output: Tên phiếu lương thay đổi theo tên của nhân viên mới được chọn
        """
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-1-1'),
            fields.Date.to_date('2021-12-31'), 'open')
        payslip_1.write({
            'employee_id': self.product_dep_manager.id,
            'date_from': fields.Date.to_date('2021-5-1'),
            'date_to': fields.Date.to_date('2021-6-30')
        })

        self.assertEqual(payslip_1.name, 'Salary Slip of Product Department Manager for June-2021',
                         'Test name field not ok')

    def test_06_payslip_name_3(self):
        """
        Test: Tên phiếu lương khi phiếu lương đánh dấu lương tháng 13
        """
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        payslip_1.write({
            'thirteen_month_pay': True,
            'thirteen_month_pay_year': 2020
        })
        self.assertEqual(payslip_1.name, '13th-Month Salary of Product Employee A for the year 2020',
                         'Test name field not ok')

    # @mute_logger('odoo.sql_db')
    # def test_payslip_contract_1(self):
    #     """
    #     Case 3: Test trường "Hợp đồng" khi thay đổi Nhân viên / khoảng thời gian chu kỳ lương
    #         TH 1: Nhân viên không có hợp đồng nào ở trạng thái "Đang chạy" / "Hết hạn"
    #             => Output: Không có hợp đồng / lưu không thành công
    #     """
    #     payslip = self.create_payslip(
    #         self.product_emp_A.id,
    #         fields.Date.to_date('2021-7-1'),
    #         fields.Date.to_date('2021-7-31'))
    #     payslip.write({'employee_id': self.product_dep_manager})
    #     with self.assertRaises(IntegrityError):
    #             payslip.write({'employee_id': self.product_dep_manager})

    def test_07_payslip_contract_2(self):
        """
        Case 3: Test trường "Hợp đồng" khi thay đổi Nhân viên / khoảng thời gian chu kỳ lương
            TH 3: nhân viên có hợp đồng ở trạng thái "Đang chạy" / "Hết hạn",
                Thời gian bắt đầu / Kết thúc không hợp lệ với thời gian trên phiếu lương phiếu lương

                => Output: Hợp đồng được điền tự động trên phiếu lương / lưu thành công
        """
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        payslip.write({
            'date_from': fields.Date.to_date('2020-12-1'),
            'date_to': fields.Date.to_date('2020-12-31')
        })
        self.assertEqual(payslip.contract_ids, self.contract_close_emp_A, 'Test compute contract not ok')

        # change employee
        new_contract = self.create_contract(self.product_dep_manager.id, fields.Date.to_date('2019-1-1'))
        payslip.write({
            'employee_id': self.product_dep_manager.id
        })
        self.assertEqual(payslip.contract_ids, new_contract, 'Test compute contract not ok')

    def test_07_payslip_contract_4(self):
        """
        Case 3: Test trường "Hợp đồng" khi thay đổi Nhân viên / khoảng thời gian chu kỳ lương
            TH 4: Nhân viên có nhiều hợp đồng ở trạng thái "Đang chạy" / "Hết hạn",
                    Thời gian bắt đầu / Kết thúc hợp lệ với thời gian trên phiếu lương phiếu lương

                Output: lưu thành công:
                    Hợp đồng có ngày bắt đầu muộn nhất tính trong khoảng thời gian bắt đầu - kết thúc phiếu lương được điền tự động trên phiếu lương
        """
        contract_1 = self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-10'), 'close')
        contract_2 = self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-7-21'),
            fields.Date.to_date('2021-7-31'), 'open')
        contract_3 = self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-7-11'),
            fields.Date.to_date('2021-7-20'), 'open')
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))

        payslip.write({'employee_id': self.product_dep_manager.id})
        self.assertEqual(payslip.contract_ids, contract_1 | contract_2 | contract_3, 'Test compute contract not ok')

    def test_08_salary_structure_1(self):
        """
        Case 4: Test trường "Cấu trúc lương" thay đổi khi thay đổi hợp đồng / đánh dấu Lương tháng 13
            TH 1: Không đánh dấu "Lương tháng 13", có hợp đồng
                => Cấu trúc lương tháng 13 trên hợp đồng
        """
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertEqual(payslip.struct_id, self.contract_open_emp_A.struct_id, 'Test compute salary structure not ok')

    def test_08_salary_structure_2(self):
        """
        Case 4: Test trường "Cấu trúc lương" thay đổi khi thay đổi hợp đồng / đánh dấu Lương tháng 13
            TH 2: Đánh dấu "Lương tháng 13", có hợp đồng, hợp đồng không có cấu trúc lương tháng 13
                => Cấu trúc lương tháng 13 trên hợp đồng
        """
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-1-1'),
            fields.Date.to_date('2021-12-31'),
            thirteen_month_pay=True)
        self.assertEqual(payslip.struct_id, self.contract_open_emp_A.struct_id, 'Test compute salary structure not ok')

    def test_08_salary_structure_3(self):
        """
        Case 4: Test trường "Cấu trúc lương" thay đổi khi thay đổi hợp đồng / đánh dấu Lương tháng 13
            TH 3: Đánh dấu "Lương tháng 13", có hợp đồng, hợp đồng có cấu trúc lương tháng 13
                => Cấu trúc lương tháng 13 trên hợp đồng
        """
        struct_13th = self.structure_base.copy()
        self.contract_open_emp_A.write({
            'thirteen_month_struct_id': struct_13th.id
        })

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-1-1'),
            fields.Date.to_date('2021-12-31'),
            thirteen_month_pay=True)
        self.assertEqual(payslip.struct_id, struct_13th, 'Test compute salary structure not ok')

    def test_09_payslip_date_for_13th_month_1(self):
        """
        Case 7: Test ngày bắt đầu, ngày kết thúc khi đánh dấu lương tháng 13
            Input: Điền số năm vào Năm tính lương tháng 13
                TH1: Chu kỳ lương không lệch chuẩn
                    Output: Chu kỳ phiếu lương tự động điền ngày từ đầu năm đến cuối năm
        """
        f = Form(self.env['hr.payslip'])
        f.employee_id = self.product_dep_manager
        f.thirteen_month_pay = True
        f.thirteen_month_pay_year = 2020
        self.assertEqual(fields.Date.to_date('2020-1-1'), f.date_from,
                         'Test date from & date to with 13th month salary not ok')
        self.assertEqual(fields.Date.to_date('2020-12-31'), f.date_to,
                         'Test date from & date to with 13th month salary not ok')

    def test_09_payslip_date_for_13th_month_2(self):
        """
        Case 7: Test ngày bắt đầu, ngày kết thúc khi đánh dấu lương tháng 13
            Input: Điền số năm vào Năm tính lương tháng 13
                TH2: Chu kỳ lương có lệch chuẩn, lệch 5 ngày
                    Output: Chu kỳ phiếu lương lương có lệch chuẩn, lệch 5 ngày
        """
        cycle_salary = self.env['hr.salary.cycle'].search([], limit=1)
        cycle_salary.write({'start_day_offset': 5})

        f = Form(self.env['hr.payslip'])
        f.employee_id = self.product_dep_manager
        f.thirteen_month_pay = True
        f.thirteen_month_pay_year = 2019
        self.assertEqual(fields.Date.to_date('2019-1-6'), f.date_from,
                         'Test date from & date to with 13th month salary not ok')
        self.assertEqual(fields.Date.to_date('2020-1-5'), f.date_to,
                         'Test date from & date to with 13th month salary not ok')

    def test_10_payslip_date_from_date_to(self):
        """
        Test ngày bắt đầu, ngày kết thúc, trùng lặp, nhân bản...
            Case 1: Test Ngày bắt đầu phải lớn hơn ngày kết thúc
                TH1: Ngày kết thúc >= Ngày bắt đầu
                    => tạo phiếu lương thành công
                TH2: Ngày kết thúc < Ngày bắt đầu
                    => Tạo phiếu lương thất bại, Thông báo ngoại lệ
        """

        # TH2
        with self.assertRaises(ValidationError):
            self.create_payslip(
                self.product_emp_A.id,
                fields.Date.to_date('2021-7-1'),
                fields.Date.to_date('2021-6-1'))

        # TH1
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertTrue(payslip, 'Test Date from <= Date to not ok')

    def test_11_payslip_date_overtlap_1(self):
        """
        8.1. Test ngày bắt đầu, ngày kết thúc, trùng lặp, nhân bản...
            Case 2: Test trùng lặp phiếu lương, Phiếu lương không liên quan đến bảng lương
                =>  Tạo thành công
        """
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-6-1'),
            fields.Date.to_date('2021-6-30'))
        payslip_2 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-6-1'),
            fields.Date.to_date('2021-6-30'))
        self.assertTrue(payslip_1, 'Test Date from <= Date to not ok')
        self.assertTrue(payslip_2, 'Test Date from <= Date to not ok')

    def test_11_payslip_date_overtlap_2(self):
        """
        8.1. Test ngày bắt đầu, ngày kết thúc, trùng lặp, nhân bản...
            Case 3: Test trùng lặp phiếu lương, Phiếu lương liên quan đến bảng lương không đánh dấu lương tháng 13
                TH1: Phiếu lương của nhân viên là duy nhất trên bảng lương
                TH2: Nhân viên có nhiều hơn 1 phiếu lương trên bảng lương, các phiếu lương không trùng khoảng thời gian của nhau
                TH3: Nhân viên có nhiều hơn 1 phiếu lương trên bảng lương, có phiếu lương trùng khoảng thời gian của nhau

            Output:
                TH1+2: tạo/lưu thành công
                TH3: Thông báo lỗi
        """
        # TH1+2
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-6-1'),
            fields.Date.to_date('2021-6-30'))
        payslip_2 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-6-1'),
            fields.Date.to_date('2021-6-30'))
        payslip_run = self.env['hr.payslip.run'].create({
            'name': 'Payslip Batch',
            'date_start': fields.Date.to_date('2021-6-1'),
            'date_end': fields.Date.to_date('2021-6-30'),
            'salary_cycle_id': self.env.company.salary_cycle_id.id,
        })

        # TH3
        payslip_1.write({'payslip_run_id': payslip_run.id})
        with self.assertRaises(UserError):
            payslip_2.write({'payslip_run_id': payslip_run.id})

    def test_11_payslip_date_overtlap_3(self):
        """
        8.1. Test ngày bắt đầu, ngày kết thúc, trùng lặp, nhân bản...
            Case 4: Test trùng lặp phiếu lương, Phiếu lương liên quan bến bảng lương có đánh dấu lương tháng 13
                Input: Bảng lương với các phiếu lương cảu nhân viên
                    TH1: Phiếu lương của nhân viên là duy nhất trên bảng lương
                    TH2: Nhân viên có nhiều hơn 1 phiếu lương trên bảng lương
                Output:
                    TH1: Tạo/lưu thành công
                    TH2: Thông báo lỗi
        """
        # TH1
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-6-1'),
            fields.Date.to_date('2021-6-30'))
        payslip_2 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        payslip_run = self.env['hr.payslip.run'].create({
            'name': 'Payslip Batch',
            'date_start': fields.Date.to_date('2021-6-1'),
            'date_end': fields.Date.to_date('2021-6-30'),
            'thirteen_month_pay': True,
            'salary_cycle_id': self.env.company.salary_cycle_id.id,
        })

        # TH2
        payslip_1.write({'payslip_run_id': payslip_run.id})
        with self.assertRaises(UserError):
            payslip_2.write({'payslip_run_id': payslip_run.id})

    def test_12_payslip_duplicate_1(self):
        """
        8.1. Test ngày bắt đầu, ngày kết thúc, trùng lặp, nhân bản...
            Case 5: Test nhân bản phiếu lương, Phiếu lương không liên quan đến bảng lương nào
                Output: Nhân bản thành công
        """
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-6-1'),
            fields.Date.to_date('2021-6-30'))
        payslip_copy = payslip_1.copy()
        self.assertTrue(payslip_copy, 'Test Duplicate not ok')

    def test_13_payslip_duplicate_2(self):
        """
        8.1. Test ngày bắt đầu, ngày kết thúc, trùng lặp, nhân bản...
            Case 6: Test nhân bản phiếu lương, Phiếu lương có liên quan đến 1 bảng lương
                Output: Không thành công
        """
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-6-1'),
            fields.Date.to_date('2021-6-30'))
        payslip_run = self.env['hr.payslip.run'].create({
            'name': 'Payslip Batch',
            'date_start': fields.Date.to_date('2021-6-1'),
            'date_end': fields.Date.to_date('2021-6-30'),
            'thirteen_month_pay': True,
            'salary_cycle_id': self.env.company.salary_cycle_id.id,
        })
        payslip_1.write({'payslip_run_id': payslip_run.id})

        with self.assertRaises(UserError):
            payslip_1.copy()

    # 8. Phiếu lương
    def test_14_thirteen_month_pay_year_1(self):
        """
        Tạo phiếu lương tháng 13 với năm < 1970 hoặc năm >= 9999

        => Tạo không thành công
        """
        with self.assertRaises(UserError):
            self.env['hr.payslip'].with_context(tracking_disable=True).create({
                'employee_id': self.product_emp_A.id,
                'date_from': fields.Date.to_date('2021-1-1'),
                'date_to': fields.Date.to_date('2021-12-31'),
                'salary_cycle_id': self.env.company.salary_cycle_id.id,
                'thirteen_month_pay': True,
                'thirteen_month_pay_year': 9999,
                'company_id': self.env.company.id,
            })

        with self.assertRaises(UserError):
            self.env['hr.payslip'].with_context(tracking_disable=True).create({
                'employee_id': self.product_emp_A.id,
                'date_from': fields.Date.to_date('2021-1-1'),
                'date_to': fields.Date.to_date('2021-12-31'),
                'salary_cycle_id': self.env.company.salary_cycle_id.id,
                'thirteen_month_pay': True,
                'thirteen_month_pay_year': 1969,
                'company_id': self.env.company.id,
            })

    # 8. Phiếu lương
    def test_14_thirteen_month_pay_year_2(self):
        """
        Sửa phiếu lương tháng 13 với năm < 1970 hoặc năm >= 9999

        => Thông báo ngoại lệ
        """
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-1-1'),
            fields.Date.to_date('2021-12-31'),
            thirteen_month_pay=True)

        with self.assertRaises(UserError):
            payslip.write({
                'thirteen_month_pay_year': 1969
            })
        with self.assertRaises(UserError):
            payslip.write({
                'thirteen_month_pay_year': 9999
            })
