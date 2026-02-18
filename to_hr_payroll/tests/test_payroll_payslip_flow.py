from odoo import fields
from odoo.exceptions import UserError

from .common import TestPayrollCommon, ADVANTAGE_CODE_LIST


class TestPayrollPayslipFlow(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollPayslipFlow, cls).setUpClass()

        # Set advantages, registers on the contract
        types = cls.env['hr.payroll.contribution.type'].search([('company_id', '=', cls.env.company.id)])
        advantages = cls.env['hr.advantage.template'].search([('company_id', '=', cls.env.company.id)])
        cls.contract_open_emp_A.write({
            'wage': 25000000,
            'advantage_ids': [(0, 0, {'template_id': advantages[0].id, 'amount': 100000}),  # TRAVEL - 530
                              (0, 0, {'template_id': advantages[1].id, 'amount': 200000}),  # PHONE - 540
                              (0, 0, {'template_id': advantages[2].id, 'amount': 300000}),  # MEAL - 550
                              (0, 0, {'template_id': advantages[3].id, 'amount': 400000}),  # RESPONSIBILITY - 560
                              (0, 0, {'template_id': advantages[4].id, 'amount': 500000}),  # HARDWORK - 570
                              (0, 0, {'template_id': advantages[5].id, 'amount': 600000}),  # PERFORMANCE - 580
                              (0, 0, {'template_id': advantages[6].id, 'amount': 700000})],  # HARMFUL - 4100
            'payroll_contribution_type_ids': types
        })
        cls.contract_open_emp_A.generate_payroll_contribution_registers()
        registers = cls.contract_open_emp_A.payroll_contribution_register_ids
        register_social_insurance = registers.filtered(lambda r: r.type_id.code == 'SOCIAL_INSURANCE')
        register_health_insurance = registers.filtered(lambda r: r.type_id.code == 'HEALTH_INSURANCE')
        register_unemployment_unsurance = registers.filtered(lambda r: r.type_id.code == 'UNEMPLOYMENT_UNSURANCE')
        register_labor_union = registers.filtered(lambda r: r.type_id.code == 'LABOR_UNION')
        register_social_insurance.write({
            'contribution_base': 25000000,
            'employee_contrib_rate': 2,  # đóng góp đầy đủ là 500.000 (ESINS)
            'company_contrib_rate': 3  # đóng góp đầy đủ là 750.000 (CSINS)
            })
        register_health_insurance.write({
            'contribution_base': 25000000,
            'employee_contrib_rate': 1.5,  # đóng góp đầy đủ là 375.000 (EHINS)
            'company_contrib_rate': 3  # đóng góp đầy đủ là 750.000 (CHINS)
            })
        register_unemployment_unsurance.write({
            'contribution_base': 25000000,
            'employee_contrib_rate': 1,  # đóng góp đầy đủ là 250.000 (EUEINS)
            'company_contrib_rate': 2  # đóng góp đầy đủ là 500.000 (CUEINS)
            })
        register_labor_union.write({
            'contribution_base': 25000000,
            'employee_contrib_rate': 1.5,  # đóng góp đầy đủ là 375.000 (ELUF)
            'company_contrib_rate': 2.5  # đóng góp đầy đủ là 625.000 (CLUF)
            })
        cls.contract_open_emp_A.payroll_contribution_register_ids.action_confirm()

        # payslip: draft
        cls.payslip_t7 = cls.create_payslip(
            cls.product_emp_A.id,
            fields.Date.to_date('2021-7-1'),
            fields.Date.to_date('2021-7-31'),
            )

    def test_flow_draft_pasylip_unlink(self):
        """
        2.1 Phiếu lương ở trạng thái Dự thảo
            Case 5: Xóa Phiếu lương ở trạng thái "Dự thảo"
                Output: Xóa phiếu lương thành công
        """
        self.assertTrue(self.payslip_t7.unlink(), 'Test unlink Payslip not ok')

    def test_flow_draft_pasylip_send_email(self):
        """
        2.1 Phiếu lương ở trạng thái Dự thảo
            Case 4: Test nút Gửi email
                Output: Wizard xuất hiện để soạn email.
        """
        result = self.payslip_t7.action_payslip_send_wizard()
        self.assertEqual(result.get('res_model', ''), 'mail.compose.message', 'Test wizard: send email not ok')

    def test_flow_draft_pasylip_action_cancel(self):
        """
        2.1 Phiếu lương ở trạng thái Dự thảo
            Test nút hủy phiếu lương
        """
        self.payslip_t7.action_payslip_cancel()
        self.assertEqual(self.payslip_t7.state, 'cancel', 'Test action_payslip_done not ok')

    def test_flow_draft_pasylip_compute_sheet(self):
        """
        2.2 Phiếu lương ở trạng thái Dự thảo
            Case 3: Test nút tính toán lương
                Ouput:
                    Tab: Tính toán lương:
                         các các dòng phiếu lương theo cấu trúc lương
                    Tab: Chi tiết theo nhóm quy tắc lương:
                        Nhóm các dòng bên Tính toán Lương theo nhóm quy tắc lương.
                    Tab: Chi tiết Thuế TNCN
                        Tính toán các thông tin:
                        Lương tổng: Dựa vào cấu trúc lương
                        cơ sở tính thuế TNCN = Lương tổng - giảm trừ bản thân
                        Nếu cơ sở tính thuế TNCN > 0
                        Bảng tính thuế sẽ được tính toán theo quy tắc thuế
                    Tab: Thông tin kế toán:
                        Chi phí công ty = tổng các dòng phiếu lương mà có nhóm quy tắc lương được đánh dấu là chi trả bởi công ty
        """
        self.payslip_t7.compute_sheet()
        payslip_lines = self.payslip_t7.line_ids

        # BASIC: 25.000.000 (tỷ lệ chi trả =1)
        # ALW : phụ cấp chịu thuế 100k +200k +300k +400k +500k +600k = 2.100.000
        # GROSS = BASIC + ALW = 25.000.000 + 2.100.000 = 27.100.000
        # ALWNOTAX : phụ cấp không chịu thuế 700.000
        # DED_BEFORE_TAX: khấu trừ trước thuế: -(500k +375k + 250k) = -1.125.000
        # DED_AFTER_TAX: khấu trừ sau thuế: 375.000
        # TBDED = giảm trừ bản thân + khấu trừ phụ thuộc - DED_BEFORE_TAX
        #        = 11.000.000 + 0 + 1.125.000 = 12.125.000
        # TAXBASE = GROSS - TBDED = 27.100.000 - 12.125.000 = 14.975.000
        # PTAX: 3 dòng thuế:
        #    dòng thuế 5% của 5.000.000 = 250.000
        #    dòng thuế 10% của 5.000.000 = 500.000
        #    dòng thuế 15% của 4.975.000 = 746.250
        #    => Tổng thuế: -1.496.250
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #    = 27.100.000 + 700.000 - 1.125.000 - 375.000 - 1.496.250 = 24.803.750

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = payslip_lines.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 25000000,
            },
            {
                'code': 'GROSS',
                'amount': 27100000,
            },
            {
                'code': 'NET',
                'amount': 24803750,
            }])

        # Test personal_tax_base field
        self.assertEqual(self.payslip_t7.personal_tax_base, 14975000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = payslip_lines.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 12125000,
            },
            {
                'code': 'TAXBASE',
                'amount': 14975000,
            },
            {
                'code': 'PTAX',
                'amount': -1496250,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = self.payslip_t7.payslip_personal_income_tax_ids
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 14975000,
                'base': 4975000,
                'rate': 15,
                'tax_amount': 746250
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

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
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

        # check contribution on payslip lines
        line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(line.total, -500000, 'Test ESINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(line.total, 750000, 'Test CSINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(line.total, -375000, 'Test EHINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(line.total, 750000, 'Test CHINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(line.total, -250000, 'Test EUEINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(line.total, 500000, 'Test CUEINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(line.total, -375000, 'Test ELUF payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(line.total, 625000, 'Test CLUF payslip line not ok')

        cost_lines = self.payslip_t7.line_ids.filtered(lambda line: line.salary_rule_id.category_id.paid_by_company)
        company_cost = sum(cost_lines.mapped('total'))
        self.assertEqual(company_cost, self.payslip_t7.company_cost, 'Test company cost not ok')

    def test_flow_draft_pasylip_action_verify(self):
        """
        2.1 Phiếu lương ở trạng thái Dự thảo
            Case 2: Test nút xác nhận phiếu lương
                => Tính toán lương
        """
        self.payslip_t7.action_payslip_verify()
        payslip_lines = self.payslip_t7.line_ids

        # BASIC: 25.000.000 (tỷ lệ chi trả =1)
        # ALW : phụ cấp chịu thuế 100k +200k +300k +400k +500k +600k = 2.100.000
        # GROSS = BASIC + ALW = 25.000.000 + 2.100.000 = 27.100.000
        # ALWNOTAX : phụ cấp không chịu thuế 700.000
        # DED_BEFORE_TAX: khấu trừ trước thuế: -(500k +375k + 250k) = -1.125.000
        # DED_AFTER_TAX: khấu trừ sau thuế: 375.000
        # TBDED = giảm trừ bản thân + khấu trừ phụ thuộc - DED_BEFORE_TAX
        #        = 11.000.000 + 0 + 1.125.000 = 12.125.000
        # TAXBASE = GROSS - TBDED = 27.100.000 - 12.125.000 = 14.975.000
        # PTAX: 3 dòng thuế:
        #     dòng thuế 5% của 5.000.000 = 250.000
        #     dòng thuế 10% của 5.000.000 = 500.000
        #     dòng thuế 15% của 4.975.000 = 746.250
        #      => Tổng thuế: -1.496.250
        # NET = GROSS + ALWNOTAX + DED_BEFORE_TAX + DED_AFTER_TAX + PTAX    (categories)
        #    = 27.100.000 + 700.000 - 1.125.000 - 375.000 - 1.496.250 = 24.803.750

        # Check salary lines ('BASIC', 'GROSS', 'NET')
        salary_lines = self.payslip_t7.line_ids.filtered(lambda r: r.code in ['BASIC', 'GROSS', 'NET'])
        self.assertRecordValues(salary_lines, [
            {
                'code': 'BASIC',
                'amount': 25000000,
            },
            {
                'code': 'GROSS',
                'amount': 27100000,
            },
            {
                'code': 'NET',
                'amount': 24803750,
            }])

        # Test personal_tax_base field
        self.assertEqual(self.payslip_t7.personal_tax_base, 14975000, 'Test Personal Income Tax Base field not ok')

        # Test tax on payslip lines
        ps_lines_tax = self.payslip_t7.line_ids.filtered(lambda r: r.code in ['TBDED', 'TAXBASE', 'PTAX'])
        self.assertRecordValues(ps_lines_tax, [
            {
                'code': 'TBDED',
                'amount': 12125000,
            },
            {
                'code': 'TAXBASE',
                'amount': 14975000,
            },
            {
                'code': 'PTAX',
                'amount': -1496250,
            },
        ])

        # Test payslip_personal_income_tax_ids field
        income_taxs = self.payslip_t7.payslip_personal_income_tax_ids
        self.assertRecordValues(income_taxs, [
            {
                'upper_base': 14975000,
                'base': 4975000,
                'rate': 15,
                'tax_amount': 746250
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

        # Check Advantages on payslip lines
        advantage_lines = payslip_lines.filtered(lambda r: r.code in ADVANTAGE_CODE_LIST)
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

        # check contribution on payslip line
        line = payslip_lines.filtered(lambda r: r.code == 'ESINS')
        self.assertEqual(line.total, -500000, 'Test ESINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'CSINS')
        self.assertEqual(line.total, 750000, 'Test CSINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'EHINS')
        self.assertEqual(line.total, -375000, 'Test EHINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'CHINS')
        self.assertEqual(line.total, 750000, 'Test CHINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'EUEINS')
        self.assertEqual(line.total, -250000, 'Test EUEINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'CUEINS')
        self.assertEqual(line.total, 500000, 'Test CUEINS payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'ELUF')
        self.assertEqual(line.total, -375000, 'Test ELUF payslip line not ok')
        line = payslip_lines.filtered(lambda r: r.code == 'CLUF')
        self.assertEqual(line.total, 625000, 'Test CLUF payslip line not ok')

        cost_lines = self.payslip_t7.line_ids.filtered(lambda line: line.salary_rule_id.category_id.paid_by_company)
        company_cost = sum(cost_lines.mapped('total'))
        self.assertEqual(self.payslip_t7.company_cost, company_cost, 'Test company cost not ok')

        self.assertEqual(self.payslip_t7.state, 'verify', 'Test action_payslip_verify not ok')

    def test_flow_draft_pasylip_action_draft_done(self):
        """
        2.1 Phiếu lương ở trạng thái Dự thảo
            Test nút đánh dấu hoàn thành, dự thảo
        """
        self.assertRaises(UserError, self.payslip_t7.action_payslip_done)
        self.assertRaises(UserError, self.payslip_t7.action_payslip_draft)

    def test_flow_verify_pasylip_unlink(self):
        """
        2.2 Phiếu lương ở trạng thái "Đang đợi"
            Case 5: Xóa Phiếu lương ở trạng thái "Dự thảo"
        """
        self.payslip_t7.action_payslip_verify()
        self.assertRaises(UserError, self.payslip_t7.unlink)

    def test_flow_verify_pasylip_action_done(self):
        """
        2.2 Phiếu lương ở trạng thái "Đang đợi"
            Case 4: Test nút Đánh dấu là hoàn thành
        """
        self.payslip_t7.action_payslip_verify()
        self.payslip_t7.action_payslip_done()
        self.assertEqual(self.payslip_t7.state, 'done', 'Test action_payslip_done not ok')

    def test_flow_verify_pasylip_action_cancel(self):
        """
        2.2 Phiếu lương ở trạng thái "Đang đợi"
            Case 3: Test nút hủy phiếu lương
        """
        self.payslip_t7.action_payslip_verify()
        self.payslip_t7.action_payslip_cancel()
        self.assertEqual(self.payslip_t7.state, 'cancel', 'Test action_payslip_cancel not ok')

    def check_refund_payslip(self, payslip):
        refund_payslip = payslip.refund_ids
        self.assertRecordValues(refund_payslip, [{
            'refund_for_payslip_id': payslip.id,
            'state': 'verify',
            'credit_note': True,
            'date_from': payslip.date_from,
            'date_to': payslip.date_to,
            'basic_wage': payslip.basic_wage,
            'gross_salary': payslip.gross_salary,
            'company_cost': payslip.company_cost,
            # ...
        }])
        lines = payslip.line_ids
        refund_lines = refund_payslip.line_ids
        self.assertEqual(len(lines), len(refund_lines), 'Test refund payslip not ok')
        for line, refund_line in zip(lines, refund_lines):
            self.assertRecordValues(refund_line, [{
                'code': line.code,
                'total': line.total
                # ...
            }])

    def test_flow_verify_pasylip_refund_sheet(self):
        self.payslip_t7.action_payslip_verify()
        self.payslip_t7.refund_sheet()
        self.check_refund_payslip(self.payslip_t7)

    def test_flow_verify_pasylip_action_draft(self):
        """
        2.2 Phiếu lương ở trạng thái "Đang đợi"
            Test nút đặt về dự thảo
        """
        self.payslip_t7.action_payslip_verify()
        self.assertRaises(UserError, self.payslip_t7.action_payslip_draft)

    def test_flow_done_pasylip_unlink(self):
        """
        2.3 Phiếu lương ở trạng thái "Hoàn thành"
            Case 4: Test xóa phiếu lương: không thành công
        """
        self.payslip_t7.action_payslip_verify()
        self.payslip_t7.action_payslip_done()
        self.assertRaises(UserError, self.payslip_t7.unlink)

    def test_flow_done_pasylip_refund_sheet(self):
        """
        2.3 Phiếu lương ở trạng thái "Hoàn thành"
            Case 2: Test xóa phiếu lương: không thành công
        """
        self.payslip_t7.action_payslip_verify()
        self.payslip_t7.action_payslip_done()
        self.payslip_t7.refund_sheet()
        self.check_refund_payslip(self.payslip_t7)

    def test_flow_done_pasylip_action_cancel(self):
        """
        2.3 Phiếu lương ở trạng thái "Hoàn thành"
            Case 3: Test nút hủy phiếu lương
        """
        self.payslip_t7.action_payslip_verify()
        self.payslip_t7.action_payslip_done()
        self.payslip_t7.action_payslip_cancel()
        self.assertEqual(self.payslip_t7.state, 'cancel', 'Test action_payslip_cancel not ok')

    def test_flow_cancel_pasylip_unlink(self):
        """
        2.4 Phiếu lương ở trạng thái "Bị từ chối"
            Case 3: Test nút hủy phiếu lương
        """
        self.payslip_t7.action_payslip_verify()
        self.payslip_t7.action_payslip_cancel()
        self.assertTrue(self.payslip_t7.unlink(), 'Test unlink payslip not ok')

    def test_flow_cancel_pasylip_action_draft(self):
        """
        2.4 Phiếu lương ở trạng thái "Bị từ chối"
            Case 3: Test nút hủy phiếu lương
        """
        self.payslip_t7.action_payslip_verify()
        self.payslip_t7.action_payslip_cancel()
        self.payslip_t7.action_payslip_draft()
        self.assertEqual(self.payslip_t7.state, 'draft', 'Test action_payslip_draft not ok')

    def test_flow_cancel_pasylip_action_done_verify(self):
        """
        2.4 Phiếu lương ở trạng thái "Bị từ chối"
            Case 3: Test nút hủy phiếu lương
        """
        self.payslip_t7.action_payslip_verify()
        self.payslip_t7.action_payslip_cancel()
        self.assertRaises(UserError, self.payslip_t7.action_payslip_done)
        self.assertRaises(UserError, self.payslip_t7.action_payslip_verify)
