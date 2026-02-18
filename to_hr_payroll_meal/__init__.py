from . import models


def post_init_hook(env):
    companies = env['res.company'].search([])
    companies._generate_meal_order_salary_rules()
