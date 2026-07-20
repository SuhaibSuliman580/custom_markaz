from odoo import fields, models


class RevenueDistributionAnalysisWizard(models.TransientModel):
    _name = 'revenue.distribution.analysis.wizard'
    _description = 'تحليل توزيع الإيرادات'

    move_id = fields.Many2one(
        'account.move',
        string='الفاتورة',
        required=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='move_id.currency_id',
        readonly=True,
    )

    detail_line_ids = fields.One2many(
        'revenue.distribution.analysis.detail.line',
        'wizard_id',
        string='التفاصيل',
        readonly=True,
    )

    summary_line_ids = fields.One2many(
        'revenue.distribution.analysis.summary.line',
        'wizard_id',
        string='ملخص حسب الصندوق',
        readonly=True,
    )


class RevenueDistributionAnalysisDetailLine(models.TransientModel):
    _name = 'revenue.distribution.analysis.detail.line'
    _description = 'سطر تفاصيل تحليل توزيع الإيرادات'
    _order = 'id'

    wizard_id = fields.Many2one(
        'revenue.distribution.analysis.wizard',
        required=True,
        ondelete='cascade',
    )

    move_id = fields.Many2one('account.move', string='الفاتورة', readonly=True)
    partner_id = fields.Many2one('res.partner', string='الشريك', readonly=True)
    product_id = fields.Many2one('product.product', string='المنتج', readonly=True)
    invoice_line_description = fields.Char(string='وصف سطر الفاتورة', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    line_subtotal = fields.Monetary(
        string='إجمالي السطر قبل الضريبة',
        currency_field='currency_id',
        readonly=True,
    )
    fund_box_id = fields.Many2one('syndicate.fund.box', string='الصندوق', readonly=True)
    percentage = fields.Float(string='النسبة', digits=(16, 4), readonly=True)
    distributed_amount = fields.Monetary(
        string='المبلغ الموزع',
        currency_field='currency_id',
        readonly=True,
    )
    account_id = fields.Many2one('account.account', string='حساب الإيراد', readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='الحساب التحليلي',
        readonly=True,
    )


class RevenueDistributionAnalysisSummaryLine(models.TransientModel):
    _name = 'revenue.distribution.analysis.summary.line'
    _description = 'سطر ملخص تحليل توزيع الإيرادات'
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
    fund_box_id = fields.Many2one('syndicate.fund.box', string='العملة', readonly=True)
    total_distributed_amount = fields.Monetary(
        string='إجمالي المبلغ الموزع',
        currency_field='currency_id',
        readonly=True,
    )
    account_id = fields.Many2one('account.account', string='حساب الإيراد', readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='الحساب التحليلي',
        readonly=True,
    )
