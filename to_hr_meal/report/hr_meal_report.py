from odoo import models, fields
from odoo import tools


class MealOrdersAnalysis(models.Model):
    _name = 'hr.meal.order.analysis'
    _description = 'Meal Orders Analysis'
    _order = 'meal_date desc'
    _auto = False

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    kitchen_id = fields.Many2one('hr.kitchen', string='Kitchen', readonly=True)
    meal_type_id = fields.Many2one('hr.meal.type', string='Meal Type', readonly=True)
    quantity = fields.Integer(string='Ordered Quantity', readonly=True)
    meal_date = fields.Datetime(string='Meal Date', readonly=True)
    ordered_by = fields.Many2one('res.users', string='Ordered By', readonly=True)
    date_ordered = fields.Datetime(string='Order Date', readonly=True)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    date_approved = fields.Datetime(string='Approved Date', readonly=True)
    price = fields.Float(string='Price', readonly=True)
    total_price = fields.Float(string='Total Price', readonly=True)
    order_id = fields.Many2one('hr.meal.order', string='Meal Order', readonly=True)
    state = fields.Selection([
                ('draft', 'Draft'),
                ('confirmed', 'Confirmed'),
                ('approved', 'Approved by Kitchen'),
                ('refused', 'Refused by Kitchen'),
                ('cancelled', 'Cancelled')
            ], string='Status', default='draft', readonly=True)

    def _select(self):
        select_str = """
            SELECT
                l.id AS id,
                l.employee_id,
                l.department_id,
                l.kitchen_id,
                l.meal_date,
                l.meal_type_id,
                l.quantity,
                o.ordered_by,
                o.date_ordered,
                o.approved_by,
                o.date_approved,
                l.price,
                l.total_price,
                o.id AS order_id,
                o.state
        """
        return select_str

    def _from(self):
        from_str = """
            FROM
                hr_meal_order_line AS l
        """
        return from_str

    def _join(self):
        join_str = """
                LEFT JOIN hr_meal_order AS o ON l.meal_order_id = o.id
        """
        return join_str

    def _where(self):
        where_str = """
            WHERE l.state in ('confirmed','approved')
        """
        return where_str

    def _group_by(self):
        group_by_str = """
        """
        return group_by_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            %s
            %s
            %s
            %s
            )
        """ % (self._table, self._select(), self._from(), self._join(), self._where(), self._group_by()))
