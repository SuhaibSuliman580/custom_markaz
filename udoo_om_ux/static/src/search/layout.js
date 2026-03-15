/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { localization } from '@web/core/l10n/localization';
import { useHotkey } from '@web/core/hotkeys/hotkey_hook';
import { useBus, useService } from '@web/core/utils/hooks';
import { throttleForAnimation } from '@web/core/utils/timing';
import { useState, useExternalListener } from '@odoo/owl';
import { Layout } from '@web/search/layout';

const VAR_ASIDE = '--Chatter-min-width';


patch(Layout.prototype, {
    setup() {
        super.setup();

        this.ui = useService('ui');
        this.yy = useState({
            sashMarkPoint: 0,
            noaside: false,
        });

        useHotkey('control+shift+arrowright', () => {
            this.onSassAsideFold(), {
                bypassEditableProtection: true,
                global: true,
            }
        });

        useBus(this.env.bus, 'LYT:TCTT', () => {
            this.onSassAsideFold();
        });

        this.adjustStatusField = throttleForAnimation(this.adjustStatusField.bind(this));
        this.onSassAsideChange = throttleForAnimation(this.onSassAsideChange.bind(this));

        useExternalListener(window, 'mousemove', this.onSassAsideChange);
        useExternalListener(window, 'mouseup', this.onSassAsideEnd);
    },

    onSassAsideFold() {
        this.yy.noaside = !this.yy.noaside;
        if (this.yy.noaside) {
            this.env.bus.trigger('TREE:OMCL');
        }
        setTimeout(() => {
            document.body.classList.toggle('noaside');
        }, 120);
    },

    onSassAsideStart(ev) {
        this.yy.sashMarkPoint = ev.x;
    },

    onSassAsideEnd() {
        this.yy.sashMarkPoint = 0;
    },

    onSassAsideChange(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        if (this.yy.sashMarkPoint) {
            const fv = localization.direction === 'rtl' ? ev.view.innerWidth - (ev.view.innerWidth - ev.x) : ev.view.innerWidth - ev.x;
            document.documentElement.style.setProperty(VAR_ASIDE, `${fv}px`);
            this.env.bus.trigger('TREE:OMCL');
            this.adjustStatusField();
        }
    },

    adjustStatusField() {
        this.env.bus.trigger('SBAR:ADJVIS');
    }
});