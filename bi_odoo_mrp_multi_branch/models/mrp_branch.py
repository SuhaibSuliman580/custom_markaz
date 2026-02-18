# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model
    def default_get(self, flds):
        result = super(MrpBom, self).default_get(flds)
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id
        result['branch_id'] = branch_id
        return result

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            user_branch = user_id.sudo().branch_id
            if user_branch and user_branch.id != selected_brach.id:
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model
    def default_get(self, flds):
        result = super(MrpBomLine, self).default_get(flds)
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id
        result['branch_id'] = branch_id
        return result

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            user_branch = user_id.sudo().branch_id
            if user_branch and user_branch.id != selected_brach.id:
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    branch_id = fields.Many2one('res.branch', string='Branch')
    product_id = fields.Many2one(
        'product.product', 'Product')

    @api.model
    def default_get(self, flds):
        result = super(MrpProduction, self).default_get(flds)
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id
        result['branch_id'] = branch_id
        return result

    # @api.onchange('product_id', 'picking_type_id', 'company_id')
    @api.onchange('picking_type_id', 'company_id')
    def onchange_product_id(self):
        """ Finds UoM of changed product. """
        if not self.product_id:
            self.bom_id = False
        else:
            bom = self.env['mrp.bom']._bom_find(
                self.product_id, picking_type=self.picking_type_id, company_id=self.company_id.id, bom_type='normal')[self.product_id]
            if bom:
                self.bom_id = bom.id
                self.branch_id = bom.branch_id.id
            else:
                self.bom_id = False
            self.product_uom_id = self.product_id.uom_id.id
            return {'domain': {'product_uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}}

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            user_branch = user_id.sudo().branch_id
            if user_branch and user_branch.id != selected_brach.id:
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")


class StockMove(models.Model):
    _inherit = 'stock.move'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model_create_multi
    def create(self, vals):

        res = super(StockMove, self).create(vals)
        for line in res:
            user_obj = self.env['res.users']
            branch_id = user_obj.browse(line.env.user.id).branch_id.id
            if line.raw_material_production_id.bom_id.branch_id:
                branch_id = line.raw_material_production_id.bom_id.branch_id.id
            line.branch_id = branch_id

        return res

    @api.model
    def default_get(self, flds):
        result = super(StockMove, self).default_get(flds)
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id

        if self.raw_material_production_id.bom_id.branch_id:
            branch_id = self.raw_material_production_id.bom_id.branch_id.id
        result['branch_id'] = branch_id
        return result

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            user_branch = user_id.sudo().branch_id
            if user_branch and user_branch.id != selected_brach.id:
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    branch_id = fields.Many2one(
        'res.branch', string='Branch', related="production_id.branch_id")

    @api.model
    def default_get(self, flds):
        result = super(MrpWorkorder, self).default_get(flds)
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id
        result['branch_id'] = branch_id
        return result


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    branch_id = fields.Many2one('res.branch', string='Branch')

    @api.model
    def default_get(self, flds):
        result = super(StockMoveLine, self).default_get(flds)
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id
        result['branch_id'] = branch_id
        return result
