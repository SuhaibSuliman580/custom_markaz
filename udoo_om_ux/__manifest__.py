# -*- coding: utf-8 -*-
# Copyright 2024 Jupetern

{
    'name': 'Omux Community Backend',
    'category': 'Themes/Backend',
    'summary': 'Refined Odoo UX with start menu, dual-tier sidebar navigation, bookmark manager, recent views, split list view, quick pop-up view, global search, dark mode, prebuilt color palette, open in new tab, switch language, RTL support, flexible chatter, sticky header, web sheet full width, group fold unfold, fullscreen form view, report action icon, optimized multi-line, interactive sortable, stunning graph view, kanban view, responsive mobile, dynamic layout, sign up login design, history activities, language selection, support RTL, dual page, multipurpose, required input, asterisk for required, arrange app menu item, right click menu, row number in list, row index, Arabic, Spanish, Vietnamese, multilingual, enterprise color theme, enterprise theme, Right-To-Left, WCAG22, RTLCSS',
    'version': '2.1.6',
    'license': 'OPL-1',
    'author': 'Sveltware Solutions',
    'website': 'https://www.linkedin.com/in/sveltware',
    'live_test_url': 'mailto:jupetern24@gmail.com?subject=Demo request for Omux Community',
    'support': 'jupetern24@gmail.com',
    'sequence': 777,
    'images': [
        'static/description/banner.png',
        'static/description/theme_screenshot.png',
    ],
    'depends': [
        'base_sparse_field',
        'auth_signup',
        'web_editor',
    ],
    'excludes': [
        'web_enterprise',
    ],
    'data': [
        'data/asset_data.xml',
        'views/webclient_templates.xml',
        'views/res_company_views.xml',
        'views/ir_ui_menu.xml',
    ],
    'assets': {
        'web._assets_primary_variables': {
            (
                'prepend',
                'udoo_om_ux/static/src/scss/style_variables.scss',
            ),
            (
                'before',
                'web/static/src/scss/primary_variables.scss',
                'udoo_om_ux/static/src/scss/primary_variables.scss',
            ),
            (
                'before',
                'web/static/src/**/*.variables.scss',
                'udoo_om_ux/static/src/**/*.variables.scss',
            ),
        },
        'web._assets_secondary_variables': [
            (
                'before',
                'web/static/src/scss/secondary_variables.scss',
                'udoo_om_ux/static/src/scss/secondary_variables.scss',
            ),
        ],
        'web._assets_backend_helpers': [
            (
                'before',
                'web/static/src/scss/bootstrap_overridden.scss',
                'udoo_om_ux/static/src/scss/bs_backend_overridden.scss',
            ),
        ],
        'web.assets_backend': [
            (
                'replace',
                'web/static/src/webclient/navbar/navbar.scss',
                'udoo_om_ux/static/src/webclient/navbar/navbar.scss',
            ),
            (
                'after',
                'web/static/src/scss/fontawesome_overridden.scss',
                'udoo_om_ux/static/src/scss/overridden_icons.scss',
            ),
            (
                'before',
                'mail/static/src/views/fields/**/*',
                'udoo_om_ux/static/src/patch/form_compiler.js',
            ),
            (
                'before',
                'mail/static/src/views/fields/**/*',
                'udoo_om_ux/static/src/patch/form_renderer.js',
            ),
            (
                'before',
                'web/static/src/webclient/**/*',
                'udoo_om_ux/static/src/views/**/*',
            ),
            (
                'before',
                'web/static/src/webclient/**/*',
                'udoo_om_ux/static/src/search/**/*',
            ),
            'udoo_om_ux/static/src/webclient/**/*',
            'udoo_om_ux/static/src/patch/chatter.xml',
            'udoo_om_ux/static/src/patch/chatter.js',
            (
                'remove',
                'udoo_om_ux/static/src/**/*.dark.scss',
            ),  # Don't include dark theme
            (
                'after',
                'udoo_om_ux/static/src/webclient/**/*',
                'udoo_om_ux/static/src/scss/style_backend.scss',
            ),
        ],
        'web.assets_web': [
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/omux/light.scss',
            ),
        ],
        'web.dark_mode_variables': [
            (
                'before',
                'udoo_om_ux/static/src/scss/primary_variables.scss',
                'udoo_om_ux/static/src/scss/primary_variables_dark.scss',
            ),
            (
                'before',
                'udoo_om_ux/static/src/**/*.variables.scss',
                'udoo_om_ux/static/src/**/*.variables.dark.scss',
            ),
            (
                'before',
                'udoo_om_ux/static/src/scss/secondary_variables.scss',
                'udoo_om_ux/static/src/scss/secondary_variables_dark.scss',
            ),
        ],
        'web.assets_web_dark': [
            ('include', 'web.dark_mode_variables'),
            (
                'before',
                'udoo_om_ux/static/src/scss/bs_backend_overridden.scss',
                'udoo_om_ux/static/src/scss/bs_backend_overridden_dark.scss',
            ),
            (
                'after',
                'web/static/lib/bootstrap/scss/_functions.scss',
                'udoo_om_ux/static/src/scss/bs_functions_overridden_dark.scss',
            ),
            'udoo_om_ux/static/src/**/*.dark.scss',
        ],
        'web.assets_frontend': [
            (
                'before',
                'web/static/lib/bootstrap/scss/_variables.scss',
                'udoo_om_ux/static/src/scss/bs_frontend_variables.scss',
            ),
            (
                'after',
                'web/static/src/scss/fontawesome_overridden.scss',
                'udoo_om_ux/static/src/scss/overridden_icons.scss',
            ),
            (
                'replace',
                'web/static/src/webclient/navbar/navbar.scss',
                'udoo_om_ux/static/src/webclient/navbar/navbar.scss',
            ),
            'udoo_om_ux/static/src/scss/style_login_page.scss',
        ],
        'web._assets_core': [
            'udoo_om_ux/static/src/core/**/*',
            'udoo_om_ux/static/lib/object_hash.js',
            (
                'replace',
                'web/static/src/core/colors/colors.js',
                'udoo_om_ux/static/src/patch/colors.js',
            ),
            (
                'after',
                'web/static/src/session.js',
                'udoo_om_ux/static/src/omux.js',
            ),
            (
                'after',
                'web/static/src/core/utils/ui.js',
                'udoo_om_ux/static/src/patch/_ui.js',
            ),
        ],
        # COLOR
        'web.assets_web_magenta': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/magenta.scss',
            ),
        ],
        'web.assets_web_magenta_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/magenta_dark.scss',
            ),
        ],
        'web.assets_web_dodger': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/dodger.scss',
            ),
        ],
        'web.assets_web_dodger_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/dodger_dark.scss',
            ),
        ],
        'web.assets_web_lime': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/lime.scss',
            ),
        ],
        'web.assets_web_lime_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/lime_dark.scss',
            ),
        ],
        'web.assets_web_green': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/green.scss',
            ),
        ],
        'web.assets_web_green_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/green_dark.scss',
            ),
        ],
        'web.assets_web_emerald': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/emerald.scss',
            ),
        ],
        'web.assets_web_emerald_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/emerald_dark.scss',
            ),
        ],
        'web.assets_web_sky': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/sky.scss',
            ),
        ],
        'web.assets_web_sky_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/sky_dark.scss',
            ),
        ],
        'web.assets_web_rose': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/rose.scss',
            ),
        ],
        'web.assets_web_rose_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/rose_dark.scss',
            ),
        ],
        'web.assets_web_yellow': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/yellow.scss',
            ),
        ],
        'web.assets_web_yellow_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/yellow_dark.scss',
            ),
        ],
        'web.assets_web_orange': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/orange.scss',
            ),
        ],
        'web.assets_web_orange_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/orange_dark.scss',
            ),
        ],
        'web.assets_web_pink': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/pink.scss',
            ),
        ],
        'web.assets_web_pink_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/pink_dark.scss',
            ),
        ],
        'web.assets_web_indigo': [
            ('include', 'web.assets_web'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/indigo.scss',
            ),
        ],
        'web.assets_web_indigo_dark': [
            ('include', 'web.assets_web_dark'),
            (
                'after',
                'udoo_om_ux/static/src/scss/style_variables.scss',
                'udoo_om_ux/static/src/scss/pallets/indigo_dark.scss',
            ),
        ],
    },
    'price': 140,
    'currency': 'USD',
}
