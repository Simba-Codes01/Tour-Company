from odoo import fields, models


class TourPackageCategory(models.Model):
    _name = 'tour.package.category'
    _description = 'Tour Package Category'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    image_1920 = fields.Image('Image')
    package_ids = fields.One2many('tour.package', 'category_id', string='Packages')
    package_count = fields.Integer(compute='_compute_package_count')

    def _compute_package_count(self):
        counts = dict(self.env['tour.package']._read_group(
            domain=[('category_id', 'in', self.ids)],
            groupby=['category_id'],
            aggregates=['__count'],
        ))
        for category in self:
            category.package_count = counts.get(category, 0)
