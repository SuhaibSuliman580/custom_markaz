from . import models
from . import controllers

def post_init_hook(env):
    from odoo.tools import config
    if not env["ir.config_parameter"].get_param("report.url"):
        http_port = config.get("http_port")
        env["ir.config_parameter"].set_param("report.url", f"http://localhost:{http_port}")