{
    "name": "Doctor Website Directory (Active Membership)",
    "version": "17.0.1.6.0",
    "category": "Website",
    "summary": "Public directory for doctors with ACTIVE membership (from membership_management).",
    "depends": ["website", "contacts", "membership_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/member_directory_templates.xml",
        "views/website_menu.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "membership_website_directory/static/src/css/member_directory.css"
        ]
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3"
}
