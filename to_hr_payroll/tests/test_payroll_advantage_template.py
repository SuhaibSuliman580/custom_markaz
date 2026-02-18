from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollAdvantageTemplate(TestPayrollCommon):

    def test_01_advantage_template_limit_1(self):
        """
        Test: Giới hạn thấp, giới hạn trên thay đổi theo số tiền trên mẫu phụ cấp
            TH1: Số tiền < giới hạn thấp
                Output: Giới hạn dưới = số tiền
            TH2: Giới hạn thấp <= Số tiền <= giới hạn trên
                Output: Giới hạn dưới và giới hạn trên không thay đổi
            TH3: Giới hạn trên < Số tiền
                Output: Giới hạn trên = số tiền
        """
        advantage_template = self.env['hr.advantage.template'].search([('company_id', '=', self.env.company.id)], limit=1)
        advantage_template.write({'lower_bound': 0, 'upper_bound': 100})

        # TH1
        advantage_template.write({'amount': -10})
        self.assertEqual(-10, advantage_template.lower_bound, 'Test compute: _compute_bounds not ok')

        # TH2
        advantage_template.write({'amount': 55})
        self.assertEqual(-10, advantage_template.lower_bound, 'Test compute: _compute_bounds not ok')
        self.assertEqual(100, advantage_template.upper_bound, 'Test compute: _compute_bounds not ok')

        # TH3
        advantage_template.write({'amount': 150})
        self.assertEqual(150, advantage_template.upper_bound, 'Test compute: _compute_bounds not ok')

    def test_01_advantage_template_limit_2(self):
        """
        Test: Số tiền phải nằm trong khoảng giới hạn trên và giới hạn dưới
            TH1: Số tiền nhỏ hơn giới hạn dưới
                Output: Không thành công
            TH2: Số tiền lớn hơn giới hạn trên
                Output: Không thành công
            TH3: Số tiền nằm trong khoảng giới hạn trên và dưới
                Output: Thành công
        """
        advantage_template = self.env['hr.advantage.template'].search([('company_id', '=', self.env.company.id)], limit=1)
        advantage_template.write({'amount': 0, 'lower_bound': 0, 'upper_bound': 100})

        # TH1: Số tiền nhỏ hơn giới hạn dưới
        self.assertRaises(UserError, advantage_template.write, {'amount': -20, 'lower_bound': 0, 'upper_bound': 100})

        # TH2: Số tiền lớn hơn giới hạn trên
        self.assertRaises(UserError, advantage_template.write, {'amount': 150, 'lower_bound': 0, 'upper_bound': 100})

        # TH3: Số tiền nằm trong khoảng giới hạn trên và dưới
        advantage_template.write({'amount': 50})
        self.assertEqual(50, advantage_template.amount, 'Test constraint not ok')

    def test_02_advantage_template(self):
        """
        Test hành động "Tạo chế độ đãi ngộ cho các chức danh" trên công cụ Hành động
        Input: Nhấn chọn hành động "Tạo chế độ đãi ngộ cho các chức danh"
        Output:
            Tất cả các chức vụ sẽ có mẫu chế độ đãi ngộ này,
                và cập nhật số tiền cho các Phúc lợi hàng tháng trên chức vụ theo mẫu này
        """
        advantage_template = self.env['hr.advantage.template'].create({
            'name': 'Test 1',
            'code': 'Test1',
            'amount': 1000,
            'lower_bound': 0,
            'upper_bound': 1000
        })
        advantage_template._generate_job_position_advantages()
        jobs = self.env['hr.job'].search([('company_id', '=', self.env.company.id)])
        job_ids = advantage_template.job_advantage_ids.job_id

        code = set(advantage_template.job_advantage_ids.mapped('code'))
        amount = set(advantage_template.job_advantage_ids.mapped('amount'))

        self.assertEqual(jobs.ids, job_ids.ids, 'Test method: _generate_job_position_advantages not ok')
        self.assertEqual(code, {advantage_template.code}, 'Test method: _generate_job_position_advantages not ok')
        self.assertEqual(amount, {advantage_template.amount}, 'Test method: _generate_job_position_advantages not ok')

    def test_03_advantage_template_2(self):
        """
        Test hành động "Cập nhật đãi ngộ của vị trí công việc" trên công cụ hành động
        Input: Nhấn chọn hành động "Cập nhật đãi ngộ của vị trí công việc"
        Output: Tất cả các Phúc lợi hàng tháng liên quan đến mẫu đãi ngộ này sẽ được cập nhật số tiền giống với mẫu
        """
        advantage_template = self.env['hr.advantage.template'].search([('company_id', '=', self.env.company.id)], limit=1)
        advantage_template._generate_job_position_advantages()
        advantage_template.write({'amount': 66})

        advantage_template._update_job_position_advantages()
        amount = set(advantage_template.job_advantage_ids.mapped('amount'))
        self.assertEqual(amount, {66}, 'Test method: _update_job_position_advantages not ok')
