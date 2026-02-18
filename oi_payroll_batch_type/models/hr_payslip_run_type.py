'''
Created on Feb 17, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields

class HrPayslipRunType(models.Model):
    _name = 'hr.payslip.run.type'
    _description = 'Payslip Batches Type'
    
    name = fields.Char(required = True, translate = True)
    code = fields.Char(required = True)