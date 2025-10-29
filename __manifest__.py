# -*- coding: utf-8 -*-
{
    "name": "Monta-Module",
    "version": "18.0.1.0.0",
    "summary": "Clean Monta <> Odoo integration: orders, products, suppliers, inbound POs, stock sync, logs.",
    "category": "Sales/Integration",
    "author": "Custom for Ali Raza Jamil",
    "website": "https://monta.nl",
    "license": "LGPL-3",
    "depends": ["sale_management", "purchase", "stock", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/product_views.xml",
        "data/ir_cron.xml"
    ],
    "assets": {},  # keep minimal
    "application": False,
    "installable": True
}
