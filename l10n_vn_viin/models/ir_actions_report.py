from odoo import fields, models, api


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    legal_name = fields.Char(string='Legal Name', translate=True, help="The legal name of the report. For instance,"
                             " 'Template S12-DN' is the legal name of the stock card according the Ministry of Finanace of Vietnam")

    def report_action(self, docids, data=None, config=True):
        if data:
            data['legal_name'] = self.legal_name
        res = super(IrActionsReport, self).report_action(docids=docids, data=data, config=config)
        res.update({
            'legal_name': self.legal_name
            })
        return res

    @api.model
    def _get_rendering_context(self, report, docids, data):
        res = super(IrActionsReport, self)._get_rendering_context(report, docids, data)
        res.update({
            'legal_name': report.legal_name or '',
            })
        return res
