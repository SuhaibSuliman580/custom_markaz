from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollSecurity(TestPayrollCommon):

    def setUp(self):
        super(TestPayrollSecurity, self).setUp()

        # group user
        group_internal = self.env.ref('base.group_user')
        group_team_leader = self.env.ref('to_hr_payroll.group_hr_payroll_team_leader')
        group_payroll_user = self.env.ref('to_hr_payroll.group_hr_payroll_user')
        group_payroll_manager = self.env.ref('to_hr_payroll.group_hr_payroll_admin')
        group_contract_manager = self.env.ref('hr_contract.group_hr_contract_manager')
        # User - employee
        groups_ids = [group_internal.id, group_team_leader.id]
        self.leader_user = self.create_user('Leader User', 'leader_user', 'leader_user', groups_ids)
        self.leader_user.action_create_employee()
        self.leader_employee = self.leader_user.employee_id

        groups_ids = [group_internal.id, group_payroll_user.id]
        self.officer_user = self.create_user('Officer User', 'officer_user', 'officer_user', groups_ids)
        self.officer_user.action_create_employee()
        self.officer_employee = self.officer_user.employee_id

        groups_ids = [group_internal.id, group_payroll_manager.id]
        self.manager_user = self.create_user('Manager User', 'manager_user', 'manager_user', groups_ids)
        self.manager_user.action_create_employee()
        self.manager_employee = self.manager_user.employee_id

        groups_ids = [group_internal.id]
        self.product_user_1 = self.create_user('Product Employee 1', 'product_employee1', 'product_employee1', groups_ids)
        self.product_user_1.action_create_employee()
        self.product_employee_1 = self.product_user_1.employee_id

        self.product_user_2 = self.create_user('Product Employee 2', 'product_employee2', 'product_employee2', groups_ids)
        self.product_user_2.action_create_employee()
        self.product_employee_2 = self.product_user_2.employee_id

        self.product_department_user = self.create_user(
            'Product Department Manager',
            'product_department_user',
            'product_department_user',
            groups_ids)
        self.contract_manager = self.create_user(
            'Contract Manger', 'contract_manager', 'contract_manager', group_contract_manager.ids
        )
        self.contract_employee_1 = self.create_contract(
            self.product_employee_1.id,
            fields.Date.to_date('2021-1-1'),
            wage=35000000)
        self.contract_employee_2 = self.create_contract(
            self.product_employee_2.id,
            fields.Date.to_date('2021-1-1'),
            wage=35000000)
        self.contract_team_leader = self.create_contract(
            self.leader_employee.id,
            fields.Date.to_date('2021-1-1'),
            wage=35000000)
        self.contract_officer_employee = self.create_contract(
            self.officer_employee.id,
            fields.Date.to_date('2021-1-1'),
            wage=35000000)
        # generate Work entries in the past
        contracts = self.contract_employee_1 | self.contract_employee_2 | self.contract_team_leader | self.contract_officer_employee
        self.generate_work_entry(
            contracts,
            fields.Datetime.to_datetime('2021-06-01 00:00:00'),
            fields.Datetime.to_datetime('2021-07-31 23:59:59'))

    def test_01_payroll_security_internal_user_1(self):
        """
        Test: Check quyền truy cập của người dùng nội bộ (Access Rights)
            TH1: Check quyền truy cập model Payslip
                => chỉ có quyền đọc
            TH2: Check quyền truy cập model Payslip Personal Income Tax Analysis
                => chỉ có quyền đọc
            TH3: Check quyền truy cập model Payroll Analysis
                => không có quyền xem, tạo, sửa, xóa
        """
        # TH1: Check quyền truy cập model Payslip (Access Rights)
        Payslip = self.env['hr.payslip'].with_user(self.product_user_1)
        self.assertTrue(Payslip.check_access_rights('read'), 'Test Access Right (Payslip) for internal user not ok')
        self.assertRaises(AccessError, Payslip.check_access_rights, 'create')
        self.assertRaises(AccessError, Payslip.check_access_rights, 'write')
        self.assertRaises(AccessError, Payslip.check_access_rights, 'unlink')

        # TH2: Check quyền truy cập model Payslip Personal Income Tax Analysis
        TaxAnalysis = self.env['payslip.personal.income.tax.analysis'].with_user(self.product_user_1)
        self.assertTrue(TaxAnalysis.check_access_rights('read'), 'Test Access Right (Payslip) for internal user not ok')
        self.assertRaises(AccessError, TaxAnalysis.check_access_rights, 'create')
        self.assertRaises(AccessError, TaxAnalysis.check_access_rights, 'write')
        self.assertRaises(AccessError, TaxAnalysis.check_access_rights, 'unlink')

        # TH3: Check quyền truy cập model Payroll Analysis
        PayrollAnalysis = self.env['hr.payroll.analysis'].with_user(self.product_user_1)
        self.assertRaises(AccessError, PayrollAnalysis.check_access_rights, 'read')
        self.assertRaises(AccessError, PayrollAnalysis.check_access_rights, 'create')
        self.assertRaises(AccessError, PayrollAnalysis.check_access_rights, 'write')
        self.assertRaises(AccessError, PayrollAnalysis.check_access_rights, 'unlink')

    def test_01_payroll_security_internal_user_2(self):
        """
        Test: Check quyền truy cập bản ghi Payslip (Access Rules) của người dùng nội bộ
            TH1: Phiếu lương của chính mình, Thuế thu nhập cá nhân của chính mình
                => Xem thành công
            TH2: Phiếu lương, thuế thu nhập cá nhân của người khác
                => Không thành công
        """
        # Prepare data for test access rule
        payslip_1 = self.create_payslip(
            self.product_employee_1.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))

        payslip_2 = self.create_payslip(
            self.product_employee_2.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        (payslip_1 | payslip_2).compute_sheet()

        # TH1: Phiếu lương của chính mình
        self.assertIsNone(payslip_1.with_user(
            self.product_user_1).check_access_rule('read'),
            'Test access rule (Payslip) for internal user not ok')
        # Xem bản ghi báo cáo thuế của chính mình
        taxs = self.env['payslip.personal.income.tax.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_1_taxs = taxs.filtered(lambda r: r.employee_id == self.product_employee_1)
        self.assertIsNone(
            employee_1_taxs.with_user(self.product_user_1).check_access_rule('read'),
            'Test access rule (Payslip Personal Income Tax Analysis) for internal user not ok')

        # TH2: Phiếu lương của người khác
        self.assertRaises(AccessError, payslip_2.with_user(self.product_user_1).check_access_rule, 'read')
        employee_2_taxs = taxs.filtered(lambda r: r.employee_id == self.product_employee_2)
        # Xem bản ghi báo cáo thuế của người khác
        with self.assertRaises(AccessError):
            employee_2_taxs.with_user(self.product_user_1).read(['id'])

    def test_02_payroll_security_team_leader_1(self):
        """
        Test: Check quyền truy cập bản ghi Payslip (Access Rules) của nhóm người dùng trưởng nhóm
        Input:
            Đọc Phiếu lương, thuế thu nhập cá nhân, phân tích lương của chính mình
        Output: Thành công
        """
        payslip = self.create_payslip(
            self.leader_employee.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertIsNone(
            payslip.with_user(self.leader_user).check_access_rule('read'),
            'Test access rule (Payslip) for team leader not ok')

        payslip.compute_sheet()
        lines = self.env['payslip.personal.income.tax.analysis'].search([('company_id', '=', self.env.company.id)])
        leader_employee_taxs = lines.filtered(lambda r: r.employee_id == self.leader_employee)
        self.assertIsNone(
            leader_employee_taxs.with_user(self.leader_user).check_access_rule('read'),
            'Test access rule (Payslip Personal Income Tax Analysis) for team leader not ok')

        lines = self.env['hr.payroll.analysis'].search([('company_id', '=', self.env.company.id)])
        leader_employee_lines = lines.filtered(lambda r: r.employee_id == self.leader_employee)
        self.assertIsNone(
            leader_employee_lines.with_user(self.leader_user).check_access_rule('read'),
            'Test access rule (Payroll Analysis) for team leader not ok')

    def test_02_payroll_security_team_leader_2(self):
        """
        Test: Check quyền truy cập bản ghi Payslip (Access Rules) của nhóm người dùng trưởng nhóm
        Input:
            Đọc Phiếu lương, thuế thu nhập cá nhân, phân tích lương của cấp dưới
        Output: Thành công
        """
        self.product_employee_2.write({'parent_id': self.leader_employee.id})
        payslip = self.create_payslip(
            self.product_employee_2.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))

        self.assertIsNone(
            payslip.with_user(self.leader_user).check_access_rule('read'),
            'Test access rule (Payslip) for team leader not ok')

        payslip.compute_sheet()
        lines = self.env['payslip.personal.income.tax.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_2_taxs = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertIsNone(
            employee_2_taxs.with_user(self.leader_user).check_access_rule('read'),
            'Test access rule (Payslip Personal Income Tax Analysis) for team leader not ok')

        lines = self.env['hr.payroll.analysis'].search([('company_id', '=', self.env.company.id)])
        leader_employee_lines = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertIsNone(
            leader_employee_lines.with_user(self.leader_user).check_access_rule('read'),
            'Test access rule (Payroll Analysis) for team leader not ok')

    def test_02_payroll_security_team_leader_3(self):
        """
        Test: Check quyền truy cập bản ghi Payslip (Access Rules) của nhóm người dùng trưởng nhóm
        Input:
            Đọc Phiếu lương, thuế thu nhập cá nhân, phân tích lương thuộc phòng ban mình quản lý
        Output: Thành công
        """
        self.product_employee_2.write({
            'department_id': self.product_department.id,
            'parent_id': False
        })
        self.product_department.write({
            'manager_id': self.leader_employee.id
        })
        payslip = self.create_payslip(
            self.product_employee_2.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertIsNone(
            payslip.with_user(self.leader_user).check_access_rule('read'),
            'Test access rule (Payslip) for team leader not ok')

        payslip.compute_sheet()
        lines = self.env['payslip.personal.income.tax.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_2_taxs = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertIsNone(
            employee_2_taxs.with_user(self.leader_user).check_access_rule('read'),
            'Test access rule (Payslip Personal Income Tax Analysis) for team leader not ok')

        lines = self.env['hr.payroll.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_2_lines = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertIsNone(
            employee_2_lines.with_user(self.leader_user).check_access_rule('read'),
            'Test access rule (Payroll Analysis) for team leader not ok')

    def test_02_payroll_security_team_leader_4(self):
        """
        Test: Check quyền truy cập bản ghi Payslip (Access Rules) của nhóm người dùng trưởng nhóm
        Input:
            - Đọc Phiếu lương, thuế thu nhập cá nhân, phân tích lương của nhân viên A
            - không phải là trường phòng hoặc quản lý của nhân viên A
        Output: Không Thành công
        """
        payslip = self.create_payslip(
            self.product_employee_2.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertRaises(AccessError, payslip.with_user(self.leader_user).check_access_rule, 'read')

        payslip.compute_sheet()
        lines = self.env['payslip.personal.income.tax.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_2_taxs = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertRaises(AccessError, employee_2_taxs.with_user(self.leader_user).check_access_rule, 'read')

    def test_03_payroll_security_officer_1(self):
        """
        Test: Check quyền truy cập của Cán bộ bảng lương (Access Rights)
            TH1: Check quyền truy cập model Payslip
                => Có thể Xem, tạo, sửa, xóa
            TH2: Check quyền truy cập model Payslip Personal Income Tax Analysis
            TH3: Check quyền truy cập model Payroll Analysis
            TH4: Check quyền truy cập model Payroll Contribution Analysis
        """
        # TH1: Check quyền truy cập model Payslip
        Payslip = self.env['hr.payslip'].with_user(self.officer_user)
        self.assertTrue(Payslip.check_access_rights('read'), 'Test Access Right (Payslip) for officer not ok')
        self.assertTrue(Payslip.check_access_rights('create'), 'Test Access Right (Payslip) for officer not ok')
        self.assertTrue(Payslip.check_access_rights('write'), 'Test Access Right (Payslip) for officer not ok')
        self.assertTrue(Payslip.check_access_rights('unlink'), 'Test Access Right (Payslip) for officer not ok')

        # TH2: Check quyền truy cập model Payslip Personal Income Tax Analysis
        TaxAnalysis = self.env['payslip.personal.income.tax.analysis'].with_user(self.officer_user)
        self.assertTrue(TaxAnalysis.check_access_rights('read'), 'Test Access Right (Payslip) for officer not ok')

        # TH3: Check quyền truy cập model Payroll Analysis
        PayrollAnalysis = self.env['hr.payroll.analysis'].with_user(self.officer_user)
        self.assertTrue(PayrollAnalysis.check_access_rights('read'), 'Test Access Right (Payroll Analysis) for officer not ok')

    def test_03_payroll_security_officer_2(self):
        """
        Tets: Check quyền truy cập bản ghi Payslip (Access Rules) của cán bộ bảng lương
        Input: Phiếu lương, thuế, phân tích lương của nhân viên cấp dưới
        Output: Full quyền
        """
        payslip = self.create_payslip(
            self.officer_employee.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('read'))
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('write'))
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('unlink'))

        payslip.compute_sheet()
        lines = self.env['payslip.personal.income.tax.analysis'].search([('company_id', '=', self.env.company.id)])
        leader_employee_taxs = lines.filtered(lambda r: r.employee_id == self.officer_employee)
        self.assertIsNone(leader_employee_taxs.with_user(self.officer_user).check_access_rule('read'))

        lines = self.env['hr.payroll.analysis'].search([('company_id', '=', self.env.company.id)])
        leader_employee_lines = lines.filtered(lambda r: r.employee_id == self.officer_employee)
        self.assertIsNone(leader_employee_lines.with_user(self.officer_user).check_access_rule('read'))

    def test_03_payroll_security_officer_3(self):
        """
        Tets: Check quyền truy cập bản ghi Payslip (Access Rules) của cán bộ bảng lương
        Input: Phiếu lương, thuế, phân tích lương của nhân viên cấp dưới
        Output: Full quyền
        """
        self.product_employee_2.write({'parent_id': self.officer_employee.id})
        payslip = self.env['hr.payslip'].with_user(self.officer_user).create({
            'employee_id': self.product_employee_2.id,
            'date_from': fields.Date.to_date('2021-6-1'),
            'date_to': fields.Date.to_date('2021-6-30'),
            'salary_cycle_id': self.env.company.salary_cycle_id.id,
            'company_id': self.env.company.id
        })
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('read'))
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('write'))
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('unlink'))

        payslip.compute_sheet()
        lines = self.env['payslip.personal.income.tax.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_2_taxs = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertIsNone(employee_2_taxs.with_user(self.officer_user).check_access_rule('read'))

        lines = self.env['hr.payroll.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_2_analysis = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertIsNone(employee_2_analysis.with_user(self.officer_user).check_access_rule('read'))

    def test_03_payroll_security_officer_4(self):
        """
        Tets: Check quyền truy cập bản ghi Payslip (Access Rules) của cán bộ bảng lương
        Input: Phiếu lương, thuế, phân tích lương của nhân viên thuộc phòng ban mình quản lý
        Output: Full quyền
        """
        self.product_employee_2.write({
            'department_id': self.product_department.id,
            'parent_id': False
        })
        self.product_department.write({
            'manager_id': self.officer_employee.id
        })

        payslip = self.env['hr.payslip'].with_user(self.officer_user).create({
            'employee_id': self.product_employee_2.id,
            'date_from': fields.Date.to_date('2021-6-1'),
            'date_to': fields.Date.to_date('2021-6-30'),
            'salary_cycle_id': self.env.company.salary_cycle_id.id,
            'company_id': self.env.company.id
        })
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('read'))
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('write'))
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('unlink'))

        payslip.with_user(self.officer_user).compute_sheet()
        lines = self.env['payslip.personal.income.tax.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_2_taxs = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertIsNone(employee_2_taxs.with_user(self.officer_user).check_access_rule('read'))

        lines = self.env['hr.payroll.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_2_lines = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertIsNone(employee_2_lines.with_user(self.officer_user).check_access_rule('read'))

    def test_03_payroll_security_officer_5(self):
        """
        Tets: Check quyền truy cập bản ghi Payslip (Access Rules) của cán bộ bảng lương
        Input: Phiếu lương, thuế, phân tích lương của nhân viên không thuộc phòng ban mình quản lý hoặc không phải cấp dưới
        Output: Full quyền
        """
        payslip = self.create_payslip(
            self.product_employee_2.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('read'))
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('write'))
        self.assertIsNone(payslip.with_user(self.officer_user).check_access_rule('unlink'))

        payslip.compute_sheet()
        lines = self.env['payslip.personal.income.tax.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_2_taxs = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertIsNone(employee_2_taxs.with_user(self.officer_user).check_access_rule('read'))

        lines = self.env['hr.payroll.analysis'].search([('company_id', '=', self.env.company.id)])
        employee_2_lines = lines.filtered(lambda r: r.employee_id == self.product_employee_2)
        self.assertIsNone(employee_2_lines.with_user(self.officer_user).check_access_rule('read'))

    def test_03_payroll_security_officer_6(self):
        """
        Test: Người dùng cán bộ bảng lượng đọc được tất cả hợp đồng của nhân viên
        """
        all_contracts = self.env['hr.contract'].search([])
        all_contracts.with_user(self.officer_user).read(['id', 'name'])

    def test_04_payroll_security_officer(self):
        """
        Test: Người dùng cán bộ bảng lượng Full quyền với đăng ký đóng góp từ lương
        """
        contribution_type = self.env['hr.payroll.contribution.type'].search([('company_id', '=', self.env.company.id)], limit=1)
        ContribRegister = self.env['hr.payroll.contribution.register']
        register = ContribRegister.with_user(self.officer_user).create({
            'employee_id': self.manager_employee.id,
            'type_id': contribution_type.id,
            'date_from': fields.Date.to_date('2021-1-1'),
            'state': 'draft',
            'computation_method': contribution_type.computation_method,
            'employee_contrib_rate': 1,
            'company_contrib_rate': 1,
            'contribution_base': 5000
        })
        self.assertTrue(register, 'Test access rule (Contribution Register) for officer not ok')
        self.assertIsNone(
            register.with_user(self.officer_user).check_access_rule('read'),
            'Test access rule (Contribution Register) for officer not ok')
        self.assertIsNone(
            register.with_user(self.officer_user).check_access_rule('write'),
            'Test access rule (Contribution Register) for officer not ok')
        self.assertIsNone(
            register.with_user(self.officer_user).check_access_rule('unlink'),
            'Test access rule (Contribution Register) for officer not ok')

    def test_05_payroll_security_manager(self):
        """
        Test: Người dùng quản lý Bảng lương Có quyền Administrator (hr_contract.group_hr_contract_manager) của HR Contract
        """
        self.assertTrue(
            self.manager_user.has_group('hr_contract.group_hr_contract_manager'),
            'Test Contract Manager (hr_contract.group_hr_contract_manager) not ok')
        self.assertTrue(
            self.manager_user.has_group('to_hr_payroll.group_hr_payroll_user'),
            'Test Contract Manager (hr.group_hr_user) not ok')

    def test_06_contract_manager_modify_contract_advantage(self):
        """
        Test: Quản lý Hợp đồng có thể điều chỉnh phụ cấp hàng tháng trực tiếp trên hợp đồng của nhân viên
        """
        self.env['hr.contract.advantage'].with_user(self.contract_manager).check_access_rights('read')
        self.env['hr.contract.advantage'].with_user(self.contract_manager).check_access_rights('write')
        self.env['hr.contract.advantage'].with_user(self.contract_manager).check_access_rights('create')
        self.env['hr.contract.advantage'].with_user(self.contract_manager).check_access_rights('unlink')
