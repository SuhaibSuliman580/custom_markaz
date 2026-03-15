/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { useBus } from '@web/core/utils/hooks';
import { Dropdown } from '@web/core/dropdown/dropdown';
import { CommandPalette } from '@web/core/commands/command_palette';

export const VIEW_IMAP = {
    'form': 'ri-news-line',
    'list': 'ri-list-view',
    'pivot': 'ri-timeline-view',
    'kanban': 'ri-kanban-view-2',
    'graph': 'ri-bar-chart-box-line',
    'calendar': 'ri-calendar-event-line',
    'activity': 'ri-calendar-schedule-line',
    'hierarchy': 'ri-organization-chart',
}

patch(CommandPalette.prototype, {

    setup() {
        super.setup();
        this.view_imap = VIEW_IMAP;

        useBus(this.env.bus, 'CMD:REFRESH', ({ detail: text }) => {
            this.debounceSearch(text);
        });
    }
});

CommandPalette.components = {
    ...CommandPalette.components,
    Dropdown: Dropdown,
}
