from unittest.mock import patch

from odoo import fields
from .common import TestPayrollCommon


# """
#     Formulas on salary rules can change in other modules
#         so tests related to payslip lines will run with tagged by default (at_install)
# """


class TestPayrollPayslipTax(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollPayslipTax, cls).setUpClass()

        TaxRule = cls.env['personal.tax.rule']
        cls.tax_flat_rate = TaxRule.create({
            'country_id': cls.env.company.country_id.id,
            'personal_tax_policy': 'flat_rate',
            'personal_tax_flat_rate': 10.0,
            'apply_tax_base_deduction': False,
            })

        cls.tax_flat_rate_deduction = TaxRule.create({
            'country_id': cls.env.company.country_id.id,
            'personal_tax_policy': 'flat_rate',
            'personal_tax_flat_rate': 10.0,
            'apply_tax_base_deduction': True,
            'personal_tax_base_ded': 11000000,
            'dependent_tax_base_ded': 4400000,
            })

        cls.tax_escalation_non_deduction = TaxRule.create({
            'country_id': cls.env.company.country_id.id,
            'apply_tax_base_deduction': False,
            'personal_tax_policy': 'escalation',
            'progress_ids': [
                (0, 0, {'base': 0, 'rate': 5.0}),
                (0, 0, {'base': 5000000, 'rate': 10.0}),
                (0, 0, {'base': 10000000, 'rate': 15.0}),
                (0, 0, {'base': 18000000, 'rate': 20.0}),
                (0, 0, {'base': 32000000, 'rate': 25.0}),
                (0, 0, {'base': 52000000, 'rate': 30.0}),
                (0, 0, {'base': 80000000, 'rate': 35.0})
            ]
        })

        contribution_types = cls.env['hr.payroll.contribution.type'].search([('company_id', '=', cls.env.company.id)])
        contribution_types.write({
            'employee_contrib_rate': 5.0,
            'company_contrib_rate': 10.0
            })
        cls.contract_open_emp_A.write({'payroll_contribution_type_ids': [(6, 0, contribution_types.ids)]})
        cls.contract_open_emp_A.generate_payroll_contribution_registers()

    # 8. Phiếu lương
    def test_payslip_tax_details_1(self):
        """
        8.2: Test Thông tin của phiếu lương
            Case 1: Test các thông tin trong tab "Chi tiết thuế TNCN" theo hợp đồng
                Input: Phiếu lương có hợp đồng, Quy tắc thuế có áp dụng giảm trừ
                Output:
                    Chính sách thuế TNCN, Quy tắc thuế lấy trên hợp đồng
                    "Giảm trừ bản thân" lấy theo Theo quy tắc thuế bên trên
                    "Giảm trừ người phụ thuộc" = Số lượng phụ thuộc của nhân viên * Giảm trừ mối người phụ thuộc trên Quy tắc thuế

        """
        # prepare data
        self.product_emp_A.write({'total_dependant': 2})
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
        )

        # check data
        self.assertRecordValues(
            payslip,
            [{
                'personal_tax_base_deduction': 11000000,
                'dependent_deduction': 8800000
            }])

    # 8. Phiếu lương
    def test_payslip_tax_details_2(self):
        """
        8.2: Test Thông tin của phiếu lương
            Case 1: Test các thông tin trong tab "Chi tiết thuế TNCN" theo hợp đồng
                Input: Phiếu lương có hợp đồng, Quy tắc thuế không áp dụng giảm trừ
                Output:
                    Chính sách thuế TNCN, Quy tắc thuế lấy trên hợp đồng
                    Sô tiền "Giảm trừ bản thân" là 0
                    Số tiền "Giảm trừ người phụ thuộc" là 0

        """
        # prepare data
        self.product_emp_A.write({'total_dependant': 2})
        self.contract_open_emp_A.personal_tax_rule_id.write({
            'apply_tax_base_deduction': False
        })
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )

        # check data
        self.assertRecordValues(
            payslip,
            [{
                'personal_tax_policy': self.contract_open_emp_A.personal_tax_policy,
                'personal_tax_rule_id': self.contract_open_emp_A.personal_tax_rule_id.id,
                'personal_tax_base_deduction': 0.0,
                'dependent_deduction': 0.0
            }])

    # 8. Phiếu lương
    def test_payslip_tax_flat_rate_1(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 10: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế cố định
                TH1: Tính toán phiếu lương với hợp đồng có quy tắc thuế:
                        Chính sách thuế: cố định
                        Thuế suất : 10%
                        Áp dụng giảm trừ: không
                    Không có các khoản đăng ký đóng góp từ lương
                Output:
                    1 dòng thuế trong Bảng tính thuế luỹ tiến từng phần trong tab Chi tiết Thuế TNCN
                    3 dòng phiếu lương lương TBDED, TAXBASE, PTAX:
                        TBDED : 0
                        TAXBASE : lương GROSS
                        PTAX : -1 * 10% của TAXBASE
        """
        # contract: wage = 15.000.000
        self.contract_open_emp_A.write({
            'personal_tax_rule_id': self.tax_flat_rate.id
            })

        # compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )
        payslip.compute_sheet()
        payslip_lines = payslip.line_ids

        # BASIC: 15.000.000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 15.000.000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: 0
        # DED_AFTER_TAX: 0
        # TBDED = 0 (không áp dụng giảm trừ)
        # TAXBASE = GROSS - TBDED = 15.000.000
        # PTAX: 1 dòng thuế 10%: = -1.500.000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 15.000.000 + 0+ - 0 - 0 - 1.500.000 = 13.500.000

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 15000000,
            },
            {
                'code': 'GROSS',
                'amount': 15000000,
            },
            {
                'code': 'NET',
                'amount': 13500000,
            }])

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 15000000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 0,
            },
            {
                'code': 'TAXBASE',
                'amount': 15000000,
            },
            {
                'code': 'PTAX',
                'amount': -1500000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 1, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 15000000,
                'base': 15000000,
                'rate': 10,
                'tax_amount': 1500000
            },
        ])

    # 8. Phiếu lương
    def test_payslip_tax_flat_rate_2(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 10: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế cố định
                TH2: Tính toán phiếu lương với hợp đồng có quy tắc thuế:
                        Chính sách thuế: cố định
                        Thuế suất : 10%
                        Áp dụng giảm trừ: không
                    Có các khoản đăng ký đóng góp từ lương
                Output:
                    1 dòng thuế trong Bảng tính thuế luỹ tiến từng phần trong tab Chi tiết Thuế TNCN
                    3 dòng phiếu lương lương TBDED, TAXBASE, PTAX:
                        TBDED : -1 * tổng số tiền của các khoản đóng góp từ lương
                        TAXBASE : lương GROSS
                        PTAX : -1 * 10% của TAXBASE
        """
        # contract: wage = 15.000.000 & contribution registers
        self.contract_open_emp_A.write({
            'personal_tax_rule_id': self.tax_flat_rate.id
        })
        # tỷ lệ nhân viên trên mỗi kiểu đăng ký là 5%
        # => 5% * 15.000.000 = 750.000
        self.contract_open_emp_A.payroll_contribution_register_ids.action_confirm()

        # compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
        )
        payslip.compute_sheet()
        payslip_lines = payslip.line_ids

        # BASIC: 15.000.000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 15.000.000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = -(750.000 + 750.000 + 750.000) = -2.250.000
        # DED_AFTER_TAX: 750.000
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX
        # TAXBASE = GROSS (không áp dụng giảm trừ) = 15.000.000
        # PTAX: -1 * 10% * TAXBASE: = -1 * 10% * 15.000.000 = -1.500.000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        # = 15.000.000 + 0+ - 2.250.000 - 750.000 - 1.500.000 = 10.500.000

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 15000000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 2250000,
            },
            {
                'code': 'TAXBASE',
                'amount': 15000000,
            },
            {
                'code': 'PTAX',
                'amount': -1500000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 1, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 15000000,
                'base': 15000000,
                'rate': 10,
                'tax_amount': 1500000
            },
        ])

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 15000000,
            },
            {
                'code': 'GROSS',
                'amount': 15000000,
            },
            {
                'code': 'NET',
                'amount': 10500000,
            }])

    def test_payslip_tax_flat_rate_3(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 10: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế cố định
                TH3: Tính toán phiếu lương với hợp đồng có quy tắc thuế:
                        Chính sách thuế: cố định
                        Thuế suất : 10%
                        Áp dụng giảm trừ: có
                            Giảm trừ Cơ sở tính Thuế thu nhập cá nhân: 11.000.000
                            Giảm trừ cho mỗi người phụ thuộc: 4.400.000
                                * Nhân viên không có phụ thuộc
                    Không các khoản đăng ký đóng góp từ lương
                Output:
                    1 dòng thuế trong Bảng tính thuế luỹ tiến từng phần trong tab Chi tiết Thuế TNCN
                    3 dòng phiếu lương lương TBDED, TAXBASE, PTAX:
                        TBDED : 11.000.000 - tổng số tiền của các khoản đóng góp từ lương
                        TAXBASE : Lương GROSS - TBDED
                        PTAX : -1 * 10% của TAXBASE
        """
        # contract: wage = 15.000.000
        self.contract_open_emp_A.write({
            'personal_tax_rule_id': self.tax_flat_rate_deduction.id
        })

        # compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
        )
        payslip.compute_sheet()
        payslip_lines = payslip.line_ids

        # BASIC: 15.000.000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 15000000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000
        # TAXBASE = GROSS - TBDED = 4000000
        # PTAX: 1 dòng thuế cố định 10%: 400000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 15000000 - 400000 = 14600000

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 15000000,
            },
            {
                'code': 'GROSS',
                'amount': 15000000,
            },
            {
                'code': 'NET',
                'amount': 14600000,
            }])

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 4000000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 11000000,
            },
            {
                'code': 'TAXBASE',
                'amount': 4000000,
            },
            {
                'code': 'PTAX',
                'amount': -400000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 1, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 4000000,
                'base': 4000000,
                'rate': 10,
                'tax_amount': 400000
            },
        ])

    def test_payslip_tax_flat_rate_4(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 10: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế cố định
                TH4: Tính toán phiếu lương với hợp đồng có quy tắc thuế:
                        Chính sách thuế: cố định
                        Thuế suất : 10%
                        Áp dụng giảm trừ: có
                            Giảm trừ Cơ sở tính Thuế thu nhập cá nhân: 11.000.000
                            Giảm trừ cho mỗi người phụ thuộc: 4.400.000
                                * Nhân viên không có phụ thuộc
                    Có các khoản đăng ký đóng góp từ lương
                Output:
                    1 dòng thuế trong Bảng tính thuế luỹ tiến từng phần trong tab Chi tiết Thuế TNCN
                    3 dòng phiếu lương lương TBDED, TAXBASE, PTAX:
                        TBDED : 11.000.000 - tổng số tiền của các khoản đóng góp từ lương
                        TAXBASE : Lương GROSS - TBDED
                        PTAX : -1 * 10% của TAXBASE
        """
        # contract: wage = 15.000.000 & contribution registers
        self.contract_open_emp_A.write({
            'personal_tax_rule_id': self.tax_flat_rate_deduction.id
            })
        self.contract_open_emp_A.payroll_contribution_register_ids.action_confirm()

        # compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )
        payslip.compute_sheet()
        payslip_lines = payslip.line_ids

        # BASIC: 15.000.000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 15000000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: -750000*3 = -2250000
        # DED_AFTER_TAX: 750000
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000 + 2250000 = 13250000
        # TAXBASE = GROSS - TBDED = 15000000-13250000 = 1750000
        # PTAX: 1 dòng thuế cố định 10%: -175000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 15000000 - 2250000 - 750000 - 175000 = 11825000

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 15000000,
            },
            {
                'code': 'GROSS',
                'amount': 15000000,
            },
            {
                'code': 'NET',
                'amount': 11825000,
            }])

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 1750000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 13250000,
            },
            {
                'code': 'TAXBASE',
                'amount': 1750000,
            },
            {
                'code': 'PTAX',
                'amount': -175000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 1, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 1750000,
                'base': 1750000,
                'rate': 10,
                'tax_amount': 175000
            },
        ])

    def test_payslip_tax_flat_rate_5(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 10: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế cố định
                TH5: Tính toán phiếu lương với hợp đồng có quy tắc thuế:
                        Chính sách thuế: cố định
                        Thuế suất : 10%
                        Áp dụng giảm trừ: có
                            Giảm trừ Cơ sở tính Thuế thu nhập cá nhân: 11.000.000
                            Giảm trừ cho mỗi người phụ thuộc: 4.400.000
                    Có các khoản đăng ký đóng góp từ lương
                    Nhân viên có 1 người phụ thuộc: chưa đủ điều kiện đóng thuế
                Output:
                    1 dòng thuế trong Bảng tính thuế luỹ tiến từng phần trong tab Chi tiết Thuế TNCN
                    3 dòng phiếu lương lương TBDED, TAXBASE, PTAX:
                        TBDED : 11.000.000 - tổng số tiền của các khoản đóng góp từ lương
                        TAXBASE : Lương GROSS - TBDED
                        PTAX : -1 * 10% của TAXBASE
        """
        # contract: wage = 15.000.000 & contribution registers
        self.contract_open_emp_A.write({
            'personal_tax_rule_id': self.tax_flat_rate_deduction.id
            })
        self.contract_open_emp_A.payroll_contribution_register_ids.action_confirm()

        # employee: 1
        self.product_emp_A.write({
            'total_dependant': 1
            })

        # compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )
        payslip.compute_sheet()
        payslip_lines = payslip.line_ids

        # BASIC: 15.000.000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 15000000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: -750000*3 = -2250000
        # DED_AFTER_TAX: -750000
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000 + 4400000 + 2250000 = 17650000
        # TAXBASE = GROSS - TBDED = 15000000-17650000 = -2650000 => 0.0 for negative
        # PTAX: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 15000000 - 2250000 - 750000 = 12000000

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 15000000,
            },
            {
                'code': 'GROSS',
                'amount': 15000000,
            },
            {
                'code': 'NET',
                'amount': 12000000,
            }])

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 0.0, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 17650000,
            },
            {
                'code': 'TAXBASE',
                'amount': 0.0,
            },
            {
                'code': 'PTAX',
                'amount': 0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip.payslip_personal_income_tax_ids
        self.assertFalse(income_taxs, 'Test payslip_personal_income_tax_ids field not ok')

    def test_payslip_tax_flat_rate_6(self):
        """
        TH6: Giống case TH5 (test_payslip_tax_flat_rate_5) nhưng đủ điều kiện đóng thuế
        """
        # contract: wage = 30.000.000 & contribution registers
        self.contract_open_emp_A.write({
            'wage': 30000000,
            'personal_tax_rule_id': self.tax_flat_rate_deduction.id
            })
        self.contract_open_emp_A.payroll_contribution_register_ids.action_confirm()

        # employee: 1
        self.product_emp_A.write({
            'total_dependant': 1
            })

        # compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )
        payslip.compute_sheet()
        payslip_lines = payslip.line_ids

        #         BASIC: 30000000 (tỷ lệ chi trả =1)
        #         ALW : 0
        #         GROSS = BASIC + ALW = 30000000
        #         ALWNOTAX : 0
        #         DED_BEFORE_TAX: -750000*3 = -2250000
        #         DED_AFTER_TAX: 750000
        #         TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000 + 4400000 + 2250000 = 17650000
        #         TAXBASE = GROSS - TBDED = 30000000-17650000 = 12350000
        #         PTAX: 1 dòng thuế cố định 10% : -1235000
        #         NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #             = 30000000 - 2250000 - 750000 - 1235000 = 25765000

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 30000000,
            },
            {
                'code': 'GROSS',
                'amount': 30000000,
            },
            {
                'code': 'NET',
                'amount': 25765000,
            }])

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 12350000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 17650000,
            },
            {
                'code': 'TAXBASE',
                'amount': 12350000,
            },
            {
                'code': 'PTAX',
                'amount': -1235000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 1, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 12350000,
                'base': 12350000,
                'rate': 10,
                'tax_amount': 1235000
            },
        ])

    # 8. Phiếu lương
    def test_payslip_tax_escalation_1(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 9: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế lũy tiến
                TH1: Tính toán phiếu lương với hợp đồng có quy tắc thuế:
                        Chính sách thuế: lũy tiến
                        Thuế suất : bảng thuế lũy tiến theo VN
                        Áp dụng giảm trừ: không
                    Không có các khoản đăng ký đóng góp từ lương
                Output:
                    Các dòng thuế trong Bảng tính thuế luỹ tiến từng phần trong tab Chi tiết Thuế TNCN
                    3 dòng phiếu lương lương TBDED, TAXBASE, PTAX
        """
        # Contract: wage = 15.000.000 & set Rule tax non deduction
        self.contract_open_emp_A.write({
            'personal_tax_rule_id': self.tax_escalation_non_deduction.id
        })

        # Compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )
        payslip.compute_sheet()
        payslip_lines = payslip.line_ids

        # BASIC: 15.000.000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 15.000.000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 0
        # TAXBASE = GROSS (không áp dụng giảm trừ) = 15.000.000
        # PTAX: 3 dòng thuế lũy tiến = 1.500.000
        #     dòng thuế lũy tiến 5%: 250.000
        #     dòng thuế lũy tiến 10%: 500.000
        #     dòng thuế lũy tiến 15%: 750.000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 15.000.000 + 0 + 0 +0 - 1.500.000 = 13.500.000

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 15000000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 0,
            },
            {
                'code': 'TAXBASE',
                'amount': 15000000,
            },
            {
                'code': 'PTAX',
                'amount': -1500000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 3, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 15000000,
                'base': 5000000,
                'rate': 15,
                'tax_amount': 750000
            },
            {
                'upper_base': 10000000,
                'base': 5000000,
                'rate': 10,
                'tax_amount': 500000
            },
            {
                'upper_base': 5000000,
                'base': 5000000,
                'rate': 5,
                'tax_amount': 250000
            },
        ])

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 15000000,
            },
            {
                'code': 'GROSS',
                'amount': 15000000,
            },
            {
                'code': 'NET',
                'amount': 13500000,
            }])

    def test_payslip_tax_escalation_2(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 9: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế lũy tiến
                TH2: Giống TH1 bên trên, nhưng có các khoản đăng ký đóng góp từ lương
        """
        # Contract: wage = 15.000.000 & contribution registers & set Rule tax non deduction
        self.contract_open_emp_A.write({
            'personal_tax_rule_id': self.tax_escalation_non_deduction.id
        })
        self.contract_open_emp_A.payroll_contribution_register_ids.action_confirm()
        # tỷ lệ nhân viên trên mỗi kiểu đăng ký là 5%
        # => 5% * 15.000.000 = 750.000

        # Compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )
        payslip.compute_sheet()
        payslip_lines = payslip.line_ids

        # BASIC: 15.000.000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 15.000.000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = -(750.000 + 750.000 +750.000) = -2.250.000
        # DED_AFTER_TAX: 750.000
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 2.250.000
        # TAXBASE = GROSS (không áp dụng giảm trừ) = 15.000.000
        # PTAX: 3 dòng thuế lũy tiến = 1.500.000
        #     dòng thuế lũy tiến 5%: 250.000
        #     dòng thuế lũy tiến 10%: 500.000
        #     dòng thuế lũy tiến 15%: 750.000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 15.000.000 + 0 + -2.250.000 -750.000 - 1.500.000 = 10.500.000

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 15000000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 2250000,
            },
            {
                'code': 'TAXBASE',
                'amount': 15000000,
            },
            {
                'code': 'PTAX',
                'amount': -1500000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 3, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 15000000,
                'base': 5000000,
                'rate': 15,
                'tax_amount': 750000
            },
            {
                'upper_base': 10000000,
                'base': 5000000,
                'rate': 10,
                'tax_amount': 500000
            },
            {
                'upper_base': 5000000,
                'base': 5000000,
                'rate': 5,
                'tax_amount': 250000
            },
        ])

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 15000000,
            },
            {
                'code': 'GROSS',
                'amount': 15000000,
            },
            {
                'code': 'NET',
                'amount': 10500000,
            }])

    # 8. Phiếu lương
    def test_payslip_tax_escalation_3(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 9: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế lũy tiến
                TH3: Tính toán phiếu lương với hợp đồng có quy tắc thuế:
                        Chính sách thuế: lũy tiến
                        Thuế suất : bảng thuế lũy tiến theo VN
                        Áp dụng giảm trừ: Có
                            Giảm trừ Cơ sở tính Thuế thu nhập cá nhân: 11.000.000
                            Giảm trừ cho mỗi người phụ thuộc: 4.400.000
                    Không có các khoản đăng ký đóng góp từ lương
                    Không có phụ thuộc
                    Mức lương <= 11.000.000
                Output:
                    Không có dòng thuế trong Bảng tính thuế luỹ tiến từng phần trong tab Chi tiết Thuế TNCN
                    3 dòng phiếu lương lương TBDED, TAXBASE, PTAX
        """
        # Contract: wage = 10.000.000
        self.contract_open_emp_A.write({'wage': 10000000})

        # Compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )
        payslip.compute_sheet()
        payslip_lines = payslip.line_ids

        # BASIC: 10000000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 10000000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000
        # TAXBASE = GROSS - TBDED = 10000000 - 11000000 = -1000000 => 0 for negative
        # PTAX: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 10000000

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 0.0, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 11000000,
            },
            {
                'code': 'TAXBASE',
                'amount': 0.0,
            },
            {
                'code': 'PTAX',
                'amount': 0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        self.assertFalse(payslip.payslip_personal_income_tax_ids, 'Test payslip_personal_income_tax_ids field not ok')

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 10000000,
            },
            {
                'code': 'GROSS',
                'amount': 10000000,
            },
            {
                'code': 'NET',
                'amount': 10000000,
            }])

    def test_payslip_tax_escalation_4(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 9: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế lũy tiến
                TH4: Giống TH3 bên trên, nhưng mức lương đủ điều kiện đóng thuế
                    Output:
                        Các dòng thuế trong Bảng tính thuế luỹ tiến từng phần trong tab Chi tiết Thuế TNCN
                        3 dòng phiếu lương lương TBDED, TAXBASE, PTAX
        """
        # Contract: wage = 15.000.000 (default)

        # Compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )
        payslip.compute_sheet()
        payslip_lines = payslip.line_ids

        # BASIC: 15000000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 15000000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000
        # TAXBASE = GROSS - TBDED = 15000000 - 11000000 = 4000000
        # PTAX: thuế lũy tiến : -200000
        #     1 dòng thuế lũy tiến 5% : 200000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 15000000 - 200000 = 14800000

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 4000000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 11000000,
            },
            {
                'code': 'TAXBASE',
                'amount': 4000000,
            },
            {
                'code': 'PTAX',
                'amount': -200000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 1, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 4000000,
                'base': 4000000,
                'rate': 5,
                'tax_amount': 200000
            },
        ])

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 15000000,
            },
            {
                'code': 'GROSS',
                'amount': 15000000,
            },
            {
                'code': 'NET',
                'amount': 14800000,
            }])

    # 8. Phiếu lương
    def test_payslip_tax_escalation_5(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 9: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế lũy tiến
                TH5: Tính toán phiếu lương với hợp đồng có quy tắc thuế:
                        Chính sách thuế: lũy tiến
                        Thuế suất : bảng thuế lũy tiến theo VN
                        Áp dụng giảm trừ: Có
                            Giảm trừ Cơ sở tính Thuế thu nhập cá nhân: 11.000.000
                            Giảm trừ cho mỗi người phụ thuộc: 4.400.000
                    Có các khoản đăng ký đóng góp từ lương
                    Không có phụ thuộc
                    Mức lương  20.000.000 (đủ điều kiện đóng thuế)
                Output:
                    Các dòng thuế trong Bảng tính thuế luỹ tiến từng phần trong tab Chi tiết Thuế TNCN
                    3 dòng phiếu lương lương TBDED, TAXBASE, PTAX
        """
        # Contract: wage = 20.000.000 & contribution registers
        self.contract_open_emp_A.write({'wage': 20000000})
        self.contract_open_emp_A.payroll_contribution_register_ids.action_confirm()

        # Compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )
        payslip.compute_sheet()

        payslip_lines = payslip.line_ids

        # BASIC: 20000000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 20000000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: -750000*3 = -2250000
        # DED_AFTER_TAX: -750000
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000 + 2250000 = 13250000
        # TAXBASE = GROSS - TBDED = 20000000 - 13250000 = 6750000
        # PTAX: thuế lũy tiến : -425000
        #     1 dòng thuế lũy tiến 5% : 250000
        #     dòng thuế lũy tiến 10%: 1750000*10% = 175000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 20000000 - 2250000 - 750000 - 425000 = 16575000

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 6750000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 13250000,
            },
            {
                'code': 'TAXBASE',
                'amount': 6750000,
            },
            {
                'code': 'PTAX',
                'amount': -425000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 2, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 6750000,
                'base': 1750000,
                'rate': 10,
                'tax_amount': 175000
            },
            {
                'upper_base': 5000000,
                'base': 5000000,
                'rate': 5,
                'tax_amount': 250000
            },
        ])

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 20000000,
            },
            {
                'code': 'GROSS',
                'amount': 20000000,
            },
            {
                'code': 'NET',
                'amount': 16575000,
            }])

    # 8. Phiếu lương
    def test_payslip_tax_escalation_6(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 9: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - chính sách thuế lũy tiến
                TH6: giống TH5, nhưng nhân viên có 2 phụ thuộc
                    => Lương 20.000.000 sẽ không đủ điều kiện đóng thuế
        """
        # Contract: wage = 20.000.000 contribution registers
        self.contract_open_emp_A.write({'wage': 20000000})
        self.contract_open_emp_A.payroll_contribution_register_ids.action_confirm()

        # Employee
        self.product_emp_A.write({'total_dependant': 2})

        # Compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )
        payslip.compute_sheet()

        payslip_lines = payslip.line_ids

        # BASIC: 20000000 (tỷ lệ chi trả =1)
        # ALW : 0
        # GROSS = BASIC + ALW = 20000000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: -3*750000 = -2250000
        # DED_AFTER_TAX: -750000
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000 + 8800000 + 2250000 = 22050000
        # TAXBASE = GROSS - TBDED = 20000000 - 22050000 = -2050000 => 0 for negative
        # PTAX: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 20000000 - 2250000 - 750000 = 17000000

        # Test personal_tax_base field
        self.assertEqual(payslip.personal_tax_base, 0.0, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 22050000,
            },
            {
                'code': 'TAXBASE',
                'amount': 0.0,
            },
            {
                'code': 'PTAX',
                'amount': 0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        self.assertFalse(payslip.payslip_personal_income_tax_ids, 'Test payslip_personal_income_tax_ids field not ok')

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 20000000,
            },
            {
                'code': 'GROSS',
                'amount': 20000000,
            },
            {
                'code': 'NET',
                'amount': 17000000,
            }])

    # 8. Phiếu lương
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_personal_tax_13th_month_salary_1(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 11: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - Có đánh dấu lương tháng 13
                TH1: không áp dụng giảm trừ, chính sách thuế cố định
                VD: 2020 có 1 phiếu lương 15M,
                    => lương 13 là 15/12 = 1.250.000
                        => Thuế 125.000
        """
        # contract: wage = 15.000.000, tax: flat rate
        self.contract_close_emp_A.write({
            'personal_tax_rule_id': self.tax_flat_rate.id
        })

        # compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-7-1'),
            fields.Date.to_date('2020-7-31'),
        )
        payslip.action_payslip_verify()

        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True)
        payslip_13th.compute_sheet()
        payslip_lines = payslip_13th.line_ids

        # BASIC: 15.000.000 / 12 = 1.250.000
        # ALW : 0
        # GROSS = BASIC + ALW = 1.250.000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 0
        # TAXBASE = GROSS (không áp dụng giảm trừ) = 1.250.000
        # PTAX: 1 dòng thuế cố định = 10% *1.250.000 = 125.000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 1.250.000 - 125.000 = 1.125.000

        # Test personal_tax_base field
        self.assertEqual(payslip_13th.personal_tax_base, 1250000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 0,
            },
            {
                'code': 'TAXBASE',
                'amount': 1250000,
            },
            {
                'code': 'PTAX',
                'amount': -125000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 1, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 1250000,
                'base': 1250000,
                'rate': 10,
                'tax_amount': 125000
            },
        ])

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 1250000,
            },
            {
                'code': 'GROSS',
                'amount': 1250000,
            },
            {
                'code': 'NET',
                'amount': 1125000,
            }])

    # 8. Phiếu lương
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_personal_tax_13th_month_salary_3(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 11: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - Có đánh dấu lương tháng 13
                TH3: Có áp dụng giảm trừ, chính sách thuế cố định, không đủ điều kiện đóng thuế
                    * giảm trừ 11 triệu, 4,4 triệu cho mỗi phụ thuộc
                VD: 2020 có 1 phiếu lương 15M,
                    => lương 13 là 15/12 = 1.250.000
                        => không đủ đk đóng thuế
        """
        # contract: wage = 15.000.000, tax: flat rate
        self.contract_close_emp_A.write({
            'personal_tax_rule_id': self.tax_flat_rate_deduction.id
            })

        # compute payslip
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-7-1'),
            fields.Date.to_date('2020-7-31'),
            )
        payslip.action_payslip_verify()

        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True)
        payslip_13th.compute_sheet()

        payslip_lines = payslip_13th.line_ids

        # BASIC: 15000000/12 = 1250000
        # ALW : 0
        # GROSS = BASIC + ALW = 1250000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + phụ thuộc - DED_BEFORE_TAX = 11000000
        # TAXBASE = GROSS - TBDED = 1250000 - 11000000 = -9750000 => 0.0 for negative
        # PTAX: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 1250000

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 1250000,
            },
            {
                'code': 'GROSS',
                'amount': 1250000,
            },
            {
                'code': 'NET',
                'amount': 1250000,
            }])

        # Test personal_tax_base field
        self.assertEqual(payslip_13th.personal_tax_base, 0.0, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 11000000,
            },
            {
                'code': 'TAXBASE',
                'amount': 0.0,
            },
            {
                'code': 'PTAX',
                'amount': 0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        self.assertFalse(payslip_13th.payslip_personal_income_tax_ids,
                         'Test payslip_personal_income_tax_ids field not ok')

    # 8. Phiếu lương
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_personal_tax_13th_month_salary_4(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 11: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - Có đánh dấu lương tháng 13
                TH4: Có áp dụng giảm trừ, chính sách thuế cố định, đủ điều kiện đóng thuế
                    * giảm trừ 11 triệu
                VD: 2020 có 3 phiếu lương 50M
                    => lương 13 là 50*3/12 = 12500000
                        => đủ đk đóng thuế
        """
        # contract: wage = 50.000.000, tax: flat rate
        self.contract_close_emp_A.write({
            'wage': 50000000,
            'personal_tax_rule_id': self.tax_flat_rate_deduction.id
            })

        # compute payslip
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-7-1'),
            fields.Date.to_date('2020-7-31'),
            )
        payslip_1.action_payslip_verify()

        payslip_2 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-7-1'),
            fields.Date.to_date('2020-7-31'),
            )
        payslip_2.action_payslip_verify()

        payslip_3 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-7-1'),
            fields.Date.to_date('2020-7-31'),
            )
        payslip_3.action_payslip_verify()

        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True)
        payslip_13th.compute_sheet()
        payslip_lines = payslip_13th.line_ids

        # BASIC: 50M*3/12 = 12500000
        # ALW : 0
        # GROSS = BASIC + ALW = 12500000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000
        # TAXBASE = GROSS - TBDED = 12500000 - 11000000 = 1500000
        # PTAX: 1 dòng thuế cố định = 10% *1500000 = 150000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 12500000 - 150000 = 12350000

        # Test personal_tax_base field
        self.assertEqual(payslip_13th.personal_tax_base, 1500000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 11000000,
            },
            {
                'code': 'TAXBASE',
                'amount': 1500000,
            },
            {
                'code': 'PTAX',
                'amount': -150000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 1, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 1500000,
                'base': 1500000,
                'rate': 10,
                'tax_amount': 150000
            },
        ])

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 12500000,
            },
            {
                'code': 'GROSS',
                'amount': 12500000,
            },
            {
                'code': 'NET',
                'amount': 12350000,
            }
            ])

    # 8. Phiếu lương
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_personal_tax_13th_month_salary_2(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 11: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - Có đánh dấu lương tháng 13
                TH2: không áo dụng giảm trừ, chính sách thuế lũy tiến
                VD1: 2020 có 2 phiếu lương 48M, tổng là 96M
                    => lương 13 là 100/12 = 8M
                        => 2 dòng thuế mức 1&2
        """
        # contract: wage = 50.000.000, tax: escalation
        self.contract_close_emp_A.write({
            'wage': 48000000,
            'personal_tax_rule_id': self.tax_escalation_non_deduction.id
            })

        # payslip 1
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-7-1'),
            fields.Date.to_date('2020-7-31'),
            )
        payslip_1.action_payslip_verify()
        # payslip 2
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-7-1'),
            fields.Date.to_date('2020-7-31'),
            )
        payslip_1.action_payslip_verify()

        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True)
        payslip_13th.compute_sheet()
        payslip_lines = payslip_13th.line_ids

        # BASIC: 96.000.000 / 12 = 8.000.000
        # ALW : 0
        # GROSS = BASIC + ALW = 8.000.000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 0
        # TAXBASE = GROSS (không áp dụng giảm trừ) = 8.000.000
        # PTAX: 2 dòng thuế lũy tiến = 550.000
        #     dòng thuế lũy tiến 5%: 5.000.000 * 5% = 250.000
        #     dòng thuế lũy tiến 10%: 3.000.000 * 10* = 300.000
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 8.000.000 - 550.000 = 7.450.000

        # Test personal_tax_base field
        self.assertEqual(payslip_13th.personal_tax_base, 8000000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 0,
            },
            {
                'code': 'TAXBASE',
                'amount': 8000000,
            },
            {
                'code': 'PTAX',
                'amount': -550000,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 2, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 8000000,
                'base': 3000000,
                'rate': 10,
                'tax_amount': 300000
            },
            {
                'upper_base': 5000000,
                'base': 5000000,
                'rate': 5,
                'tax_amount': 250000
            }
        ])

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 8000000,
            },
            {
                'code': 'GROSS',
                'amount': 8000000,
            },
            {
                'code': 'NET',
                'amount': 7450000,
            }])

    # 8. Phiếu lương
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_personal_tax_13th_month_salary_5(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 11: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - Có đánh dấu lương tháng 13
                TH5: Có áp dụng giảm trừ, chính sách thuế lũy tiến, không đủ điều kiện đống thuế
                VD1: 2020 có 1 phiếu lương 50M,
                    => lương 13 là 50/12 ~ 4,1M
                        => không đủ đk đóng thuế

        """
        # contract: wage = 50.000.000, tax: escalation
        self.contract_close_emp_A.write({
            'wage': 50000000,
            })

        # compute payslip
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-7-1'),
            fields.Date.to_date('2020-7-31'),
            )
        payslip_1.action_payslip_verify()

        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True)
        payslip_13th.compute_sheet()

        payslip_lines = payslip_13th.line_ids

        # BASIC: 50000000/12 = 4166666.66667
        # ALW : 0
        # GROSS = BASIC + ALW = 4166666.66667
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + phụ thuộc - DED_BEFORE_TAX = 11000000
        # TAXBASE = GROSS - TBDED = 4166666.66667 - 11000000 = -6833333.33333 => 0.0 for negative
        # PTAX: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 4166666.66667

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        currency = payslip_13th.currency_id
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': currency.round(4166666.66667),
            },
            {
                'code': 'GROSS',
                'amount': currency.round(4166666.66667),
            },
            {
                'code': 'NET',
                'amount': currency.round(4166666.66667)
            }])

        # Test personal_tax_base field
        self.assertEqual(payslip_13th.personal_tax_base, 0.0, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 11000000,
            },
            {
                'code': 'TAXBASE',
                'amount': 0.0,
            },
            {
                'code': 'PTAX',
                'amount': 0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        self.assertFalse(payslip_13th.payslip_personal_income_tax_ids,
                         'Test payslip_personal_income_tax_ids field not ok')

        # 8. Phiếu lương

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_personal_tax_13th_month_salary_6(self):
        """
        8.2 Test Thông tin của phiếu lương
            Case 11: Test Thông tin Thuế TNCN sau khi tính toán phiếu lương - Có đánh dấu lương tháng 13
                TH6: Có áp dụng giảm trừ, chính sách thuế lũy tiến, đủ điều kiện đống thuế
                    * giảm trừ bản thân 11.000.000
                VD1: 2020 có 4 phiếu lương 50M,
                    => lương 13 là 250/12 ~ 16,6M

        """
        # contract: wage = 50.000.000, tax: escalation
        self.contract_close_emp_A.write({
            'wage': 50000000,
            })

        # compute payslip
        payslip_1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-7-1'),
            fields.Date.to_date('2020-7-31'),
            )
        payslip_1.action_payslip_verify()

        payslip_2 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-6-1'),
            fields.Date.to_date('2020-6-30'),
            )
        payslip_2.action_payslip_verify()

        payslip_3 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-5-1'),
            fields.Date.to_date('2020-5-31'),
            )
        payslip_3.action_payslip_verify()

        payslip_4 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-4-1'),
            fields.Date.to_date('2020-4-30'),
            )
        payslip_4.action_payslip_verify()

        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True)
        payslip_13th.compute_sheet()

        payslip_lines = payslip_13th.line_ids

        # BASIC: 50000000*4/12 = 16666666.6667
        # ALW : 0
        # GROSS = BASIC + ALW = 16666666.6667
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + phụ thuộc - DED_BEFORE_TAX = 11000000
        # TAXBASE = GROSS - TBDED = 16666666.6667 - 11000000 = 5666666.6667
        # PTAX: -316666.66667
        #     dòng thuế lũy tiến 5%: 5000000*5% = 250000
        #     dòng thuế lũy tiến 10%: 666666.6667*10% = 66666.66667
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 16666666.6667 - 316666.66667 = 16350000

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        currency = payslip_13th.currency_id
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': currency.round(16666666.6667),
            },
            {
                'code': 'GROSS',
                'amount': currency.round(16666666.6667),
            },
            {
                'code': 'NET',
                'amount': 16350000
            }])

        # Test personal_tax_base field
        self.assertEqual(payslip_13th.personal_tax_base, currency.round(5666666.6667),
                         'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 11000000,
            },
            {
                'code': 'TAXBASE',
                'amount': currency.round(5666666.6667),
            },
            {
                'code': 'PTAX',
                'amount': currency.round(-316666.66667),
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 2, 'Test payslip_personal_income_tax_ids field not ok')
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': currency.round(5666666.6667),
                'base': currency.round(666666.6667),
                'rate': 10,
                'tax_amount': currency.round(66666.6667)
            },
            {
                'upper_base': 5000000,
                'base': 5000000,
                'rate': 5,
                'tax_amount': 250000
            }
        ])
