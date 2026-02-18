from odoo import fields

from .common import TestPayrollCommon, ADVANTAGE_CODE_LIST

# """
#     Formulas on salary rules can change in other modules
#         so tests related to payslip lines will run at at_install
# """


class TestPayrollPayslipAdvantage(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollPayslipAdvantage, cls).setUpClass()

        advantages = cls.env['hr.advantage.template'].search(
            [('company_id', '=', cls.env.company.id),
             ('code', 'in', ADVANTAGE_CODE_LIST)])
        cls.contract_open_emp_A.write({
            'wage': 5000000,  # không đủ điện kiện đóng thuế, không test các dòng thuế ở đây
            'advantage_ids': [(0, 0, {'template_id': advantages[0].id, 'amount': 100000}),
                              (0, 0, {'template_id': advantages[1].id, 'amount': 200000}),
                              (0, 0, {'template_id': advantages[2].id, 'amount': 300000}),
                              (0, 0, {'template_id': advantages[3].id, 'amount': 400000}),
                              (0, 0, {'template_id': advantages[4].id, 'amount': 500000}),
                              (0, 0, {'template_id': advantages[5].id, 'amount': 600000}),
                              (0, 0, {'template_id': advantages[6].id, 'amount': 700000})]
        })
        # lương đầy đủ: tiên phụ cấp là 2800000

        # leave request: 7-9/7/2021
        leave_type = cls.env['hr.leave.type'].search(
            [('unpaid', '=', True)], limit=1)
        cls.holiday_t7 = cls.create_holiday(
            'Test Leave 1',
            cls.product_emp_A.id,
            leave_type.id,
            fields.Datetime.to_datetime('2021-07-07 06:00:00'),
            fields.Datetime.to_datetime('2021-07-09 20:00:00'))

        # leave request: 10/8/2021
        cls.holiday_t8 = cls.create_holiday(
            'Test Leave 1',
            cls.product_emp_A.id,
            leave_type.id,
            fields.Datetime.to_datetime('2021-08-10 06:00:00'),
            fields.Datetime.to_datetime('2021-08-10 20:00:00'))
        # leave request: 20/9/2021
        cls.holiday_t9 = cls.create_holiday(
            'Test Leave 1',
            cls.product_emp_A.id,
            leave_type.id,
            fields.Datetime.to_datetime('2021-09-20 06:00:00'),
            fields.Datetime.to_datetime('2021-09-20 20:00:00'))

        # payslip
        cls.payslip_full_t7 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'))

        cls.payslip_t7 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2021-7-5'),
            fields.Date.to_date('2021-7-25'))

        cls.payslip_full_t7_t8 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
          fields.Date.to_date('2021-8-31'))

        cls.payslip_t7_t8_t9 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2021-7-5'),
            fields.Date.to_date('2021-9-20'))

        # Prepare data for payslips (13th month salary)
        cls.contract_close_emp_A.write({
            'advantage_ids': [(0, 0, {'template_id': advantages[0].id, 'amount': 100000}),
                              (0, 0, {'template_id': advantages[1].id, 'amount': 200000}),
                              (0, 0, {'template_id': advantages[2].id, 'amount': 300000}),
                              (0, 0, {'template_id': advantages[3].id, 'amount': 400000}),
                              (0, 0, {'template_id': advantages[4].id, 'amount': 500000}),
                              (0, 0, {'template_id': advantages[5].id, 'amount': 600000}),
                              (0, 0, {'template_id': advantages[6].id, 'amount': 700000})]
        })

        cls.payslip_13th_2020 = cls.env['hr.payslip'].with_context(tracking_disable=True).create({
            'employee_id':  cls.product_emp_A.id,
            'date_from': fields.Date.to_date('2020-1-1'),
            'date_to': fields.Date.to_date('2020-12-31'),
            'thirteen_month_pay': True,
            'thirteen_month_pay_year': 2020,
            'company_id': cls.env.company.id,
            'salary_cycle_id': cls.env.company.salary_cycle_id.id
        })

        cls.payslip_2020_1 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2020-1-1'),
            fields.Date.to_date('2020-1-31'))

        cls.payslip_2020_2 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2020-2-1'),
            fields.Date.to_date('2020-2-28'))

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

    # 10. Dòng phiếu lương
    def test_payslip_line_advantage_1(self):
        """
        Case 1A: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - Không đánh dấu lương tháng 13
            TH1: Hợp đồng không có phụ cấp
                => Không tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
        """
        self.contract_open_emp_A.write({'advantage_ids': [(6, 0, 0)]})
        self.payslip_full_t7.compute_sheet()

        advantage_lines = self.payslip_full_t7.line_ids.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertFalse(advantage_lines, 'Test payslip lines for advantages not ok')

        salary_lines = self.payslip_full_t7.line_ids.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 5000000,
            },
            {
                'code': 'GROSS',
                'amount': 5000000,
            },
            {
                'code': 'NET',
                'amount': 5000000,
            }])

    # 10. Dòng phiếu lương
    def test_payslip_line_advantage_2(self):
        """
        Case 1A: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - Không đánh dấu lương tháng 13
            TH2: Hợp đồng có các khoản phụ cấp = 0
                => Không tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
        """
        self.contract_open_emp_A.advantage_ids.write({'amount': 0})
        self.payslip_full_t7.compute_sheet()

        advantage_lines = self.payslip_full_t7.line_ids.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertFalse(advantage_lines, 'Test payslip lines for advantages not ok')

        salary_lines = self.payslip_full_t7.line_ids.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 5000000,
            },
            {
                'code': 'GROSS',
                'amount': 5000000,
            },
            {
                'code': 'NET',
                'amount': 5000000,
            }])

    # 10. Dòng phiếu lương
    def test_payslip_line_advantage_3(self):
        """
        Case 1A: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - Không đánh dấu lương tháng 13
            TH3: Hợp đồng:
                    Có các khoản phụ cấp > 0
                Phiếu lương:
                    Không đánh dấu lương tháng 13
                    Phiếu lương nằm trong 1 tháng, số ngày đủ 1 tháng
                Nghỉ:
                    không có ngày nghỉ không lương

                Output:
                    Tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
                        * Số tiền trên dòng phiếu lương = Tổng của (số tiền phụ cấp * tỷ lệ chi trả) trên tất cả các dòng chi tiết lịch làm việc
                        * tỷ lệ chi trả đã được test ở Case 2B mục 8.2 Test Thông tin của phiếu lương
        """
        # Phiếu lương tháng 7, số ngày đủ 1 tháng, không có ngày nghỉ
        self.payslip_full_t7.compute_sheet()

        advantage_payslip_lines = self.payslip_full_t7.line_ids.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_payslip_lines), 7, 'Test payslip lines for advantages not ok')
        payslip_lines = self.payslip_full_t7.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_lines), 7, 'Test payslip lines for advantages not ok')
        # tỷ lệ chi trả = 1
        self.assertRecordValues(advantage_lines, [
            {
                'amount': 100000,
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': 200000,
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': 300000,
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': 400000,
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            },
            {
                'amount': 500000,
                'sequence': 570,
                'code': 'HARDWORK'
            },
            {
                'amount': 600000,
                'sequence': 580,
                'code': 'PERFORMANCE'
            },
            {
                'amount': 700000,
                'sequence': 4100,
                'code': 'HARMFUL'
            }, ])

        salary_lines = self.payslip_full_t7.line_ids.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 5000000,
            },
            {
                'code': 'GROSS',
                'amount': 7100000,
            },
            {
                'code': 'NET',
                'amount': 7800000,
            }])

    def test_payslip_line_advantage_4(self):
        """
        Case 1A: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - Không đánh dấu lương tháng 13
            TH4: Hợp đồng:
                    Có các khoản phụ cấp > 0
                Phiếu lương:
                    Không đánh dấu lương tháng 13
                    Phiếu lương nằm trong 1 tháng, số ngày đủ 1 tháng
                Nghỉ:
                    Có ngày nghỉ không lương

                Output:
                    Tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
                        * Số tiền trên dòng phiếu lương = Tổng của (số tiền phụ cấp * tỷ lệ chi trả) trên tất cả các dòng chi tiết lịch làm việc
                        * tỷ lệ chi trả đã được test ở Case 2B mục 8.2 Test Thông tin của phiếu lương
        """
        # Phiếu lương tháng 7, số ngày đủ 1 tháng, có ngày nghỉ
        self.holiday_t7.action_validate()
        self.payslip_full_t7.compute_sheet()
        payslip_lines = self.payslip_full_t7.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_lines), 7, 'Test payslip lines for advantages not ok')
        # nghỉ không lương từ 7/7 đến 9/9 => 3 ngày (24 giờ)
        # tháng 7 : 22 ngày (176 giờ)
        # tỷ lệ chi trả (theo giờ): (176-24) / 176  = 0.86363636363
        currency = self.payslip_full_t7.currency_id
        self.assertRecordValues(advantage_lines, [
            {
                'amount': currency.round(86363.636363),  # 100000 * 0.86363636363
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': currency.round(172727.272726),  # 200000 * 0.86363636363
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': currency.round(259090.909089),  # 300000 * 0.86363636363
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': currency.round(345454.545452),  # 400000 * 0.86363636363
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            },
            {
                'amount': currency.round(431818.181815),  # 500000 * 0.86363636363
                'sequence': 570,
                'code': 'HARDWORK'
            },
            {
                'amount': currency.round(518181.818178),  # 600000 * 0.86363636363
                'sequence': 580,
                'code': 'PERFORMANCE'
            },
            {
                'amount': currency.round(604545.454541),  # 700000 * 0.86363636363
                'sequence': 4100,
                'code': 'HARMFUL'
            }, ])

        salary_lines = self.payslip_full_t7.line_ids.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 4318181.82,
            },
            {
                'code': 'GROSS',
                'amount': 6131818.19,
            },
            {
                'code': 'NET',
                'amount': 6736363.64,
            }])

    def test_payslip_line_advantage_5(self):
        """
        Case 1A: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - Không đánh dấu lương tháng 13
            TH5: Hợp đồng:
                    Có các khoản phụ cấp > 0
                Phiếu lương:
                    Không đánh dấu lương tháng 13
                    Phiếu lương nằm trong 1 tháng, số ngày không đủ 1 tháng
                Nghỉ:
                    không có ngày nghỉ không lương

                Output:
                    Tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
                        * Số tiền trên dòng phiếu lương = Tổng của (số tiền phụ cấp * tỷ lệ chi trả) trên tất cả các dòng chi tiết lịch làm việc
                        * tỷ lệ chi trả đã được test ở Case 2B mục 8.2 Test Thông tin của phiếu lương
        """
        # Phiếu lương tháng 7, số ngày không đủ 1 tháng, không có ngày nghỉ
        self.payslip_t7.compute_sheet()
        payslip_lines = self.payslip_t7.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_lines), 7, 'Test payslip lines for advantages not ok')
        # làm từ 5/7 đến 25/7 => 15 ngày (120 giờ)
        # tháng 7 : 22 ngày (176 giờ)
        # tỷ lệ chi trả (theo giờ): 120 / 176  = 0.68181818181
        currency = self.payslip_t7.currency_id
        self.assertRecordValues(advantage_lines, [
            {
                'amount': currency.round(68181.818181),  # 100000 * 0.68181818181
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': currency.round(136363.636362),  # 200000 * 0.68181818181
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': currency.round(204545.4545),  # 300000 * 0.68181818181
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': currency.round(272727.272724),  # 400000 * 0.68181818181
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            },
            {
                'amount': currency.round(340909.090905),  # 500000 * 0.68181818181
                'sequence': 570,
                'code': 'HARDWORK'
            },
            {
                'amount': currency.round(409090.909086),  # 600000 * 0.68181818181
                'sequence': 580,
                'code': 'PERFORMANCE'
            },
            {
                'amount': currency.round(477272.727267),  # 700000 * 0.68181818181
                'sequence': 4100,
                'code': 'HARMFUL'
            }, ])

        salary_lines = self.payslip_t7.line_ids.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': currency.round(3409090.90905),
            },
            {
                'code': 'GROSS',
                'amount': currency.round(4840909.09085),
            },
            {
                'code': 'NET',
                'amount': currency.round(5318181.81812),
            }])

    def test_payslip_line_advantage_6(self):
        """
        Case 1A: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - Không đánh dấu lương tháng 13
            TH6: Hợp đồng:
                    Có các khoản phụ cấp > 0
                Phiếu lương:
                    Không đánh dấu lương tháng 13
                    Phiếu lương nằm trong 1 tháng, số ngày không đủ 1 tháng
                Nghỉ:
                    Có ngày nghỉ không lương

                Output:
                    Tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
                        * Số tiền trên dòng phiếu lương = Tổng của (số tiền phụ cấp * tỷ lệ chi trả) trên tất cả các dòng chi tiết lịch làm việc
                        * tỷ lệ chi trả đã được test ở Case 2B mục 8.2 Test Thông tin của phiếu lương
        """
        # Phiếu lương tháng 7, số ngày không đủ 1 tháng, có ngày nghỉ
        self.holiday_t7.action_validate()
        self.payslip_t7.compute_sheet()
        payslip_lines = self.payslip_t7.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_lines), 7, 'Test payslip lines for advantages not ok')
        # làm từ 5/7 đến 25/7 => 15 ngày (120 giờ)
        # nghỉ không lương 7/7 đến 9/7: 3 ngày (24 giờ)
        # tháng 7 : 22 ngày (176 giờ)
        # tỷ lệ chi trả (theo giờ): (120-24) / 176  = 0.54545454545
        currency = self.payslip_t7.currency_id
        self.assertRecordValues(advantage_lines, [
            {
                'amount': currency.round(54545.454545),  # 100000 * 0.54545454545
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': currency.round(109090.90909),  # 200000 * 0.54545454545
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': currency.round(163636.363635),  # 300000 * 0.54545454545
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': currency.round(218181.81818),  # 400000 * 0.54545454545
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            },
            {
                'amount': currency.round(272727.272725),  # 500000 * 0.54545454545
                'sequence': 570,
                'code': 'HARDWORK'
            },
            {
                'amount': currency.round(327272.72727),  # 600000 * 0.54545454545
                'sequence': 580,
                'code': 'PERFORMANCE'
            },
            {
                'amount': currency.round(381818.181815),  # 700000 * 0.54545454545
                'sequence': 4100,
                'code': 'HARMFUL'
            }, ])

        salary_lines = self.payslip_t7.line_ids.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': currency.round(2727272.72725),
            },
            {
                'code': 'GROSS',
                'amount': currency.round(3872727.2727),
            },
            {
                'code': 'NET',
                'amount': currency.round(4254545.45451),
            }])

    def test_payslip_line_advantage_7(self):
        """
        Case 1A: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - Không đánh dấu lương tháng 13
            TH7: Hợp đồng:
                    Có các khoản phụ cấp > 0
                Phiếu lương:
                    Không đánh dấu lương tháng 13
                    Phiếu lương nằm trong nhiều tháng, số ngày mỗi tháng đủ 1 tháng
                Nghỉ:
                    Không có ngày nghỉ không lương

                Output:
                    Tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
                        * Số tiền trên dòng phiếu lương = Tổng của (số tiền phụ cấp * tỷ lệ chi trả) trên tất cả các dòng chi tiết lịch làm việc
                        * tỷ lệ chi trả đã được test ở Case 2B mục 8.2 Test Thông tin của phiếu lương
        """
        # Phiếu lương tháng 7 và tháng 8, số ngày mỗi tháng đủ 1 tháng, không có ngày nghỉ
        self.payslip_full_t7_t8.compute_sheet()
        payslip_lines = self.payslip_full_t7_t8.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_lines), 7, 'Test payslip lines for advantages not ok')
        # tháng 7, tháng 8 làm đủ, tỷ lệ chi trả mỗi tháng là 1
        self.assertRecordValues(advantage_lines, [
            {
                'amount': 200000,  # 100k *1 *2
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': 400000,  # 200k *1 *2
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': 600000,  # 300k *1 *2
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': 800000,  # 400k *1 *2
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            },
            {
                'amount': 1000000,  # 500k *1 *2
                'sequence': 570,
                'code': 'HARDWORK'
            },
            {
                'amount': 1200000,  # 600k *1 *2
                'sequence': 580,
                'code': 'PERFORMANCE'
            },
            {
                'amount': 1400000,  # 700k *1 *2
                'sequence': 4100,
                'code': 'HARMFUL'
            }, ])

    def test_payslip_line_advantage_8(self):
        """
        Case 1A: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - Không đánh dấu lương tháng 13
            TH8: Hợp đồng:
                    Có các khoản phụ cấp > 0
                Phiếu lương:
                    Không đánh dấu lương tháng 13
                    Phiếu lương nằm trong nhiều tháng, số ngày mỗi tháng đủ 1 tháng
                Nghỉ:
                    Có ngày nghỉ không lương

                Output:
                    Tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
                        * Số tiền trên dòng phiếu lương = Tổng của (số tiền phụ cấp * tỷ lệ chi trả) trên tất cả các dòng chi tiết lịch làm việc
                        * tỷ lệ chi trả đã được test ở Case 2B mục 8.2 Test Thông tin của phiếu lương
        """
        # Phiếu lương tháng 7 và tháng 8, số ngày mỗi tháng đủ 1 tháng, có ngày nghỉ
        self.holiday_t7.action_validate()
        self.holiday_t8.action_validate()
        self.payslip_full_t7_t8.compute_sheet()
        payslip_lines = self.payslip_full_t7_t8.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_lines), 7, 'Test payslip lines for advantages not ok')
        # tháng 7: 22 ngày (176 giờ)
        #     nghỉ từ 7/7 đến 9/7 => 3 ngày (24 giờ)
        #     tỷ lệ chi trả (theo giờ): (176-24) / 176  = 0.86363636363
        # tháng 8: 22 ngày (176 giờ)
        #     nghỉ ngày 10/8 (8 giờ)
        #     tỷ lệ chi trả (theo giờ): (176-8) / 176  = 0.95454545454

        curency = self.payslip_full_t7_t8.currency_id
        self.assertRecordValues(advantage_lines, [
            {
                'amount': curency.round(181818.181817),  # 100000 * 0.86363636363 + 100000 * 0.95454545454,
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': curency.round(363636.363634),  # 200000 * 0.86363636363 + 200000 * 0.95454545454,
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': curency.round(545454.545451),  # 300000 * 0.86363636363 + 300000 * 0.95454545454,
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': curency.round(727272.727268),  # 400000 * 0.86363636363 + 400000 * 0.95454545454,
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            },
            {
                'amount': curency.round(909090.909085),  # 500000 * 0.86363636363 + 500000 * 0.95454545454,
                'sequence': 570,
                'code': 'HARDWORK'
            },
            {
                'amount': curency.round(1090909.0909),  # 600000 * 0.86363636363 + 600000 * 0.95454545454,
                'sequence': 580,
                'code': 'PERFORMANCE'
            },
            {
                'amount': curency.round(1272727.27272),  # 700000 * 0.86363636363 + 700000 * 0.95454545454,
                'sequence': 4100,
                'code': 'HARMFUL'
            }, ])

    def test_payslip_line_advantage_9(self):
        """
        Case 1A: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - Không đánh dấu lương tháng 13
            TH9: Hợp đồng:
                    Có các khoản phụ cấp > 0
                Phiếu lương:
                    Không đánh dấu lương tháng 13
                    Phiếu lương nằm trong nhiều tháng, có tháng đủ ngày, có tháng không đủ ngày
                Nghỉ:
                    Không có ngày nghỉ không lương

                Output:
                    Tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
                        * Số tiền trên dòng phiếu lương = Tổng của (số tiền phụ cấp * tỷ lệ chi trả) trên tất cả các dòng chi tiết lịch làm việc
                        * tỷ lệ chi trả đã được test ở Case 2B mục 8.2 Test Thông tin của phiếu lương
        """
        # Phiếu lương tháng 7,8,9, không có ngày nghỉ
        self.payslip_t7_t8_t9.compute_sheet()
        payslip_lines = self.payslip_t7_t8_t9.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_lines), 7, 'Test payslip lines for advantages not ok')
        # tháng 7: 5/7 - 31/7 => 20 ngày (160 giờ)
        #     tỷ lệ chi trả (theo giờ): 160 / 176  = 0.90909090909
        # tháng 8: 1/8 - 31/8
        #     tỷ lệ chi trả (theo giờ): 1
        # tháng 9: 1/9 - 20/9 => 14 ngày (112 giờ)
        #     tỷ lệ chi trả (theo giờ): 112 / 176  = 0.63636363636
        curency = self.payslip_t7_t8_t9.currency_id
        self.assertRecordValues(advantage_lines, [
            {
                'amount': curency.round(254545.454545),  # 100000 * 0.90909090909 + 100000 + 100000 * 0.63636363636,
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': curency.round(509090.90909),  # 200000 * 0.90909090909 + 200000 + 200000 * 0.63636363636,
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': curency.round(763636.363635),  # 300000 * 0.90909090909 + 300000 + 300000 * 0.63636363636,
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': curency.round(1018181.81818),  # 400000 * 0.90909090909 + 400000 + 400000 * 0.63636363636,
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            },
            {
                'amount': curency.round(1272727.27273),  # 500000 * 0.90909090909 + 500000 + 500000 * 0.63636363636,
                'sequence': 570,
                'code': 'HARDWORK'
            },
            {
                'amount': curency.round(1527272.72727),  # 600000 * 0.90909090909 + 600000 + 600000 * 0.63636363636,
                'sequence': 580,
                'code': 'PERFORMANCE'
            },
            {
                'amount': curency.round(1781818.18182),  # 700000 * 0.90909090909 + 700000 + 700000 * 0.63636363636,
                'sequence': 4100,
                'code': 'HARMFUL'
            }, ])

    def test_payslip_line_advantage_10(self):
        """
        Case 1A: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - Không đánh dấu lương tháng 13
            TH10: Hợp đồng:
                    Có các khoản phụ cấp > 0
                Phiếu lương:
                    Không đánh dấu lương tháng 13
                    Phiếu lương nằm trong nhiều tháng, có tháng đủ ngày, có tháng không đủ ngày
                Nghỉ:
                    Có ngày nghỉ không lương

                Output:
                    Tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
                        * Số tiền trên dòng phiếu lương = Tổng của (số tiền phụ cấp * tỷ lệ chi trả) trên tất cả các dòng chi tiết lịch làm việc
                        * tỷ lệ chi trả đã được test ở Case 2B mục 8.2 Test Thông tin của phiếu lương
        """
        # Phiếu lương tháng 7,8,9, có ngày nghỉ
        self.holiday_t7.action_validate()
        self.holiday_t8.action_validate()
        self.holiday_t9.action_validate()
        self.payslip_t7_t8_t9.compute_sheet()
        payslip_lines = self.payslip_t7_t8_t9.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_lines), 7, 'Test payslip lines for advantages not ok')
        # tháng 7: 5/7 - 31/7 => 20 ngày (160 giờ)
        #    nghỉ 7/7 đến 9/7 => nghỉ 3 ngày (24 giờ)
        #    tỷ lệ chi trả (theo giờ): (160-24) / 176  = 0.77272727272
        # tháng 8: 1/8 - 31/8
        #    nghỉ ngày 10/8 (8 giờ)
        #     tỷ lệ chi trả (theo giờ): (176 -8) / 176 = 0.95454545454
        # tháng 9: 1/9 - 20/9 => 14 ngày (112 giờ)
        #    nghỉ ngày 20/9 (8 giờ)
        #    tỷ lệ chi trả (theo giờ): (112-8) / 176  = 0.5909090909
        curency = self.payslip_t7_t8_t9.currency_id
        self.assertRecordValues(advantage_lines, [
            {
                'amount': curency.round(231818.181816),  # 100000 * 0.77272727272 + 100000*0.95454545454 + 100000 * 0.5909090909,
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': curency.round(463636.363632),  # 200000 * 0.77272727272 + 200000*0.95454545454 + 200000 * 0.5909090909,
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': curency.round(695454.545448),  # 300000 * 0.77272727272 + 300000*0.95454545454 + 300000 * 0.5909090909,
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': curency.round(927272.727264),  # 400000 * 0.77272727272 + 400000*0.95454545454 + 400000 * 0.5909090909,
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            },
            {
                'amount': curency.round(1159090.90908),  # 500000 * 0.77272727272 + 500000*0.95454545454 + 500000 * 0.5909090909,
                'sequence': 570,
                'code': 'HARDWORK'
            },
            {
                'amount': curency.round(1390909.0909),  # 600000 * 0.77272727272 + 600000*0.95454545454 + 600000 * 0.5909090909,
                'sequence': 580,
                'code': 'PERFORMANCE'
            },
            {
                'amount': curency.round(1622727.27271),  # 700000 * 0.77272727272 + 700000*0.95454545454 + 700000 * 0.5909090909,
                'sequence': 4100,
                'code': 'HARMFUL'
            }, ])

    # 10. Dòng phiếu lương
    def test_payslip_line_advantage_13th_1(self):
        """
        Case 1B: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - có đánh dấu lương tháng 13
            TH1: Hợp đồng không có phụ cấp
                => Không tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
        """
        self.contract_close_emp_A.write({'advantage_ids': [(6, 0, 0)]})
        self.payslip_13th_2020.compute_sheet()

        advantage_lines = self.payslip_13th_2020.line_ids.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertFalse(advantage_lines, 'Test payslip lines for advantages not ok')

    # 10. Dòng phiếu lương
    def test_payslip_line_advantage_13th_2(self):
        """
        Case 1B: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - có đánh dấu lương tháng 13
            TH2: Hợp đồng có các khoản phụ cấp = 0
                => Không tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
        """
        self.contract_close_emp_A.advantage_ids.write({'amount': 0})
        self.payslip_13th_2020.compute_sheet()

        advantage_lines = self.payslip_13th_2020.line_ids.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertFalse(advantage_lines, 'Test payslip lines for advantages not ok')

    # 10. Dòng phiếu lương
    def test_payslip_line_advantage_13th_3(self):
        """
        Case 1B: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - có đánh dấu lương tháng 13
            TH3:
                Hợp đồng có các khoản phụ cấp > 0
                Chưa có phiếu lương nào được xác nhận / hoàn thành trong năm xét lương 13
            Output:
                Tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
                Tổng số tiền của các dòng phiếu lương liên quan đến phụ cấp = 0
        """
        self.payslip_13th_2020.compute_sheet()

        advantage_lines = self.payslip_13th_2020.line_ids.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(sum(advantage_lines.mapped('total')), 0, 'Test payslip lines for advantages not ok')

    # 10. Dòng phiếu lương
    def test_payslip_line_advantage_13th_4(self):
        """
        Case 1B: Dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng - có đánh dấu lương tháng 13
            TH4: Hợp đồng có các khoản phụ cấp > 0
                Có phiếu lương được xác nhận / hoàn thành trong năm xét lương 13
            Output:
                Tạo các dòng phiếu lương liên quan đến các khoản phụ cấp trên hợp đồng
                * Số tiền trên từngdòng phiếu lương = Tổng của số tiền phụ cấp trên các dòng phiếu lương trong năm xét lương tháng 13  /  12
        """
        payslip_for_13th = self.env['hr.payslip']

        # 1: 1 phiếu lương được xác nhận, 4 phiếu lương dự thảo
        self.payslip_2020_1.action_payslip_verify()
        payslip_for_13th |= self.payslip_2020_1
        self.payslip_13th_2020.compute_sheet()
        payslip_lines = self.payslip_13th_2020.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_lines), 7, 'Test payslip lines for advantages not ok')
        # Năm 2020 có 1 phiếu lương được xác nhận . tỷ lệ chi trả đầy đủ
        self.assertRecordValues(advantage_lines, [
            {
                'amount': 100000 / 12,
                'sequence': 530,
                'code': 'TRAVEL'
            },
            {
                'amount': 200000 / 12,
                'sequence': 540,
                'code': 'PHONE'
            },
            {
                'amount': 300000 / 12,
                'sequence': 550,
                'code': 'MEAL'
            },
            {
                'amount': 400000 / 12,
                'sequence': 560,
                'code': 'RESPONSIBILITY'
            },
            {
                'amount': 500000 / 12,
                'sequence': 570,
                'code': 'HARDWORK'
            },
            {
                'amount': 600000 / 12,
                'sequence': 580,
                'code': 'PERFORMANCE'
            },
            {
                'amount': 700000 / 12,
                'sequence': 4100,
                'code': 'HARMFUL'
            }, ])

        # 2: 3 phiếu lương được xác nhân, 2 phiếu lương dự thảo
        self.payslip_2020_2.action_payslip_verify()
        payslip_for_13th |= self.payslip_2020_2
        self.payslip_2020_4.action_payslip_verify()
        payslip_for_13th |= self.payslip_2020_4
        self.payslip_13th_2020.compute_sheet()
        payslip_lines = self.payslip_13th_2020.line_ids

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
        self.assertEqual(len(advantage_lines), 7, 'Test payslip lines for advantages not ok')
        # Năm 2020 có 1 phiếu lương được xác nhận . tỷ lệ chi trả đầy đủ
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
            },
            {
                'amount': 500000 * 3 / 12,
                'sequence': 570,
                'code': 'HARDWORK'
            },
            {
                'amount': 600000 * 3 / 12,
                'sequence': 580,
                'code': 'PERFORMANCE'
            },
            {
                'amount': 700000 * 3 / 12,
                'sequence': 4100,
                'code': 'HARMFUL'
            }, ])
