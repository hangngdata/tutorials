from datetime import date, timedelta

from odoo import models, fields, api
from odoo.exceptions import UserError

class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate Property Offer"
    _order = "price desc"

    price = fields.Float('Price')
    _check_price = models.Constraint(
        'CHECK (price > 0)',
        'The offered price must be positive.',
    )

    status = fields.Selection([
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('refused', 'Refused')
    ], 'Status', copy=False)
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    property_id = fields.Many2one("estate.property", string="Property", required=True, ondelete='cascade')

    create_date = fields.Datetime('Created on', default=fields.Datetime.now)
    validity = fields.Integer('Validity (days)', default=7)
    date_deadline = fields.Date("Deadline", compute='_compute_date_deadline', inverse='_inverse_date_deadline')

    @api.depends('validity', 'create_date')
    def _compute_date_deadline(self):
        for record in self:
            create_dt = record.create_date or fields.Datetime.now()
            if hasattr(create_dt, 'date'):
                create_date = create_dt.date()
            else:
                # fallback for string representation
                create_date = fields.Datetime.from_string(create_dt).date() if create_dt else fields.Datetime.now().date()

            record.date_deadline = create_date + timedelta(days=record.validity)

    def _inverse_date_deadline(self):
        for record in self:
            if not record.date_deadline:
                record.validity = 0
                continue
            create_dt = record.create_date or fields.Datetime.now()
            if hasattr(create_dt, 'date'):
                create_date = create_dt.date()
            else:
                create_date = fields.Datetime.from_string(create_dt).date() if create_dt else fields.Datetime.now().date()
            record.validity = (record.date_deadline - create_date).days

    def action_accept(self):
        for record in self:
            other_accepted = record.property_id.offer_ids.filtered(
                lambda offer: offer.status == 'accepted' and offer != record
            )
            if other_accepted:
                raise UserError("Only one offer can be accepted per property.")
            record.status = 'accepted'
            record.property_id.state = 'offer_accepted'
            record.property_id.buyer = record.partner_id
            record.property_id.selling_price = record.price
        return True
    
    def action_refuse(self):
        for record in self:
            record.status = 'refused'
            if record.property_id.buyer == record.partner_id and record.property_id.selling_price == record.price:
                remaining_offers = record.property_id.offer_ids.filtered(lambda offer: offer.status != 'refused')
                record.property_id.state = 'offer_received' if remaining_offers else 'new'
                record.property_id.buyer = False
                record.property_id.selling_price = 0.000001
        return True
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            property_id = self.env['estate.property'].browse(vals['property_id'])

            # Rule 1: reject offers lower than existing offers on this property
            if property_id.offer_ids:
                max_offer = max(property_id.offer_ids.mapped('price'))
                if vals['price'] < max_offer:
                    raise UserError(
                        "The offer amount must be higher than %.2f" % max_offer
                    )

            # Rule 2: property moves to 'Offer Received' once an offer exists
            property_id.state = 'offer_received'

        return super().create(vals_list)