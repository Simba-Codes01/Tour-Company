from odoo import fields, models


class TourPackageWaypoint(models.Model):
    _name = 'tour.package.waypoint'
    _description = 'Tour Package Route Waypoint'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, help='e.g. "Day 1-2: Amboseli National Park"')
    package_id = fields.Many2one('tour.package', required=True, ondelete='cascade', index=True)
    latitude = fields.Float(required=True, digits=(10, 6))
    longitude = fields.Float(required=True, digits=(10, 6))
