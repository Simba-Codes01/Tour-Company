from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    wishlist_tour_ids = fields.Many2many('tour.package', string='Saved Tours')
