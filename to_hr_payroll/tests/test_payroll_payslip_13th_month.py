from unittest.mock import patch
from odoo import fields
from .common import TestPayrollCommon, ADVANTAGE_CODE_LIST

# """
# Formulas on salary rules can change in other modules
#     so tests related to payslip lines will run at at_install
# """


class TestPayrollPayslip13thMonth(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollPayslip13thMonth, cls).setUpClass()
        # contract
        advantages = cls.env['hr.advantage.template'].search([('company_id', '=', cls.env.company.id)])
        cls.contract_close_emp_A.write({
            'date_start': fields.Date.to_date('2020-3-1'),
            'advantage_ids': [(0, 0, {'template_id': advantages[0].id, 'amount': 100000}),
                              (0, 0, {'template_id': advantages[1].id, 'amount': 200000}),
                              (0, 0, {'template_id': advantages[2].id, 'amount': 300000}),
                              (0, 0, {'template_id': advantages[3].id, 'amount': 400000}), ]
        })
        cls.contract_close_emp_A_trial = cls.create_contract(
            cls.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-2-28'),
            trial_end=fields.Date.to_date('2020-2-28'),
            state='close',
            wage=5000000)
        cls.contract_close_emp_A_trial.write({
            'trial_date_end': fields.Date.to_date('2020-2-28'),
            'advantage_ids': [(0, 0, {'template_id': advantages[0].id, 'amount': 50000}),
                              (0, 0, {'template_id': advantages[1].id, 'amount': 100000}),
                              (0, 0, {'template_id': advantages[2].id, 'amount': 150000}),
                              (0, 0, {'template_id': advantages[3].id, 'amount': 200000}), ]
        })
        # generate Work entries in the past
        cls.generate_work_entry(
            cls.contract_close_emp_A_trial,
            fields.Datetime.to_datetime('2020-01-01 00:00:00'),
            fields.Datetime.to_datetime('2020-12-31 23:59:59'))

        # payslip in 2020 (Trial)
        cls.payslip_2020_1 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-1-31'))

        cls.payslip_2020_2 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2020-2-1'),
            fields.Date.to_date('2020-2-28'))

        # payslip in 2020
        cls.payslip_2020_3 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2020-3-1'),
            fields.Date.to_date('2020-3-31'))

        cls.payslip_2020_4 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2020-4-1'),
            fields.Date.to_date('2020-4-30'))

        cls.payslip_2020_5 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2020-5-1'),
            fields.Date.to_date('2020-5-31'))

        cls.payslip_2020_6 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2020-6-1'),
            fields.Date.to_date('2020-6-30'))

    # 8.5 Test phiếu lương đánh dấu tháng 13
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_13th_payslip_1(self):
        """
        Case 1: Nhân viên không có phiếu lương nào trong khoảng thời gian xét lương tháng 13
            => Các thông tin của phiếu lương, các quy tắc tính lương 13, lương của dòng phiếu lương tương ứng = 0
        """
        (self.payslip_2020_1 + self.payslip_2020_2 + self.payslip_2020_3 + self.payslip_2020_4 + self.payslip_2020_5).unlink()
        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True)
        payslip_13th.compute_sheet()

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_13th.line_ids.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 0,
            },
            {
                'code': 'GROSS',
                'amount': 0,
            },
            {
                'code': 'NET',
                'amount': 0,
            }])

    # 8.5 Test phiếu lương đánh dấu tháng 13
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_13th_payslip_2(self):
        """
        Case 2: Nhân viên có phiếu lương năm xét lương 13,
                chu kỳ lương không lệch chuẩn và
                không đánh dấu bao gồm thử việc khi tính lương 13
            TH1: các phiếu lương trong năm xét lương ở trạng thái khác ở "Đang đợi" / "Hoàn thành"
                => các quy tắc tính lương 13, lương của dòng phiếu lương tương ứng = 0
        """

        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True)
        payslip_13th.compute_sheet()

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_13th.line_ids.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 0,
            },
            {
                'code': 'GROSS',
                'amount': 0,
            },
            {
                'code': 'NET',
                'amount': 0,
            }])

    # 8.5 Test phiếu lương đánh dấu tháng 13
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_13th_payslip_3(self):
        """
        Case 2: Nhân viên có phiếu lương năm xét lương 13, chu kỳ không lệch chuẩn, không đánh dấu bao gồm thử việc khi tính lương 13
            TH2A: Có phiếu lương trong năm xét lương ở trạng thái ở "Đang đợi" / "Hoàn thành"
                => lương của dòng phiếu lương tương ứng =  lương của tất cả dòng phiếu lương tương ứng của các phiếu lương ở "Đang đợi" / "Hoàn thành"
        """
        # wage = 15.000.000
        # có áp dụng giảm trừ 11.000.000
        # không có đóng góp từ lương
        self.payslip_2020_3.action_payslip_verify()
        self.payslip_2020_4.action_payslip_verify()
        self.payslip_2020_5.action_payslip_verify()
        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True)

        payslip_13th.compute_sheet()
        payslip_lines = payslip_13th.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        # Năm 2020 có 3 phiếu lương được xác nhận . tỷ lệ chi trả đầy đủ
        self.assertRecordValues(advantage_lines, [
            {
                'amount': 100000 * 3 / 12,  # 25.000
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': 200000 * 3 / 12,  # 50.000
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': 300000 * 3 / 12,  # 75.000
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': 400000 * 3 / 12,  # 100.000
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            }])

        # BASIC: 15.000.000*3 / 12 = 3.750.000
        # ALW : 250.000
        # GROSS = BASIC + ALW = 3.750.000 + 150.000 = 4.000.000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11.000.000
        # TAXBASE = GROSS - TBDED = 4.000.000 - 11.000.000 = -7.000.000 => 0 for negative
        # PTAX: không đủ điều kiện đóng thuế: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        # = 4.000.000

        # Test personal_tax_base field
        self.assertEqual(payslip_13th.personal_tax_base, 0, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 11000000,
            },
            {
                'code': 'TAXBASE',
                'amount': 0,
            },
            {
                'code': 'PTAX',
                'amount': 0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 0, 'Test payslip_personal_income_tax_ids field not ok')

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 3750000,
            },
            {
                'code': 'GROSS',
                'amount': 4000000,
            },
            {
                'code': 'NET',
                'amount': 4000000,
            }])

    # 8.5 Test phiếu lương đánh dấu tháng 13
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_13th_payslip_4(self):
        """
        Case 2: Nhân viên có phiếu lương năm xét lương 13, chu kỳ không lệch chuẩn, không đánh dấu bao gồm thử việc khi tính lương 13
            TH2B: Có phiếu lương trong năm xét lương ở trạng thái "Đang đợi/Hoàn thành", bao gồm cả phiếu lương ở hợp đồng thử việc
                => lương của dòng phiếu lương tương ứng =  lương của tất cả dòng phiếu lương tương ứng của các phiếu lương ở "Đang đợi" / "Hoàn thành"
                    Không bao gồm các phiếu lương nằm trong thời gian thử việc
        """
        self.payslip_2020_1.action_payslip_verify()
        self.payslip_2020_2.action_payslip_verify()
        self.payslip_2020_3.action_payslip_verify()
        self.payslip_2020_4.action_payslip_verify()
        self.payslip_2020_5.action_payslip_verify()
        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True)

        payslip_13th.compute_sheet()
        payslip_lines = payslip_13th.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        # Năm 2020 có 3 phiếu lương được xác nhận không phải là thử việc . tỷ lệ chi trả đầy đủ
        self.assertRecordValues(advantage_lines, [
            {
                'amount': 100000 * 3 / 12,
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': 200000 * 3 / 12,
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': 300000 * 3 / 12,
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': 400000 * 3 / 12,
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            }])

        # BASIC: 15.000.000*3 / 12 = 3.750.000
        # ALW : 250.000
        # GROSS = BASIC + ALW = 3.750.000 + 150.000 = 4.000.000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11.000.000
        # TAXBASE = GROSS - TBDED = 4.000.000 - 11.000.000 = -7.000.000 => 0 for negative
        # PTAX: không đủ điều kiện đóng thuế: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #     = 4.000.000

        # Test personal_tax_base field
        self.assertEqual(payslip_13th.personal_tax_base, 0, 'Test Personal Income Tax Base field not oke')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 11000000,
            },
            {
                'code': 'TAXBASE',
                'amount': 0,
            },
            {
                'code': 'PTAX',
                'amount': 0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 0, 'Test payslip_personal_income_tax_ids field not oke')

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 3750000,
            },
            {
                'code': 'GROSS',
                'amount': 4000000,
            },
            {
                'code': 'NET',
                'amount': 4000000,
            }])

    # 8.5 Test phiếu lương đánh dấu tháng 13
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_13th_payslip_5(self):
        """
        Case 2: Nhân viên có phiếu lương năm xét lương 13, chu kỳ không lệch chuẩn, không đánh dấu bao gồm thử việc khi tính lương 13
            TH4: Có phiếu lương trong năm xét lương ở trạng thái "Đang đợi/Hoàn thành", Các phiếu lương: có khoảng thời gian trùng nhau
                => Tính toán lương, bao gồm các phiếu lương trùng nhau
        """
        self.payslip_2020_3.action_payslip_verify()
        payslip_2 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-3-1'),
            fields.Date.to_date('2020-3-31'))
        payslip_2.action_payslip_verify()

        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True,
            trial=True)

        payslip_13th.compute_sheet()
        payslip_lines = payslip_13th.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        # Năm 2020 có 2 phiếu lương được xác nhận (đã trùng nhau) . tỷ lệ chi trả đầy đủ
        self.assertRecordValues(advantage_lines, [
            {
                'amount': 100000 * 2 / 12,  # 16.667
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': 200000 * 2 / 12,  # 33.333
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': 300000 * 2 / 12,  # 50.000
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': 400000 * 2 / 12,  # 66.666
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            }])

        # BASIC: 15.000.000*2 / 12 = 2.500.000
        # ALW : 166.667 ~ (2.000.000 / 12)
        # GROSS = BASIC + ALW = 2.500.000 + 166.667 = 2.666.667
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11.000.000
        # TAXBASE = GROSS - TBDED = 2.666.667 - 11.000.000 = -8.333.333 => 0 for negative
        # PTAX: không đủ điều kiện đóng thuế: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        # = 2.666.667

        currency = payslip_13th.currency_id
        # Test personal_tax_base field
        self.assertEqual(
            payslip_13th.personal_tax_base,
            0.0,
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
                'amount': 0.0,
            },
            {
                'code': 'PTAX',
                'amount': 0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 0, 'Test payslip_personal_income_tax_ids field not ok')

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 2500000,
            },
            {
                'code': 'GROSS',
                'amount': currency.round(2500000 + 166666.6667),
            },
            {
                'code': 'NET',
                'amount': currency.round(2500000 + 166666.6667),
            }])

    # 8.5 Test phiếu lương đánh dấu tháng 13
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_13th_payslip_6(self):
        """
        Case 2: Nhân viên có phiếu lương năm xét lương 13, chu kỳ không lệch chuẩn, không đánh dấu bao gồm thử việc khi tính lương 13
            TH5: Thay đổi Chu kỳ mặc định theo năm của phiếu lương T13 -> chỉ chọn một vài tháng
                => Tính toán các phiếu lương "Đang đợi / Hoàn thành" ở năm xét lương T13 và nằm trong khoảng thời gian của phiếu lương t13
        """
        self.payslip_2020_3.action_payslip_verify()
        self.payslip_2020_4.action_payslip_verify()
        self.payslip_2020_5.action_payslip_verify()
        self.payslip_2020_6.action_payslip_verify()

        # Khoảng thời gian phiếu lương t13 chỉ tính theo 3 tháng
        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-3-1'),
            fields.Date.to_date('2020-5-31'),
            thirteen_month_pay=True)

        payslip_13th.compute_sheet()
        payslip_lines = payslip_13th.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        # Năm 2020 có 3 phiếu lương được xác nhận trong năm 2020 . tỷ lệ chi trả đầy đủ
        self.assertRecordValues(advantage_lines, [
            {
                'amount': 100000 * 3 / 12,
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': 200000 * 3 / 12,
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': 300000 * 3 / 12,
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': 400000 * 3 / 12,
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            }])

        # BASIC: 15.000.000*3 / 12 = 3.750.000
        # ALW : 250.000
        # GROSS = BASIC + ALW = 3.750.000 + 150.000 = 4.000.000
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11.000.000
        # TAXBASE = GROSS - TBDED = 4.000.000 - 11.000.000 = -7.000.000 => 0.0 for negative
        # PTAX: không đủ điều kiện đóng thuế: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        # = 4.000.000

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
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 0, 'Test payslip_personal_income_tax_ids field not ok')

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 3750000,
            },
            {
                'code': 'GROSS',
                'amount': 4000000,
            },
            {
                'code': 'NET',
                'amount': 4000000,
            }])

    # 8.5 Test phiếu lương đánh dấu tháng 13
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_13th_payslip_7(self):
        """
        Case 2: Nhân viên có phiếu lương năm xét lương 13, chu kỳ không lệch chuẩn, không đánh dấu bao gồm thử việc khi tính lương 13
            TH5: Có phiếu lương trong năm xét lương ở trạng thái "Đang đợi/Hoàn thành", phiếu lương có chu kỳ lương ở 2 năm
                => Chỉ lấy những phiếu lương có ngày bắt đầu  và ngày kết thúc nằm trong năm xét lương tháng 13
        """
        self.payslip_2020_4.action_payslip_verify()
        self.payslip_2020_5.action_payslip_verify()

        payslip_2 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-12-1'),
            fields.Date.to_date('2021-1-1'))
        payslip_2.action_payslip_verify()

        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-4-1'),
            fields.Date.to_date('2020-5-31'),
            thirteen_month_pay=True)

        payslip_13th.compute_sheet()
        payslip_lines = payslip_13th.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        # Năm 2020 có 2 phiếu lương được xác nhận . tỷ lệ chi trả đầy đủ
        self.assertRecordValues(advantage_lines, [
            {
                'amount': 100000 * 2 / 12,
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': 200000 * 2 / 12,
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': 300000 * 2 / 12,
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': 400000 * 2 / 12,
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            }])

        # BASIC: 15.000.000*2 / 12 = 2.500.000
        # ALW : 166.667 ~ (2.000.000 / 12)
        # GROSS = BASIC + ALW = 2.500.000 + 166.667 = 2.666.667
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11.000.000
        # TAXBASE = GROSS - TBDED = 2.666.667 - 11.000.000 = -8.333.333 => 0 for negative
        # PTAX: không đủ điều kiện đóng thuế: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        # = 2.666.667

        currency = payslip_13th.currency_id
        # Test personal_tax_base field
        self.assertEqual(
            payslip_13th.personal_tax_base,
            0.0,
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
                'amount': 0.0,
            },
            {
                'code': 'PTAX',
                'amount': 0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 0, 'Test payslip_personal_income_tax_ids field not ok')

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 2500000,
            },
            {
                'code': 'GROSS',
                'amount': currency.round(2666666.667),
            },
            {
                'code': 'NET',
                'amount': currency.round(2666666.667),
            }])

    # 8.5 Test phiếu lương đánh dấu tháng 13
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_13th_payslip_8(self):
        """
        Case 3: Nhân viên có phiếu lương năm xét lương 13, chu kỳ lương không lệch chuẩn và có đánh dấu bao gồm thử việc khi tính lương 13
            Output: Các thông tin của phiếu lương được tính từ các phiếu lương hợp lệ của nhân viên, bao gồm các phiếu lương liên quan đến hợp đồng thử việc
        """
        self.payslip_2020_1.action_payslip_verify()
        self.payslip_2020_2.action_payslip_verify()
        self.payslip_2020_3.action_payslip_verify()
        self.payslip_2020_4.action_payslip_verify()
        self.payslip_2020_5.action_payslip_verify()
        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True,
            trial=True)

        payslip_13th.compute_sheet()
        payslip_lines = payslip_13th.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        # Năm 2020 có 5 phiếu lương được xác nhận . tỷ lệ chi trả đầy đủ
        # 2 phiếu lương  có sốt iền phụ cấp lần lượt là 50k - 100k - 150k - 200k
        # 3 phiếu lương có số tiền phụ cấp lần lượt là 100k - 200k - 300k - 400k
        self.assertRecordValues(advantage_lines, [
            {
                'amount': (50000 * 2 + 100000 * 3) / 12,  # 33333.3333333
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': (100000 * 2 + 200000 * 3) / 12,  # 66666.6666667
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': (150000 * 2 + 300000 * 3) / 12,  # 100000
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': (200000 * 2 + 400000 * 3) / 12,  # 133333.333333
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            }])

        # BASIC: (5.000.000*2 +  15.000.000*3) / 12 = 4583333.33333
        # ALW : 333333.333333
        # GROSS = BASIC + ALW = 4583333.33333 + 333333.333333 = 4916666.66666
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000
        # TAXBASE = GROSS - TBDED = 4916666.66666 - 11.000.000 = -6083333.33334 => 0 for negative
        # PTAX: không đủ điều kiện đóng thuế: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        # = 4916666.66666

        # Test personal_tax_base field
        self.assertEqual(
            payslip_13th.personal_tax_base,
            0.0,
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
                'amount': 0.0,
            },
            {
                'code': 'PTAX',
                'amount': 0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 0, 'Test payslip_personal_income_tax_ids field not ok')

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 4583333.33,
            },
            {
                'code': 'GROSS',
                'amount': 4916666.66,
            },
            {
                'code': 'NET',
                'amount': 4916666.66,
            }])

