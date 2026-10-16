{
    'name': 'Seriani Tours & Travel',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Sell and manage Kenya tour packages online',
    'description': """
Seriani Tours & Travel
======================
Browse and book Kenya tour packages (safaris, beach getaways, treks) on the
website, manage packages/departure dates/pricing/bookings from the backend,
and let customers track bookings and leave reviews from the customer portal.
""",
    'depends': ['website_sale', 'rating'],
    'data': [
        'security/tour_security.xml',
        'security/ir.model.access.csv',
        'data/mail_templates.xml',
        'report/tour_itinerary_templates.xml',
        'report/tour_package_reports.xml',
        'views/tour_package_category_views.xml',
        'views/tour_package_pricing_views.xml',
        'views/tour_booking_views.xml',
        'views/tour_package_date_views.xml',
        'views/tour_package_views.xml',
        'views/tour_menu_views.xml',
        'views/website_homepage_views.xml',
        'views/website_templates_list.xml',
        'views/website_templates_page.xml',
        'views/website_menu_views.xml',
        'views/website_header_views.xml',
        'views/website_footer_views.xml',
        'views/website_theme_toggle_views.xml',
        'views/website_whatsapp_views.xml',
        'views/website_legal_views.xml',
        'views/website_faq_views.xml',
        'views/website_404_views.xml',
        'views/portal_templates.xml',
    ],
    'demo': [
        'data/tour_demo.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'tour_travel_kenya/static/src/scss/tour_frontend.scss',
            'tour_travel_kenya/static/src/js/kt_theme_toggle.js',
            'tour_travel_kenya/static/src/js/kt_whatsapp.js',
            'tour_travel_kenya/static/src/js/kt_wishlist.js',
            'tour_travel_kenya/static/src/js/kt_gallery_lightbox.js',
            'tour_travel_kenya/static/src/js/kt_scroll_effects.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
