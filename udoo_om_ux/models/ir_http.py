# -*- coding: utf-8 -*-
# Copyright 2024 Jupetern

from odoo import models, _


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @property
    def _omux_title(self):
        return ''

    @property
    def _omux_shade(self):
        return 'Gainsboro'

    @property
    def _omux_a(self):
        return {
            '#05869c': _('Primary'),
            '#28979b': _('Action'),
        }

    @property
    def _omux_b(self):
        return {
            '#f8f9fa': _('Gray 100'),
            '#e9ecef': _('Gray 200'),
            '#dee2e6': _('Gray 300'),
            '#ced4da': _('Gray 400'),
            '#adb5bd': _('Gray 500'),
            '#6c757d': _('Gray 600'),
            '#495057': _('Gray 700'),
            '#343a40': _('Gray 800'),
            '#212529': _('Gray 900'),
        }

    @property
    def _omux_preset(self):
        return {
            'code': '',
            'title': self._omux_title + self._omux_shade,
            'subtitle': _('Seriousness and freshness, creating a refined, modern space'),
            'creator': 'Udoo',
            'scheme': self._omux_a | self._omux_b,
        }

    def session_info(self):
        result = super(IrHttp, self).session_info()

        if result.get('is_internal_user', False):
            result['udoo_presets'] = result.get('udoo_presets', [])
            result['udoo_presets'].extend(
                [
                    self._omux_preset,
                    {'code': '', 'title': _('Default'), 'color': '#05869C'},
                    {'code': 'magenta', 'title': _('Magenta'), 'color': '#714B67'},
                    {'code': 'rose', 'title': _('Rose'), 'color': '#b25968'},
                    {'code': 'lime', 'title': _('Lime'), 'color': '#66954f'},
                    {'code': 'green', 'title': _('Green'), 'color': '#19876a'},
                    {'code': 'emerald', 'title': _('Emerald'), 'color': '#0E837C'},
                    {'code': 'dodger', 'title': _('Dodger'), 'color': '#2383af'},
                    {'code': 'sky', 'title': _('Sky'), 'color': '#1e93c9'},
                    {'code': 'indigo', 'title': _('Indigo'), 'color': '#665f99'},
                    {'code': 'pink', 'title': _('Pink'), 'color': '#b16080'},
                    {'code': 'orange', 'title': _('Orange'), 'color': '#ae6464'},
                    {'code': 'yellow', 'title': _('Yellow'), 'color': '#a98357'},
                ]
            )
        return result
