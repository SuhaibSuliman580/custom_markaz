from psycopg2 import IntegrityError

from odoo.tools import mute_logger
from odoo.tests import tagged
from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollSalaryCycle(TestPayrollCommon):

    @mute_logger('odoo.sql_db')
    def test_salary_period(self):
        """
        Case 1: Tạo ban ghi với dữ liệu "Độ lệch ngày bắt đầu" trong khoảng từ 0 đến 27
            TH 1: Độ lệch ngày bắt đầu trong khoảng 0 đến 27
            TH 2: Độ lệch ngày bắt đầu ngoài khoảng 0 đến 27
        """
        SalaryCycle = self.env['hr.salary.cycle']

        # TH 2: Độ lệch ngày bắt đầu ngoài khoảng 0 đến 27
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                SalaryCycle.create(self._prepare_data_salary_cycle('Test 1', -1))
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                SalaryCycle.create(self._prepare_data_salary_cycle('Test 1', 28))

        # TH 1: Độ lệch ngày bắt đầu trong khoảng 0 đến 27
        self.env['hr.salary.cycle'].create(self._prepare_data_salary_cycle('Test 1', 0))
        self.env['hr.salary.cycle'].create(self._prepare_data_salary_cycle('Test 2', 10))
        self.env['hr.salary.cycle'].create(self._prepare_data_salary_cycle('Test 3', 27))

    def _prepare_data_salary_cycle(self, name, day):
        return {
            'name': name,
            'start_day_offset': day
        }
