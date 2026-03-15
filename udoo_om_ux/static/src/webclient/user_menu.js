/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';

import { AppearanceConfig } from './configs/appearance';

const userMenuRegistry = registry.category('user_menuitems');

function appearanceItem(env) {
    return {
        type: 'item',
        id: 'appearance',
        description: _t('Appearance'),
        callback: () => {
            env.services.dialog.add(AppearanceConfig, {

            });
        },
        sequence: 41,
    };
}

function separator42() {
    return {
        type: 'separator',
        sequence: 42,
    };
}

userMenuRegistry
    .add('appearance', appearanceItem)
    .add('separator42', separator42)