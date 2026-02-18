from odoo import fields


class BrowsableObjectSum(object):

    def __init__(self, records, env):
        self.records = records
        self.env = env

    def __getattr__(self, attr):
        amount_sum = 0.0
        for record in self.records:
            if hasattr(record, attr):
                amount_sum += getattr(record, attr)
        return amount_sum


class BrowsableObject(object):

    def __init__(self, employee_id, dictionary, env):
        self.employee_id = employee_id
        self.dict = dictionary
        self.env = env

    def __getattr__(self, attr):
        if attr in self.dict:
            return self.dict.__getitem__(attr)
        else:
            return 0.0


class InputLine(BrowsableObject):
    """a class that will be used into the python code, mainly for usability purposes"""

    def sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()
        self.env.cr.execute("""
            SELECT sum(amount) as sum
            FROM hr_payslip as hp, hr_payslip_input as pi
            WHERE hp.employee_id = %s AND hp.state = 'done'
            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
            (self.employee_id, from_date, to_date, code))
        return self.env.cr.fetchone()[0] or 0.0


class Advantages(BrowsableObject):
    """a class that will be used into the python code, mainly for usability purposes"""

    def __getattr__(self, attr):
        if attr in self.dict:
            return BrowsableObjectSum(self.dict.__getitem__(attr), self.env)
        else:
            return 0.0

    def _sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()
        self.env.cr.execute("""
            SELECT sum(adv.amount) as amount
            FROM hr_contract_advantage AS adv
            JOIN hr_contract AS c ON c.id = adv.contract_id
            JOIN hr_payslip AS hp ON hp.contract_id = c.id
            JOIN hr_advantage_template AS adv_tmpl ON adv_tmpl.id = adv.template_id
            WHERE hp.employee_id = %s
                AND hp.date_from >= %s
                AND hp.date_to <= %s
                AND adv_tmpl.code = %s""",
            (self.employee_id, from_date, to_date, code))
        res = self.env.cr.fetchone()
        return res

    def sum(self, code, from_date, to_date=None):
        res = self._sum(code, from_date, to_date)
        return res and res[0] or 0.0


class WorkedDays(BrowsableObject):
    """a class that will be used into the python code, mainly for usability purposes"""

    def __getattr__(self, attr):
        if attr in self.dict:
            return BrowsableObjectSum(self.dict.__getitem__(attr), self.env)
        else:
            return 0.0


class Payslips(BrowsableObject):
    """a class that will be used into the python code, mainly for usability purposes"""

    def sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()
        self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                    FROM hr_payslip as hp, hr_payslip_line as pl
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                    (self.employee_id, from_date, to_date, code))
        res = self.env.cr.fetchone()
        return res and res[0] or 0.0


class PayslipContributionLine(BrowsableObject):
    """a class that will be used into the python code, mainly for usability purposes"""

    def __getattr__(self, attr):
        if attr in self.dict:
            return BrowsableObjectSum(self.dict.__getitem__(attr), self.env)
        else:
            return 0.0

    def _sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = fields.Date.today()
        self.env.cr.execute("""
            SELECT
                sum(contrib.employee_contribution) as employee_contribution,
                sum(contrib.company_contribution) as company_contribution
            FROM hr_payslip_contribution_line AS contrib
            JOIN hr_payslip as hp ON hp.id=contrib.payslip_id
            JOIN hr_payroll_contribution_history AS h ON h.id = contrib.payroll_contrib_history_id

            WHERE hp.employee_id = %s
                AND hp.state = 'done'
                AND hp.date_from >= %s
                AND hp.date_to <= %s
                AND h.state in ('confirmed','resumed')
                AND contrib.code = %s""",
            (self.employee_id, from_date, to_date, code))
        res = self.env.cr.fetchone()
        return res

    def sum_employee(self, code, from_date, to_date=None):
        res = self._sum(code, from_date, to_date)
        return res and res[0] or 0.0

    def sum_company(self, code, from_date, to_date=None):
        res = self._sum(code, from_date, to_date)
        return res and res[1] or 0.0
