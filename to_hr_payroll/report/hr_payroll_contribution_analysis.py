from odoo import models, fields, tools


class PayrollContributionAnalysis(models.Model):
    """
    TODO: Analyze and improve this report or delete it.
    This report currently has no effect other than statistics on the number of payroll contribution histories monthly.
    But in some cases, the calculation is still not correct if the payroll contribution history does not have a date end.
    """
    _name = 'hr.payroll.contribution.analysis'
    _description = "Payroll Contribution Analysis"
    _order = 'date_from desc'
    _auto = False

    date_to = fields.Date(string='Date To')
    date_from = fields.Date(string='Date From')
    payroll_contribution_reg_id = fields.Many2one('hr.payroll.contribution.register', string='Payroll Contribution Register')
    payroll_contribution_type_id = fields.Many2one('hr.payroll.contribution.type', string='Payroll Contribution Register Type')
    employee_contrib_reg_id = fields.Many2one('hr.contribution.register', string='Employee Contribution')
    company_contrib_reg_id = fields.Many2one('hr.contribution.register', string='Company Contribution')
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    state = fields.Selection([
        ('confirmed', "Confirmed"),
        ('suspended', "Suspended"),
        ('resumed', "Resumed"),
        ('done', "Closed")
    ])

    def _select(self):
        return """
        SELECT
            l.id AS id,
            l.employee_id,
            l.date_from,
            l.date_to,
            l.state,
            pcr.id AS payroll_contribution_reg_id,
            pct.id AS payroll_contribution_type_id,
            empcr.id AS employee_contrib_reg_id,
            comcr.id AS company_contrib_reg_id
        """

    def _from(self):
        return """
        FROM
            (SELECT id, employee_id
                 , CASE WHEN date_from::date = d THEN date_from ELSE d END AS date_from
                 , CASE WHEN date_to::date = d THEN date_to ELSE d + 1 END AS date_to
            FROM   hr_payroll_contribution_history t
                 , LATERAL (SELECT d::date
                            FROM   generate_series(t.date_from::date, t.date_to::date, interval '1d') d
                            ) d
            ORDER  BY id, date_from) AS temp
        """

    def _join(self):
        return """
            JOIN hr_payroll_contribution_history AS l ON l.id = temp.id
            LEFT JOIN hr_payroll_contribution_register AS pcr ON pcr.id = l.payroll_contribution_reg_id
            LEFT JOIN hr_payroll_contribution_type AS pct ON pct.id = pcr.type_id
            LEFT JOIN hr_contribution_register AS empcr ON empcr.id = pct.employee_contrib_reg_id
            LEFT JOIN hr_contribution_register AS comcr ON comcr.id = pct.company_contrib_reg_id
            LEFT JOIN hr_contribution_category AS empcrcat ON empcrcat.id = empcr.category_id
            LEFT JOIN hr_contribution_category AS comcrcat ON comcrcat.id = comcr.category_id
        """

    def _where(self):
        return """
        WHERE
            l.id > 0
        """

    def _group_by(self):
        return """
        GROUP BY l.id, pcr.id, pct.id, empcr.id, comcr.id, empcrcat.id, comcrcat.id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s AS (
        %s
        %s
        %s
        %s
        %s)
        """ % (self._table, self._select(), self._from(), self._join(), self._where(), self._group_by()))
