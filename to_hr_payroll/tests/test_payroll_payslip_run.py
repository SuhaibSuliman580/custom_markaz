from odoo import fields
from odoo.exceptions import ValidationError, UserError
from odoo.tests import tagged, Form

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollPayslipRun(TestPayrollCommon):

    def create_payslip_run(self, name='', start=False, end=False):
        return self.env['hr.payslip.run'].create({
            'name': name or 'Test 1',
            'date_start': start or fields.Date.to_date('2021-7-1'),
            'date_end': end or fields.Date.to_date('2021-7-31'),
            'salary_cycle_id': self.env.company.salary_cycle_id.id
            })

    def test_01_salary_cycle_id(self):
        """
        Test: Chu kỳ lương của bảng lương lấy theo thiết lập công ty
        Input:
            Công ty có thiết lập chu kỳ lương
            Tạo bảng lương
        Output: chu kỳ lương mặc định được thiết lập trên công ty
        """
        f = Form(self.env['hr.payslip.run'])
        self.assertEqual(f.salary_cycle_id, self.env.company.salary_cycle_id, 'Test salary_cycle_id field not ok')

    def test_02_payslip_run_date(self):
        """
        Test: Tạo bảng lương với Ngày bắt đầu phải nhỏ hơn ngày kết thúc
            TH1: Ngày bắt đầu < ngày kết thúc
                => Tạo thành công
            TH2: Ngày bắt đầu > ngày kết thúc
                => Tạo không thành công
        """
        PayslipRun = self.env['hr.payslip.run']

        # TH1: Ngày bắt đầu < ngày kết thúc
        result1 = PayslipRun.create({
            'name': 'Test 1',
            'date_start': fields.Date.to_date('2021-7-1'),
            'date_end': fields.Date.to_date('2021-7-31'),
            'salary_cycle_id': self.env.company.salary_cycle_id.id,
        })
        self.assertTrue(result1, 'Test Payslip Batch: date_start < date_end not ok')

        # TH2: Ngày bắt đầu > ngày kết thúc
        vals = {
            'name': 'Test 2',
            'date_start': fields.Date.to_date('2021-9-1'),
            'date_end': fields.Date.to_date('2021-8-8'),
            'salary_cycle_id': self.env.company.salary_cycle_id.id
        }
        self.assertRaises(ValidationError, PayslipRun.create, vals)

    def test_03_payslip_run__compute_date(self):
        """
        Test: Adjust `Start Date` of payslips Batchs
            => Recalculate field `End Date`
        """
        batch = self.create_payslip_run('New Payslips Batchs')

        batch.write({'date_start': fields.Date.to_date('2021-08-01')})
        self.assertEqual(batch.date_end, fields.Date.to_date('2021-08-31'))
        batch.write({'date_start': fields.Date.to_date('2021-07-15')})
        self.assertEqual(batch.date_end, fields.Date.to_date('2021-08-14'))

    def test_04_change_payslip_batches_01(self):
        """
        Test: Thay đổi chu kỳ bảng lương không thành công khi bảng lương đã có phiếu lương
        """
        # batch_1: 1/7/2021 -> 31/7/2021
        batches = self.create_payslip_run()
        # Create wizard
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': batches.id,
            'mode': 'batch_period',
            'employee_ids': [(6, 0, self.product_emp_A.ids)]
        })
        # Generate Payslips
        wizard.compute_sheet()
        self.assertTrue(batches.slip_ids)
        with self.assertRaises(UserError):
            batches.write({'date_start': fields.Date.to_date('2021-08-01')})

    def test_05_generate_payslip_1(self):
        """
        Test: Tạo nhanh phiếu lương cho nhiều người, chế độ chu kỳ bảng lương
        Output:
            Tạo thành công các phiếu lương và được tham chiếu đến bảng lương này
            Các phiếu lương là các phiếu lương có hợp đồng, thời gian hợp lệ với khoảng thời gian trên bảng lương.
            khoảng thời gian trên phiếu lương giống với khoảng thời gian của bảng lương
        """
        # Prepare data
        # manager's contract
        self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-1-1'),
            fields.Date.to_date('2021-7-15'))
        # new employee
        employee_3 = self.create_employee('Project Employee 1')
        employees = self.env['hr.employee'].search([('company_id', '=', self.env.company.id)])

        # batch_1: 1/7/2021 -> 31/7/2021
        batch_1 = self.create_payslip_run()
        # Create wizard
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': batch_1.id,
            'mode': 'batch_period',
            'employee_ids': [(6, 0, employees.ids)]
        })
        # Generate Payslips
        wizard.compute_sheet()

        # Test
        payslip_1 = batch_1.slip_ids.filtered(lambda r: r.employee_id == self.product_emp_A)
        self.assertTrue(payslip_1, 'Test Generate Payslips not ok')
        self.assertEqual(payslip_1.date_from, fields.Date.to_date('2021-7-1'), 'Test Generate Payslips not ok')
        self.assertEqual(payslip_1.date_to, fields.Date.to_date('2021-7-31'), 'Test Generate Payslips not ok')
        self.assertEqual(payslip_1.state, 'draft', 'Test Generate Payslips not ok')

        payslip_2 = batch_1.slip_ids.filtered(lambda r: r.employee_id == self.product_dep_manager)
        self.assertTrue(payslip_2, 'Test Generate Payslips not ok')
        self.assertEqual(payslip_2.date_from, fields.Date.to_date('2021-7-1'), 'Test Generate Payslips not ok')
        self.assertEqual(payslip_2.date_to, fields.Date.to_date('2021-7-31'), 'Test Generate Payslips not ok')
        self.assertEqual(payslip_2.state, 'draft', 'Test Generate Payslips not ok')

        payslip_3 = batch_1.slip_ids.filtered(lambda r: r.employee_id == employee_3)
        self.assertFalse(payslip_3, 'Test Generate Payslips not ok')
        batch_1.action_verify_payslips()

    def test_05_generate_payslip_2(self):
        """
        Test: Tạo nhanh phiếu lương cho nhiều người, chế độ thời hạn hợp đồng
        Output:
            Tạo thành công các phiếu lương và được tham chiếu đến bảng lương này
            Các phiếu lương là các phiếu lương có hợp đồng, thời gian hợp lệ với khoảng thời gian trên bảng lương.
            Thời gian kết thúc của phiếu lương được tính dựa theo thời gian kết thúc của hợp đồng,
                nếu thời gian kết thúc trên bảng lương > thời gian kết thúc hợp đồng
                    => thời gian kết thúc phiếu lương là thời gian kết thúc hợp đồng
        """
        # Prepare data
        # manager's contract
        self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-1-1'),
            fields.Date.to_date('2021-7-15'),
            'open')
        # new employee
        employee_3 = self.create_employee('Project Employee 1')
        employees = self.env['hr.employee'].search([('company_id', '=', self.env.company.id)])

        # batch_1: 1/7/2021 -> 31/7/2021
        batch_1 = self.create_payslip_run()
        # Create wizard
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': batch_1.id,
            'mode': 'contract_period',
            'employee_ids': [(6, 0, employees.ids)]
        })
        # Generate Payslips
        wizard.compute_sheet()

        # Test
        payslip_1 = batch_1.slip_ids.filtered(lambda r: r.employee_id == self.product_emp_A)
        self.assertTrue(payslip_1, 'Test Generate Payslips not ok')
        self.assertEqual(payslip_1.date_from, fields.Date.to_date('2021-7-1'), 'Test Generate Payslips not ok')
        self.assertEqual(payslip_1.date_to, fields.Date.to_date('2021-7-31'), 'Test Generate Payslips not ok')
        self.assertEqual(payslip_1.state, 'draft', 'Test Generate Payslips not ok')

        payslip_2 = batch_1.slip_ids.filtered(lambda r: r.employee_id == self.product_dep_manager)
        self.assertTrue(payslip_2, 'Test Generate Payslips not ok')
        self.assertEqual(payslip_2.date_from, fields.Date.to_date('2021-7-1'), 'Test Generate Payslips not ok')
        self.assertEqual(payslip_2.date_to, fields.Date.to_date('2021-7-15'), 'Test Generate Payslips not ok')
        self.assertEqual(payslip_2.state, 'draft', 'Test Generate Payslips not ok')

        payslip_3 = batch_1.slip_ids.filtered(lambda r: r.employee_id == employee_3)
        self.assertFalse(payslip_3, 'Test Generate Payslips not ok')
        batch_1.action_verify_payslips()

    def test_05_generate_payslip_3(self):
        """
        Test: Tạo bảng lương cho nhân viên có nhiều hợp đồng trong 1 tháng
        Input:
            Tạo bảng lương cho nhiều nhân viên, nhân viên có nhiều hợp đồng trong 1 tháng.
                - Các hợp đồng của nhân viên là giống nhau. (chức vụ, phòng ban, cấu trúc lương, công ty)
        Output:
            Nhân viên có nhiều hợp đồng trong 1 tháng sẽ có 1 phiếu lương
        """
        # Prepare data
        # manager's contract
        self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-01-01'),
            fields.Date.to_date('2021-07-15'),
            state='close')
        self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-07-16'),
            state='open')
        # new employee
        employee_3 = self.create_employee('Project Employee 1')
        employees = self.env['hr.employee'].search([('company_id', '=', self.env.company.id)])

        # payslip_batch: 1/7/2021 -> 31/7/2021
        payslip_batch = self.create_payslip_run()
        # Create wizard
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': payslip_batch.id,
            'mode': 'contract_period',
            'employee_ids': [(6, 0, employees.ids)]
        })
        # Generate Payslips
        wizard.compute_sheet()

        # Test
        manager_payslips = payslip_batch.slip_ids.filtered(lambda r: r.employee_id == self.product_dep_manager)
        self.assertRecordValues(
            manager_payslips,
            [{
                'date_from': fields.Date.to_date('2021-07-01'),
                'date_to': fields.Date.to_date('2021-07-31')
            }])
        emp_A_payslips = payslip_batch.slip_ids.filtered(lambda r: r.employee_id == self.product_dep_manager)
        self.assertRecordValues(
            emp_A_payslips,
            [{
                'date_from': fields.Date.to_date('2021-07-01'),
                'date_to': fields.Date.to_date('2021-07-31')
            }])
        emp3_payslips = payslip_batch.slip_ids.filtered(lambda r: r.employee_id == employee_3)
        self.assertFalse(emp3_payslips)
        payslip_batch.action_verify_payslips()

    def test_05_generate_payslip_4(self):
        """
        Test: Tạo bảng lương cho nhân viên có nhiều hợp đồng trong 1 tháng
        Input:
            Tạo bảng lương cho nhiều nhân viên, nhân viên có nhiều hợp đồng trong 1 tháng.
                - Các hợp đồng của nhân viên là khác nhau. (chức vụ, phòng ban, cấu trúc lương, công ty, )
        Output:
            Nhân viên có nhiều hợp đồng trong 1 tháng sẽ có nhiều phiếu lương tương ứng theo khoảng hợp đồng
                HĐ 1 và 3 giống nhau, HĐ 2 khác HĐ 1 và 3
                => 3 phiếu lương tương ứng với từng hợp đồng
        """
        # Prepare data
        # manager's contract
        contract_1 = self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-01-01'),
            fields.Date.to_date('2021-07-10'),
            state='close')
        contract_2 = self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-07-11'),
            fields.Date.to_date('2021-07-20'),
            state='open')
        contract_3 = self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-07-21'),
            fields.Date.to_date('2021-07-31'),
            state='open')
        contract_1.job_id = self.job_product_dev
        contract_2.job_id = self.job_product_manager
        contract_3.job_id = self.job_product_dev

        # payslip_batch: 1/7/2021 -> 31/7/2021
        payslip_batch = self.create_payslip_run()
        # Create wizard
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': payslip_batch.id,
            'mode': 'contract_period',
            'employee_ids': [(6, 0, self.product_dep_manager.ids)]
        })
        wizard.compute_sheet()
        payslips = payslip_batch.slip_ids.filtered(lambda r: r.employee_id == self.product_dep_manager)

        self.assertRecordValues(
            payslips,
            [{
                'date_from': fields.Date.to_date('2021-07-01'),
                'date_to': fields.Date.to_date('2021-07-10')
            },
            {
                'date_from': fields.Date.to_date('2021-07-21'),
                'date_to': fields.Date.to_date('2021-07-31')
            },
            {
                'date_from': fields.Date.to_date('2021-07-11'),
                'date_to': fields.Date.to_date('2021-07-20')
            }])
        payslip_batch.action_verify_payslips()

    def test_05_generate_payslip_5(self):
        """
        Test: Tạo bảng lương cho nhân viên có nhiều hợp đồng trong 1 tháng
        Input:
            Tạo bảng lương cho nhiều nhân viên, nhân viên có nhiều hợp đồng trong 1 tháng.
                - Các hợp đồng của nhân viên là khác nhau. (chức vụ, phòng ban, cấu trúc lương, công ty, )
        Output:
            Nhân viên có nhiều hợp đồng trong 1 tháng sẽ có nhiều phiếu lương tương ứng theo khoảng hợp đồng
                HĐ 2 và 3 giống nhau, HĐ 1 khác HĐ 2 và 3
                => 2 phiếu lương: phiếu lương 1 - HĐ 1, phiếu lương 2 - HĐ 2 và 3
        """
        # Prepare data
        # manager's contract
        contract_1 = self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-01-01'),
            fields.Date.to_date('2021-07-10'),
            state='close')
        contract_2 = self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-07-11'),
            fields.Date.to_date('2021-07-20'),
            state='open')
        contract_3 = self.create_contract(
            self.product_dep_manager.id,
            fields.Date.to_date('2021-07-21'),
            fields.Date.to_date('2021-07-31'),
            state='open')
        contract_1.job_id = self.job_product_manager
        contract_2.job_id = self.job_product_dev
        contract_3.job_id = self.job_product_dev

        # payslip_batch: 1/7/2021 -> 31/7/2021
        payslip_batch = self.create_payslip_run()
        # Create wizard
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': payslip_batch.id,
            'mode': 'contract_period',
            'employee_ids': [(6, 0, self.product_dep_manager.ids)]
        })
        wizard.compute_sheet()
        payslips = payslip_batch.slip_ids.filtered(lambda r: r.employee_id == self.product_dep_manager)

        self.assertRecordValues(
            payslips,
            [{
                'date_from': fields.Date.to_date('2021-07-01'),
                'date_to': fields.Date.to_date('2021-07-10')
            },
            {
                'date_from': fields.Date.to_date('2021-07-11'),
                'date_to': fields.Date.to_date('2021-07-31')
            }])
        payslip_batch.action_verify_payslips()

    def test_06_payslip_run_duplicate(self):
        """
        Test: bảng lương không thể nhân bản
        Input: nhân bản bảng lương
        Output: Thông báo ngoại lệ
        """
        batch_1 = self.create_payslip_run()
        self.assertRaises(UserError, batch_1.copy)

    def test_07_payslip_run_unlink_1(self):
        """
        Test xóa bảng lương thành công khi chưa có phiếu lương nào
        TH1: bảng lương k có phiếu lương nào, tất cả trạng thái đều xóa đc
            Output: Xóa thành công
        """
        # draft
        batch_1 = self.create_payslip_run()
        self.assertTrue(batch_1.unlink(), 'Test Unlink: Payslip Batch not ok')

        # Verified
        batch_2 = self.create_payslip_run()
        batch_2.action_verify_payslips()
        self.assertTrue(batch_2.unlink(), 'Test Unlink: Payslip Batch not ok')

        # Close
        batch_3 = self.create_payslip_run()
        batch_3.close_payslip_run()
        self.assertTrue(batch_3.unlink(), 'Test Unlink: Payslip Batch not ok')

        # Cancel
        batch_4 = self.create_payslip_run()
        batch_4.action_cancel()
        self.assertTrue(batch_4.unlink(), 'Test Unlink: Payslip Batch not ok')

    def test_07_payslip_run_unlink_2(self):
        """
        Test xóa bảng lương không thành công khi đã có phiếu lương ở trạng thái khác dự thảo
        TH2: Bảng lương có phiếu lương và ở trạng thái bảng lương khác dự thảo
            Output: Xóa không thành công
        """
        batch_1 = self.create_payslip_run()
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': batch_1.id,
            'mode': 'batch_period',
            'employee_ids': [(6, 0, self.product_emp_A.ids)]
            })
        # Generate Payslips
        wizard.compute_sheet()

        batch_1.action_verify_payslips()
        self.assertRaises(UserError, batch_1.unlink)

    # 9. Bảng lương
    def test_07_payslip_run_unlink_3(self):
        """
        Test xóa bảng lương thành công khi phiếu lương ở trạng thái dự thảo
        TH3: Bảng lương có phiếu lương và ở trạng thái dự thảo, có phiếu lương ở trạng thái "dự thảo"
            Output: Xóa thành công bảng lương và các phiếu lương
        """
        batch_1 = self.create_payslip_run()
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': batch_1.id,
            'mode': 'batch_period',
            'employee_ids': [(6, 0, self.product_emp_A.ids)]
            })
        # Generate Payslips
        wizard.compute_sheet()

        self.assertTrue(batch_1.unlink(), 'Test Unlink: Payslip Batch not ok')
        self.assertFalse(batch_1.slip_ids.exists(), 'Test Unlink: Payslip Batch not ok')

    def test_07_payslip_run_unlink_4(self):
        """
        Test xóa bảng lương thành công khi phiếu lương ở trạng thái hủy
        TH6: Bảng lương có phiếu lương và ở trạng thái dự thảo, có phiếu lương ở trạng thái "hủy"
            Output: Xóa thành công bảng lương và các phiếu lương
        """
        batch_1 = self.create_payslip_run()
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': batch_1.id,
            'mode': 'batch_period',
            'employee_ids': [(6, 0, self.product_emp_A.ids)]
            })
        # Generate Payslips
        wizard.compute_sheet()

        batch_1.slip_ids.action_payslip_cancel()
        self.assertTrue(batch_1.unlink(), 'Test Unlink: Payslip Batch not ok')
        self.assertFalse(batch_1.slip_ids.exists(), 'Test Unlink: Payslip Batch not ok')

    def test_07_payslip_run_unlink_5(self):
        """
        Test xóa bảng lương không thành công khi phiếu lương ở trạng thái chờ đợi/hoàn thành
        TH4: Bảng lương có phiếu lương và ở trạng thái dự thảo, có phiếu lương ở trạng thái "chờ đợi"
            Output: Xóa không thành công
        TH5: Bảng lương có phiếu lương và ở trạng thái dự thảo, có phiếu lương ở trạng thái "hoàn thành"
            Output: Xóa không thành công
        """
        batch_1 = self.create_payslip_run()
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': batch_1.id,
            'mode': 'batch_period',
            'employee_ids': [(6, 0, self.product_emp_A.ids)]
            })
        # Generate Payslips
        wizard.compute_sheet()

        # TH4
        batch_1.slip_ids.action_payslip_verify()
        self.assertRaises(UserError, batch_1.unlink)
        # TH5
        batch_1.slip_ids.action_payslip_done()
        self.assertRaises(UserError, batch_1.unlink)

    # 9. Bảng lương
    def test_08_payslip_run_action_compute_sheets(self):
        """
        Test hành động tính toán hàng loạt phiếu lương (Compute Payslip Batch)
            TH2: Bảng lương ở trạng thái Dự thảo, các phiếu lương ở trạng thái dự thảo
                Ouput: Xuất hiện nút tính toán bảng lương (Compute Payslip Batch), khi nhấn vào sẽ tính toán toàn bộ các phiếu lương

            TH1: Bảng lương ở trạng thái Dự thảo, có bất kỳ phiếu 1 ương khác trạng thái dự thảo
                Ouput: Xuất hiện nút tính toán bảng lương (Compute Payslip Batch), khi nhấn vào sẽ thông báo ngoại lệ
        """
        batch_1 = self.create_payslip_run()
        # TH2: payslip_1: draft
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-10'))
        payslip_1.write({'payslip_run_id': batch_1.id})
        batch_1.action_compute_sheets()

        # TH1: payslip_2: cancel
        payslip_1.action_payslip_cancel()
        self.assertRaises(UserError, batch_1.action_compute_sheets)

    def test_09_payslip_run_action_refund_sheet(self):
        """
        Test: Check the refund action of payslip in the payslips batch
            Expect: Successfully created a refund payslip
        """
        batch = self.create_payslip_run()
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2022-8-25'),
            fields.Date.to_date('2022-8-30'))
        batch.write({'slip_ids': [(6, 0, [payslip.id])]})
        batch.action_verify_payslips()
        payslip.with_context({
            'default_thirteen_month_pay': batch.thirteen_month_pay,
            'default_date_from': batch.date_start,
            'default_date_to': batch.date_end,
            'default_payslip_run_id': batch.id,
        }).refund_sheet()
        self.assertTrue(payslip.refund_ids)

    def test_10_payslip_run_action_close_0(self):
        """
        Test: hành động đóng bảng lương
            => Trạng thái của bảng lương là "Đóng"
        """
        batch_1 = self.create_payslip_run()
        batch_1.close_payslip_run()
        self.assertEqual(batch_1.state, 'close', 'Test action: close_payslip_run() not ok')

    def test_10_payslip_run_action_close_01(self):
        """
        Test: Check payroll closing action with draft pay slip
            Expect: Raise UserError
        """
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-10'))
        batch = self.create_payslip_run()
        batch.write({'slip_ids': [(6, 0, [payslip.id])]})
        with self.assertRaises(UserError):
            batch.close_payslip_run()

    def test_10_payslip_run_action_close_02(self):
        """
        Test: Check payroll closing action with cancel pay slip
            Expect: Raise UserError
        """
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-21'),
            fields.Date.to_date('2021-7-31'))
        payslip.action_payslip_verify()
        payslip.action_payslip_cancel()
        batch = self.create_payslip_run()
        batch.write({'slip_ids': [(6, 0, [payslip.id])]})
        with self.assertRaises(UserError):
            batch.close_payslip_run()

    def test_10_payslip_run_action_close_03(self):
        """
        Test: Check payroll closing action with verify pay slip
            Expect: payslip's state changes to done
        """
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-11'),
            fields.Date.to_date('2021-7-20'))
        payslip.action_payslip_verify()
        batch = self.create_payslip_run()
        batch.write({'slip_ids': [(6, 0, [payslip.id])]})
        batch.close_payslip_run()
        self.assertEqual(batch.slip_ids.state, 'done')

    def test_11_payslip_run_action_verify(self):
        """
        Test: Xác nhận trạng thái phiếu lương khi xác nhận bảng lương
            Input: Xác nhận bảng lương
            Output:
                Tất cả phiếu lương trong bảng lương ở trạng thái dự thảo chuyển sang trạng thái Đang đợi
                Các phiếu lương ở trạng thái khác dự thảo không thay đổi trạng thái
        """
        # 3 employees - 3 contracts
        # self.product_emp_A.id
        # self.product_dep_manager.id
        # employee_3
        employee_3 = self.create_employee('Product Employee 3')
        self.create_contract(employee_3.id, fields.Date.to_date('2021-1-1'))
        self.create_contract(self.product_dep_manager.id, fields.Date.to_date('2021-1-1'))

        # salary batch
        batch_1 = self.create_payslip_run()
        # Create wizard with 3 employees
        employees_ids = [self.product_emp_A.id, self.product_dep_manager.id, employee_3.id]
        wizard = self.env['hr.payslip.employees'].create({
            'batch_id': batch_1.id,
            'mode': 'batch_period',
            'employee_ids': [(6, 0, employees_ids)]
        })
        # Generate Payslips
        wizard.compute_sheet()

        # payslip_2: cancel
        batch_1.slip_ids[1].action_payslip_verify()
        batch_1.slip_ids[1].action_payslip_cancel()

        # payslip_3: done
        batch_1.slip_ids[2].action_payslip_verify()
        batch_1.slip_ids[2].action_payslip_done()

        # payslip_1: draft
        # Xác nhận bảng lương
        batch_1.action_verify_payslips()

        self.assertEqual(batch_1.state, 'verified', 'Test action_payslip_verify() on payslip batch not ok')
        self.assertEqual(batch_1.slip_ids[0].state, 'verify', 'Test action_payslip_verify() on payslip batch not ok')
        self.assertEqual(batch_1.slip_ids[1].state, 'cancel', 'Test action_payslip_verify() on payslip batch not ok')
        self.assertEqual(batch_1.slip_ids[2].state, 'done', 'Test action_payslip_verify() on payslip batch not ok')

    def test_12_payslip_run_action_cancel(self):
        """
        Test: Xác nhận trạng thái phiếu lương khi hủy bảng lương
            Input: Hủy bảng lương
            Output: Tất cả phiếu lương trong bảng lương chuyển sang trạng thái Bị từ chối
        """
        batch_1 = self.create_payslip_run()
        # payslip_1: draft
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-10'))

        # payslip_2: verify
        payslip_2 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-11'),
            fields.Date.to_date('2021-7-20'))
        payslip_2.action_payslip_verify()

        # payslip_3: done
        payslip_3 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-21'),
            fields.Date.to_date('2021-7-31'))
        payslip_3.action_payslip_verify()
        payslip_3.action_payslip_done()

        batch_1.write({'slip_ids': [(6, 0, [payslip_1.id, payslip_2.id, payslip_3.id])]})
        batch_1.action_cancel()

        self.assertEqual(batch_1.state, 'cancelled', 'Test action_cancel() on payslip batch not ok')
        self.assertEqual(payslip_1.state, 'cancel', 'Test action_cancel() on payslip batch not ok')
        self.assertEqual(payslip_2.state, 'cancel', 'Test action_cancel() on payslip batch not ok')
        self.assertEqual(payslip_3.state, 'cancel', 'Test action_cancel() on payslip batch not ok')
