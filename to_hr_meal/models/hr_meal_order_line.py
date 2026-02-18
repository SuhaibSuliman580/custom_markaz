from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HrMealOrderLine(models.Model):
    _name = 'hr.meal.order.line'
    _description = 'HR Meal Order Line'

    meal_order_id = fields.Many2one('hr.meal.order', string='Meal Order Ref.',
                                    required=True, readonly=False,
                                    ondelete='cascade', index=True)
    company_id = fields.Many2one(related='meal_order_id.company_id', store=True)
    currency_id = fields.Many2one(related='meal_order_id.currency_id')
    meal_type_id = fields.Many2one(related='meal_order_id.meal_type_id', store=True, precompute=True)
    kitchen_id = fields.Many2one(related='meal_order_id.kitchen_id', store=True)
    state = fields.Selection(related='meal_order_id.state', store=True)

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=False,
                                    compute='_compute_department', store=True, precompute=True)
    partner_ids = fields.Many2many('res.partner', 'hr_meal_order_line_partner_rel', 'hr_meal_order_line_id', 'partner_id',
                                   string='Clients', help="The clients who enjoy the meal with this employee")
    quantity = fields.Integer(string='Quantity', required=True, readonly=False,
                              compute='_compute_quantity', store=True, precompute=True)
    price = fields.Monetary(string='Price', required=True, readonly=False,
                            compute='_compute_price', store=True, precompute=True)
    employee_price = fields.Monetary(string='Employee Price',
                                     compute='_compute_employee_price', store=True, precompute=True)
    total_price = fields.Monetary(string='Amount',
                                  compute='_compute_total_price', store=True, precompute=True)
    employee_amount = fields.Monetary(string='Employee Amount',
                                      compute='_compute_amount', store=True, precompute=True)
    company_amount = fields.Monetary(string='Company Amount',
                                     compute='_compute_amount', store=True, precompute=True)

    description = fields.Text(string='Description')
    meal_date = fields.Datetime(string='Meal Date', index=True,
                                compute='_compute_meal_date', store=True, precompute=True)

    @api.depends('price', 'quantity')
    def _compute_total_price(self):
        for r in self:
            r.total_price = r.price * r.quantity

    @api.depends('meal_type_id')
    def _compute_price(self):
        for r in self:
            if r.meal_type_id:
                r.price = r.meal_type_id.price
            else:
                r.price = 0.0

    @api.depends('employee_id', 'meal_order_id.company_id', 'meal_date', 'price')
    def _compute_employee_price(self):
        for r in self:
            r.employee_price = r._get_employee_price()

    def _get_employee_price(self):
        """
        TO override
        """
        self.ensure_one()
        if self.company_id.set_meal_employee_price:
            return min(self.price, self.company_id.meal_emp_price)
        else:
            return self.price

    @api.depends('employee_price', 'quantity', 'total_price')
    def _compute_amount(self):
        for r in self:
            employee_amount = r.employee_price * r.quantity
            if r.total_price < employee_amount:
                employee_amount = r.total_price
            r.employee_amount = employee_amount
            r.company_amount = r.total_price - employee_amount

    @api.depends('meal_order_id.scheduled_date', 'meal_order_id.scheduled_hour')
    def _compute_meal_date(self):
        for r in self:
            if r.meal_order_id.scheduled_date and 0 <= r.meal_order_id.scheduled_hour < 24:
                time = self.env['to.base'].float_hours_to_time(r.meal_order_id.scheduled_hour)
                meal_date = datetime.combine(r.meal_order_id.scheduled_date, time)
                r.meal_date = self.env['to.base'].convert_local_to_utc(
                    meal_date,
                    force_local_tz_name=self.env.user.tz if self.env.user.tz else 'UTC',
                    naive=True
                )
            else:
                r.meal_date = r.meal_order_id.scheduled_date or fields.Date.today()

    @api.constrains('employee_id', 'meal_date', 'state')
    def constrains_employee_id_and_meal_date(self):
        hr_meal_order_lines = self.search([('state', 'in', ('confirmed', 'approved'))])
        for r in self:
            if r.state == 'draft':
                continue
            overlap = hr_meal_order_lines.filtered(
                lambda l: l.id != r.id
                and l.employee_id == r.employee_id
                and l.meal_date == r.meal_date
            )
            if overlap:
                raise ValidationError(_("You cannot register more than one meal for the same employee '%s' at the same time."
                                        " '%s' was registered by the order %s.")
                                      % (r.employee_id.name, r.employee_id.name, overlap[:1].meal_order_id.name))

    @api.depends('employee_id')
    def _compute_department(self):
        for r in self:
            r.department_id = r.employee_id and r.employee_id.department_id or False

    @api.depends('partner_ids')
    def _compute_quantity(self):
        for r in self:
            r.quantity = len(r.partner_ids) + 1

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_state(self):
        for r in self:
            if r.state != 'draft':
                raise UserError(_("You may not be able to delete the meal order line which is not in Draft state. "
                                  "You may need to set it to Draft the meal order first"))
