from datetime import timedelta
from unittest.mock import patch

from odoo import fields

from .common import TestPayrollCommon

# """
#     Formulas on salary rules can change in other modules
#         so tests related to payslip lines will run with tagged by default (at_install)
# """


class TestPayrollPayslipRegisterLine(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollPayslipRegisterLine, cls).setUpClass()
        cls.types = cls.env['hr.payroll.contribution.type'].search([('company_id', '=', cls.env.company.id)])
        cls.type = cls.types[0]

        cls.contract_close_emp_A.write({
            'payroll_contribution_type_ids': cls.types
        })
        cls.contract_close_emp_A.generate_payroll_contribution_registers()
        cls.contract_open_emp_A.write({
            'payroll_contribution_type_ids': cls.types
        })
        registers = cls.contract_open_emp_A.payroll_contribution_register_ids
        register_social_insurance = registers.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        register_health_insurance = registers.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        register_unemployment_unsurance = registers.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        register_labor_union = registers.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        register_social_insurance.write({
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,  # đóng góp đầy đủ là 300.000 (ESINS)
            'company_contrib_rate': 3  # đóng góp đầy đủ là 450.000 (CSINS)
            })
        register_health_insurance.write({
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,  # đóng góp đầy đủ là 225.000 (EHINS)
            'company_contrib_rate': 3  # đóng góp đầy đủ là 450.000 (CHINS)
            })
        register_unemployment_unsurance.write({
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,  # đóng góp đầy đủ là 150.000 (EUEINS)
            'company_contrib_rate': 2  # đóng góp đầy đủ là 300.000 (CUEINS)
            })
        register_labor_union.write({
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,  # đóng góp đầy đủ là 225.000 (ELUF)
            'company_contrib_rate': 2.5  # đóng góp đầy đủ là 375.000 (CLUF)
            })
        cls.contribution_registers = cls.contract_open_emp_A.payroll_contribution_register_ids

    # 8. Phiếu lương
    def test_payslip_contribute_line_1(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 5A: Test thông tin "Dòng đóng góp phiếu lương"
                TH1: Hợp đồng không có dòng đăng ký đóng góp từ lương
                    =>  Không có dữ liệu
        """
        self.contract_open_emp_A.write({
            'payroll_contribution_register_ids': False
        })

        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))

        self.assertFalse(payslip_1.hr_payslip_contribution_line_ids, 'Test hr_payslip_contribution_line_ids field not ok')

    # 8. Phiếu lương
    def test_payslip_contribute_line_2(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 5A: Test thông tin "Dòng đóng góp phiếu lương"
                TH2: Hợp đồng có các dòng đăng ký đóng góp từ lương, chưa xác nhận
                    =>  Không có dữ liệu
        """
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertFalse(payslip_1.hr_payslip_contribution_line_ids, 'Test hr_payslip_contribution_line_ids field not ok')

    # 8. Phiếu lương
    def test_payslip_contribute_line_3(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 5A: Test thông tin "Dòng đóng góp phiếu lương"
                TH3: Phiếu lương không đánh đấu lương tháng 13
                    Hợp đồng có các dòng đăng ký đóng góp từ lương, đã xác nhận

                => số dòng đóng góp = 4
        """
        self.contribution_registers.action_confirm()

        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        self.assertEqual(len(payslip_1.hr_payslip_contribution_line_ids), 4, 'Test hr_payslip_contribution_line_ids field not ok')

    # 8. Phiếu lương
    def test_payslip_contribute_line_4(self):  # check
        """
        8.2 Test Thông tin của phiếu lương
            Case 5A: Test thông tin "Dòng đóng góp phiếu lương"
                TH4: Phiếu lương có đánh đấu lương tháng 13
                    Hợp đồng có các dòng đăng ký đóng góp từ lương, đã xác nhận

                => số dòng đóng góp = 12 * số lượng kiểu đóng góp của phiếu lương
        """
        self.contribution_registers.action_confirm()

        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-1-1'),
            fields.Date.to_date('2021-12-31'),
            thirteen_month_pay=True)

        # 4 types x 12 line for 12 months
        self.assertEqual(len(payslip_1.hr_payslip_contribution_line_ids), 48, 'Test hr_payslip_contribution_line_ids field not ok')

    # 8. Phiếu lương
    def test_13th_payslip_register_lines(self):
        """
        10. Dòng phiếu lương
            Case 2B: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương - có đánh dấu tháng lương 13
                Input: Phiếu lương đã xác nhận trong năm xét lương,
                            và có các dòng phiếu lương liên quan đến đăng ký đóng góp từ lương
                        Tạo phiếu lương tháng 13 và nhấn tính toán / xác nhận
                Output: Không có các dòng phiếu lương liên quan đến các kiểu đóng góp từ lương
        """
        self.contribution_registers.action_confirm()

        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        payslip_1.action_payslip_verify()

        # 13th month salary
        payslip_2 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-1-1'),
            fields.Date.to_date('2021-12-31'),
            thirteen_month_pay=True)
        payslip_2.compute_sheet()

        register_lines = payslip_1.line_ids.filtered(lambda r: r.code in self.types.mapped('code'))
        self.assertFalse(register_lines, 'Test payroll register lines not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH1_1(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH1: computation_block: day, days_in_months: fixed (28 ngay`)
                    TH1.1: duration >= 28 days
                    TH1.2 duration < 28 days (14days)

        10. Dòng phiếu lương
            Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()
        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'day',
            'days_in_months': 'fixed'
        })
        self.contribution_registers.action_confirm()

        # TH1.1 duration >= 28 days
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        payslip_lines = payslip.line_ids

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            # (15.000.000 * 2 / 100) *(28/28) = 300000
            'employee_contribution': 300000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) *(28/28) = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(ps_line.total, -300000, 'Test ESINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(ps_line.total, 450000, 'Test CSINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) *(28/28) = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) *(28/28) = 300000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(ps_line.total, -225000, 'Test EHINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(ps_line.total, 450000, 'Test CHINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            # (15.000.000 * 1 / 100) *(28/28) = 150000
            'employee_contribution': 150000,
            'company_contrib_rate': 2,
            # (15.000.000 * 2 / 100) *(28/28) = 300000
            'company_contribution': 300000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(ps_line.total, -150000, 'Test EUEINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(ps_line.total, 300000, 'Test CUEINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) *(28/28) = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 2.5,
            # (15.000.000 * 2.5 / 100) *(28/28) = 375000
            'company_contribution': 375000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(ps_line.total, -225000, 'Test ELUF payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(ps_line.total, 375000, 'Test CLUF payslip line not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH1_2(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH1: computation_block: day, days_in_months: fixed (28 ngay`)
                    TH1.2 duration < 28 days (14days)
        10. Dòng phiếu lương
            Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()
        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'day',
            'days_in_months': 'fixed'
        })
        self.contribution_registers.action_confirm()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-14'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        payslip_lines = payslip.line_ids

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            # (15.000.000 * 2 / 100) *(14/28) = 150000
            'employee_contribution': 150000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) *(14/28) = 225000
            'company_contribution': 225000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(ps_line.total, -150000, 'Test ESINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(ps_line.total, 225000, 'Test CSINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) *(14/28) = 112500
            'employee_contribution': 112500,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) *(14/28) = 225000
            'company_contribution': 225000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(ps_line.total, -112500, 'Test EHINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(ps_line.total, 225000, 'Test CHINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            # (15.000.000 * 1 / 100) *(14/28) = 75000
            'employee_contribution': 75000,
            'company_contrib_rate': 2,
            # (15.000.000 * 2 / 100) *(14/28) = 150000
            'company_contribution': 150000,
            'state': 'confirmed',
        }])

        ps_line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(ps_line.total, -75000, 'Test EUEINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(ps_line.total, 150000, 'Test CUEINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) *(14/28) = 112500
            'employee_contribution': 112500,
            'company_contrib_rate': 2.5,
            # (15.000.000 * 2.5 / 100) *(14/28) = 187500
            'company_contribution': 187500,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(ps_line.total, -112500, 'Test ELUF payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(ps_line.total, 187500, 'Test CLUF payslip line not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH2_1(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH2: computation_block: day, days_in_months: flexible (linh hoat)
                    TH2.1 duration = days in month
        10. Dòng phiếu lương
                Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                    * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()
        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'day',
            'days_in_months': 'flexible'
        })
        self.contribution_registers.action_confirm()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        payslip_lines = payslip.line_ids

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            # (15.000.000 * 2 / 100) *(31/31) = 300000
            'employee_contribution': 300000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) *(31/31) = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(ps_line.total, -300000, 'Test ESINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(ps_line.total, 450000, 'Test CSINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) *(31/31) = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) *(31/31) = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(ps_line.total, -225000, 'Test EHINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(ps_line.total, 450000, 'Test CHINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            # (15.000.000 * 1 / 100) *(31/31) = 150000
            'employee_contribution': 150000,
            'company_contrib_rate': 2,
            # (15.000.000 * 2 / 100) *(31/31) = 300000
            'company_contribution': 300000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(ps_line.total, -150000, 'Test EUEINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(ps_line.total, 300000, 'Test CUEINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) *(31/31) = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 2.5,
            # (15.000.000 * 2.5 / 100) *(31/31) = 375000
            'company_contribution': 375000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(ps_line.total, -225000, 'Test ELUF payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(ps_line.total, 375000, 'Test CLUF payslip line not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH2_2(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH2: computation_block: day, days_in_months: flexible (linh hoat)
                    TH2.2 duration < days in month (14/31 days)
        10. Dòng phiếu lương
                Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                    * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()
        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'day',
            'days_in_months': 'flexible'
        })
        self.contribution_registers.action_confirm()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-14'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        payslip_lines = payslip.line_ids
        currency = payslip.currency_id
        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            # (15.000.000 * 2 / 100) *(14/31) = 135483.87096
            'employee_contribution': currency.round(135483.87096),
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) *(14/31) = 203225.8065
            'company_contribution': currency.round(203225.8065),
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(ps_line.total, currency.round(-135483.87096), 'Test ESINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(ps_line.total, currency.round(203225.8065), 'Test CSINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) *(14/31) = 101612.90322
            'employee_contribution': currency.round(101612.90322),
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) *(14/31) = 203225.8065
            'company_contribution': currency.round(203225.8065),
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(ps_line.total, currency.round(-101612.90322), 'Test EHINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(ps_line.total, currency.round(203225.8065), 'Test CHINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            # (15.000.000 * 1 / 100) *(14/31) = 67741.93548
            'employee_contribution': currency.round(67741.93548),
            'company_contrib_rate': 2,
            # (15.000.000 * 2 / 100) *(14/31) = 135483.87096
            'company_contribution': currency.round(135483.87096),
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(ps_line.total, currency.round(-67741.93548), 'Test EUEINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(ps_line.total, currency.round(135483.87096), 'Test CUEINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) *(14/31) = 101612.90322
            'employee_contribution': currency.round(101612.90322),
            'company_contrib_rate': 2.5,
            # (15.000.000 * 2.5 / 100) *(14/31) = 169354.8387
            'company_contribution': currency.round(169354.8387),
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(ps_line.total, currency.round(-101612.90322), 'Test ELUF payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(ps_line.total, currency.round(169354.8387), 'Test CLUF payslip line not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH3_1(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH3: computation_block: week, days_in_months: fixed (28 ngay`)
                    TH3.1 duration >= 28 days (4 weeks)
        10. Dòng phiếu lương
                Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                    * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()

        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'week',
            'days_in_months': 'fixed'
        })
        self.contribution_registers.action_confirm()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        payslip_lines = payslip.line_ids

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            # week = round(31/7) = 4
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            # (15.000.000 * 2 / 100) * 4 / 4 = 225.000
            'employee_contribution': 300000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) * 4 / 4 = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(ps_line.total, -300000, 'Test ESINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(ps_line.total, 450000, 'Test CSINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            # week = round(31/7) = 4
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) * 4 / 4 = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) * 4 / 4 = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(ps_line.total, -225000, 'Test EHINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(ps_line.total, 450000, 'Test CHINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            # week = round(31/7) = 4
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            # (15.000.000 * 1 / 100) * 4 / 4 = 150000
            'employee_contribution': 150000,
            'company_contrib_rate': 2,
            # (15.000.000 * 2 / 100) * 4 / 4 = 300000
            'company_contribution': 300000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(ps_line.total, -150000, 'Test EUEINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(ps_line.total, 300000, 'Test CUEINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            # week = round(31/7) = 4
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) * 4 / 4 = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 2.5,
            # (15.000.000 * 2.5 / 100) * 4 / 4 = 375000
            'company_contribution': 375000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(ps_line.total, -225000, 'Test ELUF payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(ps_line.total, 375000, 'Test CLUF payslip line not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH3_2(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH3: computation_block: week, days_in_months: fixed (28 ngay`)
                    TH3.2  4 days <= duration <= 24 days (1 -> 3 weeks)
        10. Dòng phiếu lương
                Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                    * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()

        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'week',
            'days_in_months': 'fixed'
        })
        self.contribution_registers.action_confirm()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-16'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        payslip_lines = payslip.line_ids

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            # week = round(16/7) = 2
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            # (15.000.000 * 2 / 100) * 2 / 4 = 150000
            'employee_contribution': 150000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) * 2 / 4 = 225000
            'company_contribution': 225000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(ps_line.total, -150000, 'Test ESINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(ps_line.total, 225000, 'Test CSINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            # week = round(16/7) = 2
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) * 4 / 4 = 112500
            'employee_contribution': 112500,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) * 2 / 4 = 225000
            'company_contribution': 225000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(ps_line.total, -112500, 'Test EHINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(ps_line.total, 225000, 'Test CHINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            # week = round(31/7) = 2
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            # (15.000.000 * 1 / 100) * 2 / 4 = 75000
            'employee_contribution': 75000,
            'company_contrib_rate': 2,
            # (15.000.000 * 2 / 100) * 2 / 4 = 150000
            'company_contribution': 150000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(ps_line.total, -75000, 'Test EUEINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(ps_line.total, 150000, 'Test CUEINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            # week = round(31/7) = 4
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) * 2 / 4 = 112500
            'employee_contribution': 112500,
            'company_contrib_rate': 2.5,
            # (15.000.000 * 2.5 / 100) * 0 / 4 = 187500
            'company_contribution': 187500,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(ps_line.total, -112500, 'Test ELUF payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(ps_line.total, 187500, 'Test CLUF payslip line not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH3_3(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH3: computation_block: week, days_in_months: fixed (28 ngay`)
                    TH3.3  duration < 4 days (0 weeks)
                TH4: computation_block: week, days_in_months: flexible (linh hoat)
                    * giống TH 3: round( [28:31] / 7) = 4
        10. Dòng phiếu lương
                Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                    * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()

        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'week',
            'days_in_months': 'fixed'
        })
        self.contribution_registers.action_confirm()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-3'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            # week = round(16/7) = 2
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            'employee_contribution': 0,
            'company_contrib_rate': 3,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            # week = round(16/7) = 2
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            'employee_contribution': 0,
            'company_contrib_rate': 3,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            # week = round(31/7) = 2
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            'employee_contribution': 0,
            'company_contrib_rate': 2,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            # week = round(31/7) = 4
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            'employee_contribution': 0,
            'company_contrib_rate': 2.5,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        payslip_lines = payslip.line_ids
        codes = ['ESINS', 'CSINS', 'EHINS', 'CHINS', 'EUEINS', 'CUEINS', 'ELUF', 'CLUF']
        ps_lines = payslip_lines.filtered(lambda r: r.code in codes)
        self.assertFalse(ps_lines, 'Test contribution payslip line not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH5_1(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH5: computation_block: month, computation_method: half_up, days_in_months: fixed (28 ngay`)
                    TH5.1 duration >= 14 days
        10. Dòng phiếu lương
                Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                    * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()
        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'month',
            'computation_method': 'half_up',
            'days_in_months': 'fixed'
        })
        self.contribution_registers.action_confirm()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-14'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        payslip_lines = payslip.line_ids

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            # month = float_round(14/28) = 1
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            # (15.000.000 * 2 / 100) * 1 = 225.000
            'employee_contribution': 300000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) * 1 = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(ps_line.total, -300000, 'Test ESINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(ps_line.total, 450000, 'Test CSINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            # month = float_round(14/28) = 1
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) * 1 = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) * 1 = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(ps_line.total, -225000, 'Test EHINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(ps_line.total, 450000, 'Test CHINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            # month = float_round(14/28) = 1
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            # (15.000.000 * 1 / 100) * 1 = 150000
            'employee_contribution': 150000,
            'company_contrib_rate': 2,
            # (15.000.000 * 2 / 100) * 1 = 300000
            'company_contribution': 300000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(ps_line.total, -150000, 'Test EUEINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(ps_line.total, 300000, 'Test CUEINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            # month = float_round(14/28) = 1
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) * 1 = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 2.5,
            # (15.000.000 * 2.5 / 100) * 1 = 375000
            'company_contribution': 375000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(ps_line.total, -225000, 'Test ELUF payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(ps_line.total, 375000, 'Test CLUF payslip line not ok')

    def test_payslip_contribute_line_and_payslip_lines_TH5_2(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH5: computation_block: month, computation_method: half_up, days_in_months: fixed (28 ngay`)
                    TH5.2 duration < 14 days
        10. Dòng phiếu lương
                Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                    * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()
        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'month',
            'computation_method': 'half_up',
            'days_in_months': 'fixed'
        })
        self.contribution_registers.action_confirm()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-13'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            'employee_contribution': 0,
            'company_contrib_rate': 3,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            'employee_contribution': 0,
            'company_contrib_rate': 3,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            'employee_contribution': 0,
            'company_contrib_rate': 2,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            'employee_contribution': 0,
            'company_contrib_rate': 2.5,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        payslip_lines = payslip.line_ids
        codes = ['ESINS', 'CSINS', 'EHINS', 'CHINS', 'EUEINS', 'CUEINS', 'ELUF', 'CLUF']
        ps_lines = payslip_lines.filtered(lambda r: r.code in codes)
        self.assertFalse(ps_lines, 'Test contribution payslip line not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH6_1(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH6: computation_block: month, computation_method: half_up, days_in_months: flexible (linh hoat)
                    TH6.1 duration >= half of the days in the month
        10. Dòng phiếu lương
                Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                    * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()
        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'month',
            'computation_method': 'half_up',
            'days_in_months': 'flexible'
        })
        self.contribution_registers.action_confirm()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-16'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        payslip_lines = payslip.line_ids

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            # month = float_round(16/31) = 1
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            # (15.000.000 * 2 / 100) * 1 = 225.000
            'employee_contribution': 300000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) * 1 = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(ps_line.total, -300000, 'Test ESINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(ps_line.total, 450000, 'Test CSINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            # month = float_round(16/31) = 1
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) * 1 = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) * 1 = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(ps_line.total, -225000, 'Test EHINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(ps_line.total, 450000, 'Test CHINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            # month = float_round(16/31) = 1
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            # (15.000.000 * 1 / 100) * 1 = 150000
            'employee_contribution': 150000,
            'company_contrib_rate': 2,
            # (15.000.000 * 2 / 100) * 1 = 300000
            'company_contribution': 300000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(ps_line.total, -150000, 'Test EUEINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(ps_line.total, 300000, 'Test CUEINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            # month = float_round(16/31) = 1
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) * 1 = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 2.5,
            # (15.000.000 * 2.5 / 100) * 1 = 375000
            'company_contribution': 375000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(ps_line.total, -225000, 'Test ELUF payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(ps_line.total, 375000, 'Test CLUF payslip line not ok')

    def test_payslip_contribute_line_and_payslip_lines_TH6_2(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH6: computation_block: month, computation_method: half_up, days_in_months: flexible (linh hoat)
                    TH6.2 duration < half of the days in the month
        10. Dòng phiếu lương
                Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                    * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()
        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'month',
            'computation_method': 'half_up',
            'days_in_months': 'flexible'
        })
        self.contribution_registers.action_confirm()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-14'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            'employee_contribution': 0,
            'company_contrib_rate': 3,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            'employee_contribution': 0,
            'company_contrib_rate': 3,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            'employee_contribution': 0,
            'company_contrib_rate': 2,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            'employee_contribution': 0,
            'company_contrib_rate': 2.5,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        payslip_lines = payslip.line_ids
        codes = ['ESINS', 'CSINS', 'EHINS', 'CHINS', 'EUEINS', 'CUEINS', 'ELUF', 'CLUF']
        ps_lines = payslip_lines.filtered(lambda r: r.code in codes)
        self.assertFalse(ps_lines, 'Test contribution payslip line not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH7_1(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH7: computation_block: month, computation_method: max_unpaid_days, max unpaid_days
                    TH7.1: nghỉ < 10 ngày

        10. Dòng phiếu lương
            Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()
        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'month',
            'computation_method': 'max_unpaid_days',
            'max_unpaid_days': 10,
        })
        self.contribution_registers.action_confirm()

        # nghỉ < 10 ngày
        leave_type = self.env['hr.leave.type'].search([('unpaid', '=', True)], limit=1)
        hol1 = self.create_holiday(
            'Test Leave 1',
            self.product_emp_A.id, leave_type.id,
            fields.Datetime.to_datetime('2021-07-01 00:00:00'),
            fields.Datetime.to_datetime('2021-07-02 23:59:59'))
        hol1.action_validate()

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-30'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        payslip_lines = payslip.line_ids

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            # (15.000.000 * 2 / 100) * 1 = 300000
            'employee_contribution': 300000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) * 1 = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(ps_line.total, -300000, 'Test ESINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(ps_line.total, 450000, 'Test CSINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) * 1 = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 3,
            # (15.000.000 * 3 / 100) * 1 = 450000
            'company_contribution': 450000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(ps_line.total, -225000, 'Test EHINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(ps_line.total, 450000, 'Test CHINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            # (15.000.000 * 1 / 100) * 1 = 150000
            'employee_contribution': 150000,
            'company_contrib_rate': 2,
            # (15.000.000 * 2 / 100) * 1 = 300000
            'company_contribution': 300000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(ps_line.total, -150000, 'Test EUEINS payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(ps_line.total, 300000, 'Test CUEINS payslip line not ok')

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            # (15.000.000 * 1.5 / 100) * 1 = 225000
            'employee_contribution': 225000,
            'company_contrib_rate': 2.5,
            # (15.000.000 * 2.5 / 100) * 1 = 375000
            'company_contribution': 375000,
            'state': 'confirmed',
        }])
        ps_line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(ps_line.total, -225000, 'Test ELUF payslip line not ok')
        ps_line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(ps_line.total, 375000, 'Test CLUF payslip line not ok')

    # 8. Phiếu lương
    # 10. Dòng phiếu lương
    def test_payslip_contribute_line_and_payslip_lines_TH7_2(self):
        """
        8. Phiếu lương
            Case 5B: Test thông tin chi tiết "Dòng đóng góp phiếu lương" trên phiếu lương
                TH7: computation_block: month, computation_method: max_unpaid_days, max unpaid_days
                    TH7.2: nghỉ >= 10 ngày

        10. Dòng phiếu lương
            Case 2A: Dòng phiếu lương liên quan đến các đăng ký đóng góp từ lương
                * được test sau khi nhấn nút tính toán phiếu lương: payslip.compute_sheet()
        """
        # Prepare data
        self.contribution_registers.write({
            'computation_block': 'month',
            'computation_method': 'max_unpaid_days',
            'max_unpaid_days': 10,
        })
        self.contribution_registers.action_confirm()

        # nghỉ >= 10 ngày:
        # hol1 + hol2 = 10 days
        leave_type = self.env['hr.leave.type'].search([('unpaid', '=', True)], limit=1)
        hol1 = self.create_holiday(
            'Test Leave 1',
            self.product_emp_A.id, leave_type.id,
            fields.Datetime.to_datetime('2021-07-01 00:00:00'),
            fields.Datetime.to_datetime('2021-07-02 23:59:59'))
        hol1.action_validate()
        hol2 = self.create_holiday(
            'Test Leave 2',
            self.product_emp_A.id, leave_type.id,
            fields.Datetime.to_datetime('2021-07-03 00:00:00'),
            fields.Datetime.to_datetime('2021-07-14 23:59:59'))
        hol2.action_validate()
        self.env['hr.work.entry'].search([('leave_id', 'in', (hol1 | hol2).ids)]).write({'state': 'validated'})

        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        payslip.compute_sheet()

        # check contrib lines & payslip lines
        contrib_lines = payslip.hr_payslip_contribution_line_ids
        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'SOCIAL_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 2,
            'employee_contribution': 0,
            'company_contrib_rate': 3,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'HEALTH_INSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            'employee_contribution': 0,
            'company_contrib_rate': 3,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        self.assertRecordValues(contrib_line, [{
            'code': 'UNEMPLOYMENT_UNSURANCE',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1,
            'employee_contribution': 0,
            'company_contrib_rate': 2,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        contrib_line = contrib_lines.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        self.assertRecordValues(contrib_line, [{
            'code': 'LABOR_UNION',
            'contribution_base': 15000000,
            'employee_contrib_rate': 1.5,
            'employee_contribution': 0,
            'company_contrib_rate': 2.5,
            'company_contribution': 0,
            'state': 'confirmed',
        }])

        payslip_lines = payslip.line_ids
        codes = ['ESINS', 'CSINS', 'EHINS', 'CHINS', 'EUEINS', 'CUEINS', 'ELUF', 'CLUF']
        ps_lines = payslip_lines.filtered(lambda r: r.code in codes)
        self.assertFalse(ps_lines, 'Test contribution payslip line not ok')

    def change_contract_for_emp_A(self, date):
        self.contract_open_emp_A.with_context(close_contract=False).write({'date_end': date})
        self.contract_open_emp_A.state = 'close'
        self.new_contract_open_emp_A = self.create_contract(
            self.product_emp_A.id,
            date + timedelta(days=1),
            state='open')
        self.new_contract_open_emp_A.write({
            'payroll_contribution_type_ids': self.types
            })

    # 8. Phiếu lương
    # 10. Dòng đóng góp phiếu lương
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_payslip_contribute_line_TH8_1(self):
        """
        Input:
        - Nhân viên thay đổi hợp đồng vào ngày 05/07/2021.
        - Tạo phiếu lương cho tháng 07/2021 theo chu kỳ chuẩn.

        Output:
        - Mỗi loại đóng góp từ lương sẽ có 1 dòng đóng góp được sinh ra,
        với chu kỳ từ 01/07/2021 đến 31/07/2021.
        """
        self.change_contract_for_emp_A(fields.Date.to_date('2021-7-5'))
        self.contribution_registers.action_confirm()
        ps = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))
        ps.compute_sheet()

        # check period of all contrib lines
        contrib_lines = ps.hr_payslip_contribution_line_ids
        for code in ['SOCIAL_INSURANCE', 'HEALTH_INSURANCE', 'UNEMPLOYMENT_UNSURANCE', 'LABOR_UNION']:
            contrib_lines_by_code = contrib_lines.filtered(lambda line: line.code == code).sorted('date_from')
            self.assertEqual(len(contrib_lines_by_code), 1, "There must be 1 contribution line with code '%s'" % code)
            self.assertRecordValues(contrib_lines_by_code, [{
                'date_from': fields.Date.to_date('2021-7-1'),
                'date_to': fields.Date.to_date('2021-7-31'),
                }])

    # 8. Phiếu lương
    # 10. Dòng đóng góp phiếu lương
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_payslip_contribute_line_TH8_2(self):
        """
        Input:
        - Nhân viên thay đổi hợp đồng vào ngày 05/07/2021.
        - Tạo phiếu lương theo chu kỳ lệch chuẩn từ 26/06/2021 đến 25/07/2021.

        Output:
        - Mỗi loại đóng góp từ lương sẽ có 2 dòng đóng góp được sinh ra:
            - 1 dòng từ 26/06/2021 đến 30/06/2021
            - 1 dòng từ 01/07/2021 đến 25/07/2021
        """
        self.change_contract_for_emp_A(fields.Date.to_date('2021-7-5'))
        self.env.company.salary_cycle_id.write({
            'start_day_offset': 25,
        })
        self.contribution_registers.action_confirm()
        ps = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-6-26'),
            fields.Date.to_date('2021-7-25'))
        ps.compute_sheet()

        # check period of all contrib lines
        contrib_lines = ps.hr_payslip_contribution_line_ids
        for code in ['SOCIAL_INSURANCE', 'HEALTH_INSURANCE', 'UNEMPLOYMENT_UNSURANCE', 'LABOR_UNION']:
            contrib_lines_by_code = contrib_lines.filtered(lambda line: line.code == code).sorted('date_from')
            self.assertEqual(len(contrib_lines_by_code), 2, "There must be 2 contribution lines with code '%s'" % code)
            self.assertRecordValues(contrib_lines_by_code[0], [{
                'date_from': fields.Date.to_date('2021-6-26'),
                'date_to': fields.Date.to_date('2021-6-30'),
                }])
            self.assertRecordValues(contrib_lines_by_code[1], [{
                'date_from': fields.Date.to_date('2021-7-1'),
                'date_to': fields.Date.to_date('2021-7-25'),
                }])
