{
    "name": "Monta-Module",
    "version": "18.0.1.7.0",
    "summary": "Clean Monta <> Odoo integration: orders, products, suppliers, inbound POs, stock sync, logs.",
    "category": "Sales/Integration",
    "author": "Custom for Ali Raza Jamil3",
    "website": "https://monta.nl",
    "license": "LGPL-3",
    "depends": ["sale_management", "purchase", "stock", "mail", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/product_views.xml",
        "data/ir_cron.xml"
    ],
    "application": False,
    "installable": True
}
