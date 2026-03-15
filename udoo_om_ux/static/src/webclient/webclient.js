/** @odoo-module **/

import { loadLanguages, _t } from '@web/core/l10n/translation';
import { session } from '@web/session';
import { patch } from '@web/core/utils/patch';
import { useHotkey } from '@web/core/hotkeys/hotkey_hook';
import { useService, useBus } from '@web/core/utils/hooks';
import { useCommand } from '@web/core/commands/command_hook';
import { isMacOS } from '@web/core/browser/feature_detection';
import { registry } from '@web/core/registry';
import { WebClient } from '@web/webclient/webclient';
import { ResizablePanel } from '@web/core/resizable_panel/resizable_panel';
import { reactive, useState, onWillStart, onMounted, useExternalListener } from '@odoo/owl';

import { CommandPalette } from './trays/quick_search';
import { bookmarkPalette, actionBookmarkThis, openBookmarkPalette } from './bookmark';
import { BookmarkManager } from './trays/bookmark';

const trayMenu = registry.category('systray');

export const LCID = () => {
    return `udoo_${session.db}_${session.username}`;
}

// Memorized store
const jsonStore = (obj, key) => {
    localStorage.setItem(key, JSON.stringify(obj));
};
const lstore = reactive({}, () => jsonStore(lstore, LCID()));
export function useUdooLocalStore(initialst = {}) {
    Object.assign(lstore, JSON.parse(localStorage.getItem(LCID())) || initialst);
    jsonStore(lstore, LCID());
    return useState(lstore);
}

// Global store (non-memorized)
export const ustore = reactive({ recents: [] });
export function useUdooStore() {
    return useState(ustore);
}


