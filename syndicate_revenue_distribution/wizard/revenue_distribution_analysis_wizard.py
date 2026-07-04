from odoo import fields, models


class RevenueDistributionAnalysisWizard(models.TransientModel):
    _name = 'revenue.distribution.analysis.wizard'
    _description = 'Revenue Distribution Analysis'

    move_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='move_id.currency_id',
        readonly=True,
    )

    detail_line_ids = fields.One2many(
        'revenue.distribution.analysis.detail.line',
        'wizard_id',
        string='Details',
        readonly=True,
    )

    summary_line_ids = fields.One2many(
        'revenue.distribution.analysis.summary.line',
        'wizard_id',
        string='Summary by Fund Box',
        readonly=True,
    )


class RevenueDistributionAnalysisDetailLine(models.TransientModel):
    _name = 'revenue.distribution.analysis.detail.line'
    _description = 'Revenue Distribution Analysis Detail Line'
    _order = 'id'

    wizard_id = fields.Many2one(
        'revenue.distribution.analysis.wizard',
        required=True,
        ondelete='cascade',
    )

    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    invoice_line_description = fields.Char(string='Invoice Line Description', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    line_subtotal = fields.Monetary(
        string='Line Untaxed Subtotal',
        currency_field='currency_id',
        readonly=True,
    )
    fund_box_id = fields.Many2one('syndicate.fund.box', string='Fund Box', readonly=True)
    percentage = fields.Float(string='Percentage', digits=(16, 4), readonly=True)
    distributed_amount = fields.Monetary(
        string='Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    account_id = fields.Many2one('account.account', string='Income Account', readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
    )


class RevenueDistributionAnalysisSummaryLine(models.TransientModel):
    _name = 'revenue.distribution.analysis.summary.line'
    _description = 'Revenue Distribution Analysis Summary Line'
    _order = 'fund_box_id, id'

    wizard_id = fields.Many2one(
        'revenue.distribution.analysis.wizard',
        required=True,
        ondelete='cascade',
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    fund_box_id = fields.Many2one('syndicate.fund.box', string='Fund Box', readonly=True)
    total_distributed_amount = fields.Monetary(
        string='Total Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    account_id = fields.Many2one('account.account', string='Income Account', readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
    )
