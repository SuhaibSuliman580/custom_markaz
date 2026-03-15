# -*- coding: utf-8 -*-
# Copyright 2024 Jupetern

import base64

from odoo import api, models


class ScssEditor(models.AbstractModel):
    _inherit = 'web_editor.assets'

    @property
    def DEF_OMLIGHT(self):
        return ''

    @property
    def ULIGHT(self):
        return '/udoo_om_ux/static/src/scss/omux/light.scss'

    @property
    def UDARK(self):
        return '/udoo_om_ux/static/src/scss/omux/dark.scss'

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Light
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_omux_light(self):
        curl = self._omux_asset_url(self.ULIGHT, 'web.assets_web')
        attachment = self.env['ir.attachment'].search([('url', '=', curl)])
        return attachment and base64.b64decode(attachment.datas) or self.DEF_OMLIGHT

    def set_omux_light(self, content):
        curl = self._omux_bundle(content, 'scss', self.ULIGHT, 'web.assets_web')
        self.env.ref('udoo_om_ux.remove_light_in_dark').path = curl

    @api.model
    def reset_omux_light(self):
        self.env.ref('udoo_om_ux.remove_light_in_dark').path = self.ULIGHT
        self._omux_reset(self.ULIGHT, 'web.assets_web')

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Dark
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def get_omux_dark(self):
        curl = self._omux_asset_url(self.UDARK, 'web.assets_web_dark')
        attachment = self.env['ir.attachment'].search([('url', '=', curl)])
        return attachment and base64.b64decode(attachment.datas) or ''

    def set_omux_dark(self, content):
        self._omux_bundle(content, 'scss', self.UDARK, 'web.assets_web_dark')

    @api.model
    def reset_omux_dark(self):
        self._omux_reset(self.UDARK, 'web.assets_web_dark')

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Writer
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _omux_asset_url(self, url, bundle_xmlid):
        return f'/_omux/{bundle_xmlid}{url}'

    def _omux_reset(self, url, bundle):
        curl = self._omux_asset_url(url, bundle)
        self.env['ir.attachment'].search([('url', '=', curl)]).unlink()
        self.env['ir.asset'].search([('path', '=', curl)]).unlink()

    def _omux_bundle(self, content, type, url, bundle, directive='replace'):
        IrAsset = self.env['ir.asset']
        IrAttachment = self.env['ir.attachment']

        custom_url = self._omux_asset_url(url, bundle)
        datas = base64.b64encode((content or '\n').encode('utf-8'))

        # Check if the file to save had already been modified
        custom_attachment = IrAttachment.search([('url', '=', custom_url)])
        if custom_attachment:
            # If it was already modified, simply override the corresponding
            # attachment content
            custom_attachment.write({'datas': datas})
            self.env.registry.clear_cache('assets')
        else:
            # If not, create a new attachment to copy the original scss/js file
            # content, with its modifications
            new_attach = {
                'name': url.split('/')[-1],
                'type': 'binary',
                'mimetype': (type == 'js' and 'text/javascript' or 'text/scss'),
                'datas': datas,
                'url': custom_url,
            }
            IrAttachment.create(new_attach)

        # Create an asset with the new attachment
        target_asset = IrAsset.search([('path', '=', custom_url)])
        if not target_asset:
            new_asset = {
                'path': custom_url,
                'name': '[OMUX] ' + url,
                'bundle': bundle,
                'target': url,
                'directive': directive,
                'sequence': 98,  # NOTE: Keep sequence >= 16 (DEFAULT_SEQUENCE)
            }
            IrAsset.create(new_asset)
        return custom_url
