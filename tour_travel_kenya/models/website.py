import base64
import hashlib

from markupsafe import Markup

from odoo import api, models
from odoo.tools.json import scriptsafe as json_scriptsafe
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

# Countries Seriani actively markets to, besides worldwide - see the
# TravelAgency structured data below
AREA_SERVED = ['Kenya', 'Uganda', 'Tanzania', 'Rwanda', 'Burundi', 'South Sudan']
SOCIAL_FIELDS = ['social_facebook', 'social_instagram', 'social_twitter', 'social_youtube',
                 'social_tiktok', 'social_linkedin']


class Website(models.Model):
    _inherit = 'website'

    def _enumerate_pages(self, query_string=None, force=False):
        for page in super()._enumerate_pages(query_string=query_string, force=force):
            loc = page['loc']
            if not any(loc == p or loc.startswith(p + '/') for p in SITEMAP_EXCLUDED_PREFIXES):
                yield page

    def _kt_get_organization_structured_data(self):
        """Site-wide TravelAgency JSON-LD, rendered in every page's head by
        views/website_seo_views.xml. Built here rather than inline in QWeb so
        values are JSON-encoded instead of HTML-escaped (the inline version
        published the name as "Seriani Tours &amp; Travel"), and so empty
        email/sameAs values are left out instead of emitted blank. The @id is
        what each package's TouristTrip points at as its provider."""
        self.ensure_one()
        company = self.company_id.sudo()
        base_url = self.get_base_url()
        prices = self.env['tour.package'].sudo().search(
            [('website_published', '=', True)]).pricing_ids.mapped('price')
        address = {'@type': 'PostalAddress', 'addressLocality': 'Nairobi', 'addressCountry': 'KE'}
        # Only trust the company address once it's actually filled in with the
        # Kenyan office - never publish a leftover placeholder address
        if company.country_id.code == 'KE' and company.street:
            address.update({
                'streetAddress': ', '.join(filter(None, [company.street, company.street2])),
                'addressLocality': company.city or 'Nairobi',
            })
            if company.zip:
                address['postalCode'] = company.zip
        data = {
            '@context': 'https://schema.org',
            '@type': 'TravelAgency',
            '@id': base_url + '/#organization',
            'name': self.name or company.name,
            'alternateName': ['Seriani Tours and Travel', 'Seriani Tours', 'Seriani Safaris'],
            'description': (
                'Nairobi-based Kenya safari operator running private guided safaris to the Masai Mara, '
                'Amboseli, Samburu, Lake Nakuru, Tsavo and more - planned in-house and booked direct, '
                'with no middleman markups.'
            ),
            'url': base_url,
            'logo': '%s/logo.png?company=%s' % (base_url, company.id),
            'image': '%s/logo.png?company=%s' % (base_url, company.id),
            'address': address,
            'areaServed': [{'@type': 'Country', 'name': name} for name in AREA_SERVED]
                          + [{'@type': 'Place', 'name': 'Worldwide'}],
            'knowsAbout': ['Kenya safaris', 'Masai Mara', 'Great Migration', 'Amboseli National Park',
                           'Samburu National Reserve', 'Lake Nakuru', 'Tsavo', 'Ol Pejeta'],
        }
        if company.phone:
            data['telephone'] = company.phone
            data['contactPoint'] = {
                '@type': 'ContactPoint',
                'telephone': company.phone,
                'contactType': 'reservations',
                'availableLanguage': ['English', 'Swahili'],
            }
        if company.email:
            data['email'] = company.email
            data.setdefault('contactPoint', {'@type': 'ContactPoint', 'contactType': 'reservations'})['email'] = company.email
        if prices:
            data['priceRange'] = '$%d-$%d' % (min(prices), max(prices))
        same_as = [self[field] for field in SOCIAL_FIELDS if self[field]]
        if same_as:
            data['sameAs'] = same_as
        return Markup(json_scriptsafe.dumps(data, indent=4))

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
                        "Amboseli, Tsavo and more. Welcoming travelers from East Africa and "
                        "around the world, no middleman markups."
                    ),
                })
        contactus = Page.search([('url', '=', '/contactus')], limit=1)
        if contactus:
            contactus.write({
                'website_meta_title': 'Contact Us | Seriani Tours & Travel',
                'website_meta_description': (
                    "Get in touch with Seriani Tours & Travel to plan your Kenya safari - "
                    "WhatsApp, call or email us directly, wherever in the world you're "
                    "traveling from."
                ),
            })
