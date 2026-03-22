
from odoo import models, fields, tools

class RevenueDistributionReport(models.Model):
    _name = 'syndicate.revenue.distribution.report'
    _description = 'Revenue Distribution Report'
    _auto = False

    date = fields.Date()
    move_name = fields.Char()
    product_id = fields.Many2one('product.product')
    account_id = fields.Many2one('account.account')
    amount = fields.Float()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    aml.id as id,
                    am.invoice_date as date,
                    am.name as move_name,
                    aml.product_id as product_id,
                    aml.account_id as account_id,
                    aml.balance as amount
                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                WHERE aml.is_distribution_generated = TRUE
            )
        """ % self._table)
