from odoo import api, fields, models


class TourPackagePricing(models.Model):
    _name = 'tour.package.pricing'
    _description = 'Tour Package Pricing Tier'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, translate=True, help='e.g. "Standard Camping", "Premium Lodge"')
    description = fields.Text(translate=True)
    package_id = fields.Many2one('tour.package', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, ondelete='restrict',
        domain="[('type', '=', 'service')]")
    currency_id = fields.Many2one(related='package_id.currency_id')
    price = fields.Float(related='product_id.list_price', readonly=False, store=True, digits='Product Price')
    seats_max = fields.Integer(string='Max Travelers for this Tier', default=0, help='0 = no per-tier limit')

    @api.model_create_multi
    def create(self, vals_list):
        pricings = super().create(vals_list)
        for pricing in pricings:
            pricing.product_id.write({'sale_ok': True, 'website_published': False})
        return pricings
