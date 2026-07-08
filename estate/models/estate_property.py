from datetime import datetime, timedelta
from odoo import _, api, fields, models, exceptions
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate Property"
    _order = "id desc"

    name = fields.Char('Title', required=True)
    description = fields.Text('Description')
    postcode = fields.Char('Postcode')
    date_availability = fields.Date('Date Availability', copy=False, default=lambda self: datetime.today() + timedelta(weeks=90))
    
    expected_price = fields.Float('Expected Price', required=True)
    _check_expected_price = models.Constraint(
        'CHECK (expected_price > 0)',
        'The expected price must be strictly positive.',
    )

    selling_price = fields.Float('Selling Price', readonly=True, copy=False)
    _check_selling_price = models.Constraint(
        'CHECK (selling_price > 0)',
        'The selling price must be positive.',
    )

    bedrooms = fields.Integer('Bedrooms', default=2)
    living_area = fields.Integer('Living Area (sqm)')
    facades = fields.Integer('Facades')
    garage = fields.Boolean('Garage')
    garden = fields.Boolean('Garden')
    garden_area = fields.Integer('Garden Area')
    garden_orientation = fields.Selection([
        ('north', 'North'),
        ('south', 'South'),
        ('east', 'East'),
        ('west', 'West')
    ], 'Garden Orientation')
    active = fields.Boolean('Active', default=True)
    state = fields.Selection([
        ('new', 'New'), 
        ('offer_received', 'Offer Received'), 
        ('offer_accepted', 'Offer Accepted'),    
        ('sold', 'Sold'),
        ('cancelled', 'Cancelled')
     ], 'Status', default='new', required=True, copy=False)
    
    property_type_id = fields.Many2one("estate.property.type", string="Type")
    buyer = fields.Many2one("res.partner", string="Buyer", copy=False)
    salesperson = fields.Many2one("res.users", string="Salesperson", default=lambda self: self.env.user)
    tag_ids = fields.Many2many("estate.property.tag", string="Tags")
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offers")
    
    total = fields.Float(compute="_compute_total", string="Total")
    best_price = fields.Float(compute="_compute_best_price", string='Best Offer')

    @api.depends('living_area', 'garden_area')
    def _compute_total(self):
        for record in self:
            record.total = record.living_area + record.garden_area

    @api.depends('offer_ids.price')
    def _compute_best_price(self):
        for record in self:
            if record.offer_ids:
                record.best_price = max(record.offer_ids.mapped('price'))
            else:
                record.best_price = 0.0

    @api.onchange('garden')
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = 'north'
        else:
            self.garden_area = 0
            self.garden_orientation = False
    
    def action_set_sold(self):
        for record in self:
            if record.state == 'cancelled':
                raise exceptions.UserError("Cancelled properties cannot be sold.")
            record.state = 'sold'
        return True

    def action_set_cancelled(self):
        for record in self:
            if record.state == 'sold':
                raise exceptions.UserError("Sold properties cannot be cancelled.")
            record.state = 'cancelled'
        return True
    
    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price_constraint(self):
        for record in self:
            if (
                not float_is_zero(record.selling_price, precision_digits=2)
                and float_compare(record.selling_price, 0.9 * record.expected_price, precision_digits=2) == -1
            ):
                raise exceptions.ValidationError(
                    "The selling price must be at least 90% of the expected price."
                )
    
    @api.ondelete(at_uninstall=False)
    def _unlink_except_wrong_state(self):
        for record in self:
            if record.state not in ['new', 'cancelled']:
                raise UserError("Only new or cancelled properties can be deleted.")