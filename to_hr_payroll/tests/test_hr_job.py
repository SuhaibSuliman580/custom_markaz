from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestHrJob(TestPayrollCommon):

    def test_01_job_action_update_contract_advantages(self):
        """
        Test: hành động "Apply to contracts" bên dưới mục "Monthly Advantages"
        Input:
            - Hợp đồng chưa có phúc lợi hàng tháng
            - Đi vào Chức vụ, thiết lập mẫu phúc lợi hàng tháng, và bấm vào "Apply to contracts"
        Output:
            - "Phúc lợi hàng tháng" của tất cả hợp đồng liên quan đến Chức vụ trên sẽ được thay đổi giống với Chức vụ.
        """
        # Set job advantages on the Job
        advantages = self.env['hr.advantage.template'].search([('company_id', '=', self.env.company.id)])
        job_product_dev = self.job_product_dev
        job_product_dev.write({
            'advantage_ids': [
                (0, 0, {'template_id': advantages[0].id, 'amount': 100000}),
                (0, 0, {'template_id': advantages[1].id, 'amount': 200000})
                ]
        })

        # Set job on contracts
        contract_ids = self.product_emp_A.contract_ids
        contract_ids.write({'job_id': job_product_dev.id})

        # update
        job_product_dev.update_contract_advantages()

        # test
        job_advantages = job_product_dev.advantage_ids
        for contract in contract_ids:
            contract_advantages = contract.advantage_ids
            self.assertEqual(len(job_advantages), len(contract_advantages), 'Test method: update_contract_advantages not ok')

            for job_advantage in job_advantages:
                contract_advantage = contract_advantages.filtered(lambda r: r.template_id == job_advantage.template_id)
                self.assertRecordValues(
                    job_advantage, [{
                        'template_id': contract_advantage.template_id.id,
                        'amount': contract_advantage.amount
                    }])

    def test_02_job_action_update_contract_advantages(self):
        """
        Test: Hành động "Apply to contracts" bên dưới mục "Monthly Advantages"
        Input:
            -  Hợp đồng nhân viên đã có phúc lợi hàng tháng
            - Đi vào Chức vụ, thiết lập mẫu phúc lợi hàng tháng, và bấm vào "Apply to contracts"
        Output:
            - "Phúc lợi hàng tháng" của tất cả hợp đồng liên quan đến Chức vụ trên sẽ được thay đổi giống với Chức vụ
        """
        # Set job advantages on the Job
        advantages = self.env['hr.advantage.template'].search([('company_id', '=', self.env.company.id)])
        job_product_dev = self.job_product_dev
        job_product_dev.write({
            'advantage_ids': [(0, 0, {'template_id': advantages[0].id, 'amount': 100000}),
                              (0, 0, {'template_id': advantages[1].id, 'amount': 200000})]
        })

        # Set job on contracts
        contract_ids = self.product_emp_A.contract_ids
        contract_ids.write({'job_id': job_product_dev.id})
        contract_ids.write({
            'advantage_ids': [
                (6, 0, 0),
                (0, 0, {'template_id': advantages[3].id, 'amount': 5500}),
                (0, 0, {'template_id': advantages[1].id, 'amount': 5500})
            ]
        })

        # update
        job_product_dev.update_contract_advantages()

        # test
        job_advantages = job_product_dev.advantage_ids
        for contract in contract_ids:
            contract_advantages = contract.advantage_ids
            self.assertEqual(len(job_advantages), len(contract_advantages),
                             'Test method: update_contract_advantages not ok')

            for job_advantage in job_advantages:
                contract_advantage = contract_advantages.filtered(lambda r: r.template_id == job_advantage.template_id)
                self.assertRecordValues(
                    job_advantage, [{
                        'template_id': contract_advantage.template_id.id,
                        'amount': contract_advantage.amount
                    }])
