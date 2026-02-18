from datetime import datetime

from odoo import fields, models, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    meals_count = fields.Integer(string='Meals Count', compute='_compute_meals_count')
    meal_order_line_ids = fields.One2many('hr.meal.order.line', 'hr_payslip_id', string='HR Meal Order Line', readonly=True)

    @api.depends('meal_order_line_ids.quantity')
    def _compute_meals_count(self):
        payslips_data = self.env['hr.meal.order.line']._read_group([('hr_payslip_id', 'in', self.ids)], ['quantity'], ['hr_payslip_id'])
        mapped_data = dict([(dict_data['hr_payslip_id'][0], dict_data['quantity']) for dict_data in payslips_data])
        for r in self:
            r.meals_count = mapped_data.get(r.id, 0)

    def compute_sheet(self):
        self._link_hr_meal_order_line()
        return super(HrPayslip, self).compute_sheet()

    def action_payslip_cancel(self):
        for r in self:
            r.meal_order_line_ids = False
        return super(HrPayslip, self).action_payslip_cancel()

    def _link_hr_meal_order_line(self):
        # exclude meals from 13th payslip
        self = self.filtered(lambda r: not r.thirteen_month_pay)
        if not self:
            return
        earliest_date = datetime.combine(min(self.mapped('date_from')), datetime.min.time())
        latest_date = datetime.combine(max(self.mapped('date_to')), datetime.max.time())
        meal_lines = self.env['hr.meal.order.line'].search([('state', 'in', ('confirmed', 'approved')),
                                                                ('employee_id', 'in', self.employee_id.ids),
                                                                ('company_id', 'in', self.company_id.ids),
                                                                ('meal_date', '>=', earliest_date),
                                                                ('meal_date', '<=', latest_date),
                                                                '|', ('hr_payslip_id', '=', False),
                                                                ('hr_payslip_id', 'in', self.ids)])
        for r in self:
            date_from_payslip = datetime.combine(r.date_from, datetime.min.time())
            date_to_payslip = datetime.combine(r.date_to, datetime.max.time())
            meal_order_line_ids = meal_lines.filtered(lambda l: l.employee_id == r.employee_id
                                                            and l.meal_date >= date_from_payslip
                                                            and l.meal_date <= date_to_payslip
                                                            and l.company_id == r.company_id)
            if meal_order_line_ids:
                r.meal_order_line_ids = [(6, 0, meal_order_line_ids.ids)]
            elif r.meal_order_line_ids:
                r.meal_order_line_ids = [(3, line.id) for line in r.meal_order_line_ids]