patch(WebClient.prototype, {
    setup() {
        super.setup();

        this.ui = useService('ui');
        this.user = useService('user');
        this.hotkey = useService('hotkey');
        this.action = useService('action');

        this.uo = useUdooStore();
        this.ue = useUdooLocalStore({
            sidenav: !this.env.isSmall,
            sidenavWidth: odoo.omux.sidenav.def_width,
        });

        this.currentCompany = useService('company').currentCompany;

        /* Set web page title by config */
        if (odoo.omux.web.title_prefix) {
            this.title.setParts({ zopenerp: odoo.omux.web.title_prefix });
        }

        /* Bookmark manager command */
        useCommand(
            _t('Bookmark current tab'),
            () => { actionBookmarkThis(this.env); },
            {
                category: 'smart_action',
                global: true,
                isAvailable: () => this.env.services.action.currentController,
            }
        );
        useCommand(
            _t('Bookmark manager'),
            () => (bookmarkPalette),
            {
                category: 'smart_action',
                global: true,
            }
        );
        useHotkey('alt+k', () => openBookmarkPalette(this.env), {
            bypassEditableProtection: true,
            global: true,
        });

        /* Bookmark manager system tray */
        trayMenu.add('bookmark', { Component: BookmarkManager, isDisplayed: (env) => !env.isSmall }, { sequence: 50 });

        /* Quick action system tray */
        trayMenu.add('quick_search', { Component: CommandPalette }, { sequence: 50 });

        /* Side nav state */
        useHotkey('control+shift+arrowleft', () => {
            this.onSassLsideFold(), {
                bypassEditableProtection: true,
                global: true,
            }
        });

        /* Holding key handling */
        useBus(this.env.bus, 'ACTION_MANAGER:UI-UPDATED', (mode) => {
            // Clear key holding state
            this.ui.ctrlKey = false;
            this.ui.shiftKey = false;
        });

        onWillStart(async () => {
            this.uo.ps_auto_hmenu = this.user.settings?.ps_auto_hmenu;
            this.ui.bookmarks = this.parseBookmarks();
            const languages = await loadLanguages(this.orm);
            this.ui.languages = languages;

            // Restore ui size from local
            if (this.ue.sett_uisize && this.ue.sett_uisize !== 0) {
                odoo.sett_uisize = this.ue.sett_uisize;
                this.ui.size = this.ue.sett_uisize;
                document.body.classList.add('uup');
            }
        });

        onMounted(() => {
            this._loadSidenavState();

            // Load recents from local
            if (this.ue.recents?.length) {
                this.uo.recents = this.ue.recents;
            }
        });

        useExternalListener(window, 'beforeunload', () => {
            /* Recents post process */
            const lastRecent = this.ue.recents || [];
            const mergeArray = lastRecent.concat(this.uo.recents);
            mergeArray.forEach(el => {
                el.act_uid = el.act_uid || objectHash.MD5(el);
            });
            const uniqueArray = [];
            for (let index = mergeArray.length - 1; index >= 0; index--) {
                const el = mergeArray[index];
                if (uniqueArray.findIndex(o => o.act_uid === el.act_uid) == -1) {
                    uniqueArray.push(el);
                }
            }
            // Save to local context
            this.ue.recents = uniqueArray.reverse();

            /* Bookmark post process */
            if (this.ui.bookmarks.length == 0) {
                return;
            }
            const bookmarks = [];
            for (let index = this.ui.bookmarks.length - 1; index >= 0; index--) {
                const el = this.ui.bookmarks[index];
                if (el.pinned || bookmarks.findIndex(o => o.act_uid === el.act_uid) === -1) {
                    bookmarks.push(el);
                }
            }
            this.user.setUserSettings('up_bookmarks', JSON.stringify(bookmarks.reverse()));
        });
    },

    onGlobalClick(ev) {
        // Save ctrl holding state
        this.env.services.ui.ctrlKey = ev.ctrlKey || (isMacOS() && ev.metaKey);
        this.env.services.ui.shiftKey = ev.shiftKey;

        super.onGlobalClick(ev);
    },

    _loadSidenavState() {
        if (this.ue.sidenav) {
            document.body.classList.remove('nolside');
        } else {
            document.body.classList.add('nolside');
        }
    },

    async _loadDefaultApp() {
        // Get company menu preset for initial user
        const favconf = this.user.settings?.ps_fav_menus;
        if (!favconf || favconf == '[]') {
            this.uo.apps_preset = await this.orm.silent.call('res.company', 'get_menus_preset', [[this.currentCompany.id]]);
            if (this.uo.apps_preset) {
                const newfav = [];
                this.uo.orderedApps.forEach(app => {
                    if (this.uo.apps_preset.includes(app.id)) {
                        newfav.push(app.xmlid);
                    }
                });
                this.uo.fav_menus = newfav;
                await this.env.services.user.setUserSettings('ps_fav_menus', JSON.stringify(newfav));
            }
        }
        // Start action logic
        const root = this.menuService.getMenu('root');
        for (const app of root.childrenTree) {
            if (app.xmlid === this.user.settings?.ps_start_xmlid) {
                return this.menuService.selectMenu(app);
            }
        }
        return super._loadDefaultApp();
    },

    _onSideNavResize(width) {
        if (width > odoo.omux.sidenav.max_width)
            return;
        const sidenav = document.querySelector('.o_sidenav');
        if (!sidenav)
            return;

        if (width < 142) {
            sidenav.classList.add('sm');
        } else {
            sidenav.classList.remove('sm');
        }

        this.ue.sidenavWidth = width;
        document.documentElement.style.setProperty('--uw-sidenav', `${width}px`);

        // Refresh column width when has list view
        this.env.bus.trigger('TREE:OMCL');
    },

    toggleFootnav() {
        this.ue.footnav = !this.ue.footnav;
    },

    parseBookmarks() {
        return JSON.parse(this.user.settings?.up_bookmarks || '[]');
    },

    onSassLsideFold() {
        this.ue.sidenav = !this.ue.sidenav && !this.env.isSmall;
        this._loadSidenavState();

        // Refresh column width when has list view
        this.env.bus.trigger('TREE:OMCL');
    },

    openOmSearch() {
        this.env.services.command.openMainPalette({
            searchValue: '/',
            bypassEditableProtection: true,
            global: true,
        });
    }
});

WebClient.components = { ...WebClient.components, ResizablePanel }
