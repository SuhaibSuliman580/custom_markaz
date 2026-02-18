'''
Created on Feb 17, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    type_id = fields.Many2one('hr.payslip.run.type', string='Batches Type')