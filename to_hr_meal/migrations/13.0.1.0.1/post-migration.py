from odoo import api, SUPERUSER_ID


def auto_approved_meal_order(env):
    """
    Finds a record that has `state` is 'confirm' and falls under one of the following two conditions:
    - have Meal Order Source (`order_source`) is Internal
        and the order creator is responsible for the kitchen in the Kitchen to Order section.
    - have Meal Order Source (`order_source`) is External
        and Vendor (`vendor_id`) is the order creator.
    """
    meal_order_ids = env['hr.meal.order'].search(['&', ('state', '=', 'confirmed'),
                                                  '|', '&',
                                                    ('order_source', '=', 'internal'),
                                                    ('kitchen_id.responsible_id', '!=', False),
                                                  '&',
                                                    ('order_source', '=', 'external'),
                                                    ('vendor_id', '!=', False),
                                                  ])
    meal_order_ids = meal_order_ids.filtered(lambda r: (r.order_source == 'internal'
                                                        and r.kitchen_id.responsible_id == r.ordered_by.partner_id)
                                                        or (r.order_source == 'external'
                                                            and r.vendor_id == r.ordered_by.partner_id))

    """ Approve orders found with `approved_by` is confirmation person"""
    if meal_order_ids:
        for meal_order in meal_order_ids:
            meal_order.write({
                'state': 'approved',
                'approved_by': meal_order.ordered_by.id,
                'date_approved': meal_order.write_date
                })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    auto_approved_meal_order(env)
