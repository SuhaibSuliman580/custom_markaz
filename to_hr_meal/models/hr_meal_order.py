from datetime import timedelta, datetime

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError


class HrMealOrder(models.Model):
    _name = 'hr.meal.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'HR Meal Order'
    _order = 'scheduled_date desc, date_ordered asc, date_approved asc, scheduled_hour desc, id'

    @api.model
    def _get_default_kitchen(self):
        default_kitchen = self.env.ref('to_hr_meal.hr_kitchen_main_kitchen')
        if not default_kitchen:
            default_kitchen = self.env['hr.kitchen'].search([], limit=1)
        if not default_kitchen:
            raise ValidationError(_("No kitchen found! It seems you have deleted the default kitchen. Please create at least one to continue"))
        return default_kitchen

    name = fields.Char(string='Title', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    state = fields.Selection([
                ('draft', 'Draft'),
                ('confirmed', 'Confirmed'),
                ('approved', 'Approved by Kitchen'),
                ('refused', 'Refused by Kitchen'),
                ('cancelled', 'Cancelled')
            ], string='Status', default='draft', tracking=True, required=True, copy=False, index=True)
    notes = fields.Text(string='Notes', copy=False, tracking=True)
    date_ordered = fields.Datetime(string='Order Date', default=fields.Datetime.now,
                                   required=True, readonly=True, copy=False, index=True)
    scheduled_date = fields.Date(string='Scheduled Date', required=True, help="The date scheduled for the meal",
                                 default=fields.Date.today, copy=False, tracking=True, index=True)
    scheduled_hour = fields.Float(string='Scheduled Hour',
                                  help="The time scheduled for the meal",
                                  compute='_compute_scheduled_hour', store=True, readonly=False,
                                 required=True, copy=True, tracking=True, index=True)
    order_line_ids = fields.One2many('hr.meal.order.line', 'meal_order_id', string='Order Lines', copy=True)
    department_id = fields.Many2one('hr.department', string='Department', help="Select a department for auto employees load",
                                    copy=False, domain="[('company_id','=',company_id)]")
    applied_department_ids = fields.Many2many('hr.department', string='Applied Departments',
                                    help="This field helps to show applied departments for a meal order",
                                    compute='_compute_applied_department_ids')
    meal_type_id = fields.Many2one('hr.meal.type', string='Meal Type', tracking=True, required=True, copy=True, index=True)
    kitchen_id = fields.Many2one('hr.kitchen', string='Kitchen to Order', tracking=True,
                                 default=_get_default_kitchen, required=True, copy=True)
    ordered_by = fields.Many2one('res.users', string='Ordered By', help="The user who place the meal order", tracking=True,
                                 required=True, default=lambda self: self.env.user, copy=False, index=True)
    approved_by = fields.Many2one('res.users', string='Approve By', tracking=True, copy=False, readonly=True,
                                  help="The user who approved the meal order. It is usually the kitchen manager.")
    date_approved = fields.Datetime(string='Approved Date', tracking=True, copy=False, readonly=True, index=True)
    order_lines_count = fields.Integer('Number of Lines', compute='_compute_order_lines_count')
    total_qty = fields.Integer('Total Quantity', tracking=True, compute='_compute_total', store=True)
    total_price = fields.Monetary('Total Price', tracking=True, compute='_compute_total', store=True)
    total_employee_pay = fields.Monetary('Employee Total Pay', compute='_compute_total_pay', store=True)
    total_company_pay = fields.Monetary('Company Total Pay', compute='_compute_total_pay', store=True)
    load_employee = fields.Selection([
            ('load_all', 'All Employees'),
            ('clear_all', 'Clear All')
        ], copy=False, string='Mass Load/Clear', store=False,
        help="Utility fields to allow massive load/clear of employees")
    partner_ids = fields.Many2many('res.partner', 'hr_meal_order_partner_rel', 'hr_meal_order_id', 'partner_id',
                                   string='Clients', compute='_compute_partners', store=True)
    partners_count = fields.Integer(string='Clients Count', compute='_compute_partners_count')
    order_source = fields.Selection([
            ('external', 'External'),
            ('internal', 'Internal')
        ], string='Meal Order Source', default='external', required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', index=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Currency')

    _sql_constraints = [
        ('scheduled_hour_check_positive',
         'CHECK(scheduled_hour >= 0)',
         "The Scheduled Hour must be equal to or greater than zero!"),

        ('scheduled_hour_check_less_than_24',
         'CHECK(scheduled_hour < 24)',
         "The Scheduled Hour must be less than than 24!"),
    ]

    @api.depends('meal_type_id')
    def _compute_scheduled_hour(self):
        for r in self:
            r.scheduled_hour = r.meal_type_id.scheduled_hour

    @api.depends('order_line_ids.partner_ids')
    def _compute_partners(self):
        for r in self:
            r.partner_ids = r.mapped('order_line_ids.partner_ids')

    @api.depends('partner_ids')
    def _compute_partners_count(self):
        for r in self:
            r.partners_count = len(r.partner_ids)

    @api.depends('order_line_ids')
    def _compute_order_lines_count(self):
        for order in self:
            order.order_lines_count = len(order.order_line_ids)

    @api.depends('order_line_ids', 'order_line_ids.quantity', 'order_line_ids.total_price')
    def _compute_total(self):
        for r in self:
            r.total_qty = sum(r.order_line_ids.mapped('quantity'))
            r.total_price = sum(r.order_line_ids.mapped('total_price'))

    @api.depends('order_line_ids', 'order_line_ids.employee_amount', 'order_line_ids.company_amount')
    def _compute_total_pay(self):
        for r in self:
            r.total_employee_pay = sum(r.order_line_ids.mapped('employee_amount'))
            r.total_company_pay = sum(r.order_line_ids.mapped('company_amount'))

    def _prepare_meal_order_line(self, employee):
        data = {
            'employee_id': employee._origin.id or employee.id,
            'price': self.meal_type_id.price,
            'quantity': 1,
        }
        return data

    def _prepare_new_lines(self, employees):
        # exclude employees that don't register meal
        employees = employees.filtered('order_meal')

        new_lines = self.env['hr.meal.order.line']
        scheduled_date_dt = datetime.combine(self.scheduled_date, datetime.min.time())
        date_order = scheduled_date_dt + timedelta(hours=self.scheduled_hour)
        date_order_utc = self.env['to.base'].convert_local_to_utc(date_order)
        related_leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', employees.ids),
            ('date_from', '<', date_order_utc),
            ('date_to', '>=', date_order_utc),
            ('state', 'in', ('validate1', 'validate'))])
        for employee in employees:
            if employee in self.order_line_ids.mapped('employee_id') or employee.id in related_leaves.employee_id.ids:
                continue
            data = self._prepare_meal_order_line(employee)
            new_line = new_lines.new(data)
            new_lines += new_line
        return new_lines

    @api.depends('order_line_ids.department_id')
    def _compute_applied_department_ids(self):
        for r in self:
            r.applied_department_ids = r.order_line_ids.department_id

    @api.onchange('department_id', 'scheduled_date', 'scheduled_hour')
    def _onchange_department_id(self):
        if self.department_id:
            if not self.meal_type_id:
                self.department_id = False
                return {'warning': {
                            'title': _("Warning"),
                            'message': _("You must select a meal type first.")
                            }
                        }
            departments_to_calculate = self.department_id | self.department_id.recursive_child_ids
            self.order_line_ids += self._prepare_new_lines(departments_to_calculate.member_ids)
            self.department_id = False
            self.load_employee = False

    @api.onchange('load_employee', 'company_id', 'scheduled_date', 'scheduled_hour')
    def _onchange_load_employee(self):
        if self.load_employee == 'load_all':
            if not self.meal_type_id:
                self.load_employee = False
                return {'warning': {
                            'title': _("Warning"),
                            'message': _("You must select a meal type first.")
                            }
                        }
            self.order_line_ids += self._prepare_new_lines(self.env['hr.employee'].search([('company_id', '=', self.company_id.id)]))

        elif self.load_employee == 'clear_all':
            self.order_line_ids = False

    def action_confirm(self):
        for r in self:
            if r.state != 'draft':
                raise UserError(_("You can only Confirm an order in draft state"))
            if not len(r.order_line_ids):
                raise UserError(_("You cannot confirm an order without any order line"))
        self.write({
            'state': 'confirmed',
            'ordered_by': self.env.user.id,
            'date_ordered': fields.Datetime.now()
        })
        # """
        # Auto approve meal order with current user is
        # kitchen responsible (if choose meal order source is Internal)
        # or vendor (if choose meal order source is External)
        # """
        meal_approve = self._get_order_confirm_kitchen_responsible_or_vendor()
        if meal_approve:
            meal_approve.with_user(SUPERUSER_ID).action_approve()

    def _get_order_confirm_kitchen_responsible_or_vendor(self):
        return self.filtered(lambda r: (r.order_source == 'internal'
                                      and r.kitchen_id.responsible_id
                                      and self.env.user.partner_id.id == r.kitchen_id.responsible_id.id
                                     ) or (r.order_source == 'external'
                                           and r.vendor_id
                                           and self.env.user.partner_id.id == r.vendor_id.id
                                           )
                                     and r.state == 'confirmed')

    def action_approve(self):
        if not self.is_manager():
            raise UserError(_("Only users with Manager Access Right can approve meal orders"))
        for r in self:
            if r.state != 'confirmed':
                raise UserError(_("You can only approve an order that is in confirmed state"))
        self.add_follower()
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'date_approved': fields.Datetime.now()
            })

    def action_refuse(self):
        if not self.is_manager():
            raise UserError(_("Only users with Manager Access Right can refuse meal orders"))
        for r in self:
            if r.state != 'confirmed':
                raise UserError(_("You can only refuse an order that is in confirmed state"))
        self.write({'state': 'refused'})

    def action_cancel(self):
        for r in self:
            if r.state not in ('confirmed', 'approved'):
                raise UserError(_("You can only cancel an order that is in either confirmed or approved state"))
            if r.state == 'approved' and not self.is_manager():
                raise UserError(_("Only users with Manager Access Right can cancel approved meal orders"))
        self.write({'state': 'cancelled'})

    def action_draft(self):
        for r in self:
            if r.state != 'cancelled':
                raise UserError(_("You can only set an order to draft state while it is cancelled."))
        self.write({'state': 'draft'})

    def is_manager(self):
        return self.env.user.has_group('to_hr_meal.hr_meal_group_admin') and True or False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                company_id = vals.get('company_id', self.default_get(['company_id']).get('company_id'))
                # Ensures things are taken from the right company.
                vals['name'] = self.with_company(company_id).env['ir.sequence'].next_by_code('hr.meal.order') or 'New'
        return super(HrMealOrder, self).create(vals_list)

    def add_follower(self):
        for r in self:
            if r.order_source == 'internal' and r.kitchen_id.responsible_id:
                r.message_subscribe(partner_ids=r.kitchen_id.responsible_id.ids)
            elif r.order_source == 'external' and r.vendor_id:
                r.message_subscribe(partner_ids=r.vendor_id.ids)
            else:
                pass

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_state(self):
        for r in self:
            if r.state != 'draft':
                raise UserError(_("You may not be able to delete the meal order '%s' which is not in Draft state. "
                                  "You may need to set it to Draft first") % (r.name))

    def action_view_partners(self):
        partner_ids = self.mapped('partner_ids')
        result = self.env['ir.actions.act_window']._for_xml_id('to_hr_meal.hr_meal_order_action_partners')

        # override the context to get rid of the default filtering
        result['context'] = {}
        result['domain'] = "[('id', 'in', %s)]" % str(partner_ids.ids)
        return result
