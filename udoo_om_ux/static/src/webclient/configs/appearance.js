/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { cookie } from '@web/core/browser/cookie';
import { browser } from '@web/core/browser/browser';
import { utils } from '@web/core/ui/ui_service';
import { session } from '@web/session';
import { useService } from '@web/core/utils/hooks';
import { Dialog } from '@web/core/dialog/dialog';
import { CheckBox } from '@web/core/checkbox/checkbox';
import { Component, useState } from '@odoo/owl';

import { useUdooStore, useUdooLocalStore } from '../webclient';

export class AppearanceConfig extends Component {
    static template = 'udoo_om_ux.AppearanceConfig';
    static components = { Dialog, CheckBox };
    static props = {
        close: { type: Function },
    };

    setup() {
        this.ui = useService('ui');
        this.uo = useUdooStore();
        this.ue = useUdooLocalStore();
        this.user = useService('user');

        this.uiSizes = { VSM: 1, SM: 2, MD: 3, LG: 4, XL: 5, XXL: 6, Auto: 0 };
        this.uiTooltip = {
            VSM: _t('Underline input fields; Set default form list view to Kanban; Position Chatter at bottom; Hide Document Viewer by default'),
            SM: _t('Set default form list view to Kanban; Position Chatter at bottom; Hide Document Viewer by default'),
            MD: _t('Position Chatter at bottom; Hide Document Viewer by default'),
            LG: _t('Position Chatter at bottom; Hide Document Viewer by default'),
            XL: _t('Position Chatter at bottom; Document Viewer on right if present'),
            XXL: _t('Position Chatter and Document Viewer on right')
        };
        this.uiUtils = utils;

        this.scheme_data = session.udoo_presets || [];

        this.o_color_shade = cookie.get('color_shade');
        this.o_color_scheme = this.ui.color_scheme || 'light';
        this.state = useState({
            color_shade: this.o_color_shade,
            color_scheme: this.o_color_scheme,
        });
    }

    async confirm() {
        if (this.state.color_shade !== this.o_color_shade) {
            cookie.set('color_shade', this.state.color_shade);
            this.ui.block();
        } else {
            await this.user.setUserSettings('ps_auto_hmenu', this.uo.ps_auto_hmenu);
        }

        if (this.ui.isBlocked) {
            browser.location.reload();
        } else {
            this.props.close();
        }
    }

    onUoOptionChanged(key, val) {
        this.uo[key] = val;
    }

    onUiSize(size) {
        if (odoo.sett_uisize !== size) {
            if (size === 0) {
                delete odoo.sett_uisize;
                this.ui.size = utils.getSize();
            } else {
                odoo.sett_uisize = size;
                this.ui.size = size;

                document.body.classList.add('uup');
            }

            // Local saver
            this.ue.sett_uisize = size;
        }
    }
}