# 8.5 Test phiếu lương đánh dấu tháng 13
    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-7-20'))
    def test_13th_payslip_9(self):
        """
        Case 3: Phiếu lương T13 tính đúng trong khoảng thời gian được thiết lập
            - Nhân viên có các phiếu lương trong năm xét lương 13, chu kỳ lương không lệch chuẩn
            - Trong đó có phiêu lương có nhiều hợp đồng và đánh dấu bao gồm cả phiếu lương thử việc
            => Các thông tin của phiếu lương được tính từ các phiếu lương hợp lệ trong khoảng thời gian của nhân viên
        """
        # Payslip cyclce: 2020-02-01 -> 2020-03-31 (2 contracts)
        self.payslip_2020_2.write({'date_to': fields.Date.to_date('2020-03-31')})
        payslips_for_13th = self.payslip_2020_1 | self.payslip_2020_2 | self.payslip_2020_4 | self.payslip_2020_5
        payslips_for_13th.action_payslip_verify()

        payslip_13th = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-12-31'),
            thirteen_month_pay=True,
            trial=True)

        currency = payslip_13th.currency_id
        payslip_13th.compute_sheet()
        payslip_13th_lines = payslip_13th.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_13th_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertRecordValues(advantage_lines, [
            {
                'amount': currency.round(33333.33333),
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': currency.round(66666.6666667),
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': 100000,
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': currency.round(133333.333333),
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            }])

        # BASIC: (5.000.000 + 20.000.000 + 15.000.000*2) / 12 = 4583333.33333
        # ALW : 333333.333333
        # GROSS = BASIC + ALW = 4583333.33333 + 333333.333333 = 4916666.66666
        # ALWNOTAX : 0
        # DED_BEFORE_TAX: = 0
        # DED_AFTER_TAX: 0
        # TBDED = giảm trừ bản thân + giảm trừ phụ thuộc - DED_BEFORE_TAX = 11000000
        # TAXBASE = GROSS - TBDED = 4916666.66666 - 11.000.000 = -6083333.33334 => 0 for negative
        # PTAX: không đủ điều kiện đóng thuế: 0
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        # = 4916666.66666

        # Test personal_tax_base field
        self.assertEqual(payslip_13th.personal_tax_base, 0.0)

        # Test tax on payslip lines
        ps_lines_tax = payslip_13th_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
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
                'amount': 0.0,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = payslip_13th.payslip_personal_income_tax_ids
        self.assertEqual(len(income_taxs), 0, 'Test payslip_personal_income_tax_ids field not ok')

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_13th_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 4583333.33,
            },
            {
                'code': 'GROSS',
                'amount': 4916666.66,
            },
            {
                'code': 'NET',
                'amount': 4916666.66,
            }])
