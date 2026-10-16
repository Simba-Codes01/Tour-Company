import base64
import hashlib

from odoo import api, models
from odoo.tools.misc import file_open

FAVICON_PATH = 'tour_travel_kenya/static/src/img/seriani_favicon.png'
FAVICON_PARAM = 'tour_travel_kenya.favicon_sha1'
LOGO_PATH = 'tour_travel_kenya/static/src/img/seriani_logo_cropped.png'
LOGO_PARAM = 'tour_travel_kenya.logo_sha1'
WEBSITE_NAME = 'Seriani Tours & Travel'

# Odoo's stock pages this site doesn't use, kept out of sitemap.xml (and so out
# of Google): website_sale is only a dependency for product.product - there's no
# real public shop - and /website/info is Odoo's own "about this install" page.
# Filtered here rather than with sitemap=False on the routes: website_sale's
# controller is subclassed by other installed modules (comparison, wishlist),
# each keeping its own copy of the /shop route with the original sitemap rule.
SITEMAP_EXCLUDED_PREFIXES = ('/shop', '/website/info')


class Website(models.Model):
    _inherit = 'website'

    def _enumerate_pages(self, query_string=None, force=False):
        for page in super()._enumerate_pages(query_string=query_string, force=force):
            loc = page['loc']
            if not any(loc == p or loc.startswith(p + '/') for p in SITEMAP_EXCLUDED_PREFIXES):
                yield page

    @api.model
    def _kt_apply_favicon(self):
        """Set the default website's favicon from the module's PNG.

        Called from data/website_branding_data.xml on every install/upgrade.
        A <record> on website.default_website can't do this: that xmlid is
        noupdate in the website module, so upgrades silently skip it. Only
        writes when the PNG changed since it was last applied, so a favicon
        uploaded in the backend is kept until the repo file itself changes.
        """
        with file_open(FAVICON_PATH, 'rb') as f:
            data = f.read()
        sha1 = hashlib.sha1(data).hexdigest()
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param(FAVICON_PARAM) == sha1:
            return
        website = self.env.ref('website.default_website', raise_if_not_found=False)
        if website:
            website.favicon = base64.b64encode(data)
            params.set_param(FAVICON_PARAM, sha1)

    @api.model
    def _kt_apply_logo(self):
        """Set the default website's name and logo (separate from
        res.company's own name/logo) the same noupdate-safe way as
        _kt_apply_favicon above - see that method's docstring. The mobile
        header reads website.logo specifically, and it shipped as Odoo's
        generic unbranded default (a grey "ODOO" wordmark SVG) until this
        ran, which is why the mobile logo looked broken.
        """
        with file_open(LOGO_PATH, 'rb') as f:
            data = f.read()
        sha1 = hashlib.sha1(data).hexdigest()
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param(LOGO_PARAM) == sha1:
            return
        website = self.env.ref('website.default_website', raise_if_not_found=False)
        if website:
            website.logo = base64.b64encode(data)
            website.name = WEBSITE_NAME
            params.set_param(LOGO_PARAM, sha1)

    @api.model
    def _kt_apply_seo_page_meta(self):
        """Fix the default Odoo placeholder title/description on the
        homepage and Contact Us page ("This is the homepage of the
        website", no title at all) - plain field writes, not file-based,
        so no noupdate issue and nothing to track between runs.
        """
        Page = self.env['website.page'].sudo()
        website = self.env.ref('website.default_website', raise_if_not_found=False)
        if website:
            homepage = Page.search([('url', '=', '/'), ('website_id', '=', website.id)], limit=1)
            if homepage:
                homepage.write({
                    'website_meta_title': 'Seriani Tours & Travel | Kenya Safari Tours & Travel Packages',
                    'website_meta_description': (
                        "Book Kenya safaris direct with Seriani Tours & Travel - Masai Mara, "
                        "Amboseli, Tsavo and more. Serving travelers across East Africa and "
                        "beyond, no middleman markups."
                    ),
                })
        contactus = Page.search([('url', '=', '/contactus')], limit=1)
        if contactus:
            contactus.write({
                'website_meta_title': 'Contact Us | Seriani Tours & Travel',
                'website_meta_description': (
                    "Get in touch with Seriani Tours & Travel to plan your Kenya safari - "
                    "WhatsApp, call or email us directly, wherever in East Africa you're "
                    "traveling from."
                ),
            })
