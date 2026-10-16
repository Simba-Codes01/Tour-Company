import base64
import hashlib

from odoo import api, models
from odoo.tools.misc import file_open

FAVICON_PATH = 'tour_travel_kenya/static/src/img/seriani_favicon.png'
FAVICON_PARAM = 'tour_travel_kenya.favicon_sha1'
LOGO_PATH = 'tour_travel_kenya/static/src/img/seriani_logo_cropped.png'
LOGO_PARAM = 'tour_travel_kenya.logo_sha1'
WEBSITE_NAME = 'Seriani Tours & Travel'


class Website(models.Model):
    _inherit = 'website'

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
