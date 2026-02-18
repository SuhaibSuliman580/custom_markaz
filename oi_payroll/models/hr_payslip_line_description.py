'''
Created on May 5, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class HrPayslipLineDescription(models.Model):
    _name = 'hr.payslip.line.description'
    _description = _name
    
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    code = fields.Char(required=True)
    description = fields.Char()