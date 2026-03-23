from odoo import models, fields, tools


class RevenueDistributionReport(models.Model):
    _name = 'syndicate.revenue.distribution.report'
    _description = 'Revenue Distribution Report'
    _auto = False
    _rec_name = 'move_name'
    _order = 'date desc, id desc'

    date = fields.Date(readonly=True)
    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    move_name = fields.Char(string='Invoice Number', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', readonly=True)
    fund_box_id = fields.Many2one('syndicate.fund.box', string='Fund Box', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    amount = fields.Float(string='Amount', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    aml.id AS id,
                    am.invoice_date AS date,
                    am.id AS move_id,
                    am.name AS move_name,
                    am.partner_id AS partner_id,
                    aml.product_id AS product_id,
                    pp.product_tmpl_id AS product_tmpl_id,
                    fb.id AS fund_box_id,
                    aml.account_id AS account_id,
                    ABS(aml.balance) AS amount,
                    aml.company_id AS company_id
                FROM account_move_line aml
                JOIN account_move am
                    ON am.id = aml.move_id
                LEFT JOIN product_product pp
                    ON pp.id = aml.product_id
                LEFT JOIN syndicate_fund_box fb
                    ON fb.income_account_id = aml.account_id
                WHERE aml.is_distribution_generated = TRUE
            )
        """)
