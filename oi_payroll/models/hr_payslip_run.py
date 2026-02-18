'''
Created on Oct 27, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields, api, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _description = 'Payslip Batches'

    name = fields.Char(required=True)
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(string='Date From', required=True, default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True, default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    credit_note = fields.Boolean(string='Credit Note', help="If its checked, indicates that all payslips generated from here are refund payslips.")

    exceptional_line_ids = fields.Many2many('hr.payslip.line', compute = '_calc_exceptional_line_ids')
    
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True, default=lambda self: self.env.company)
    
    
    @api.depends('slip_ids')
    def _compute_payslip_count(self):
        for record in self:
            record.payslip_count = len(record.slip_ids)
    
    @api.depends('slip_ids')
    def _calc_exceptional_line_ids(self):
        for record in self:
            record.exceptional_line_ids = self.env['hr.payslip.line'].search([('slip_id', 'in', record.slip_ids.ids), ('salary_rule_id.exceptional','=', True), ('total', '!=', 0)])
                
    def draft_payslip_run(self):
        return self.write({'state': 'draft'})

    
    def close_payslip_run(self):
        return self.write({'state': 'close'})
    
    
    def action_view_payslips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'name': _('Payslips'),
            'view_mode' : 'tree,form',
            'domain': [['id', 'in', self.slip_ids.ids]],
            'context': {'default_payslip_run_id': self.id},
            
        }    
            
    def action_view_exceptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.line',
            'name': _('Exceptions'),
            'view_mode' : 'tree,form',
            'domain': [['id', 'in', self.exceptional_line_ids.ids]],
        }
