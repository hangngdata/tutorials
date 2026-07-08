from odoo import models, fields

class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Estate Property Type"
    _order = "sequence,name"

    name = fields.Char('Type', required=True)
    property_ids = fields.One2many("estate.property", "property_type_id", string="Properties")
    sequence = fields.Integer('Sequence', default=1, help="Used to determine the order of property types. Lower sequence means more commonly used.")

    _unique_name = models.Constraint(
        'UNIQUE(name)',
        'The property type name must be unique',
    )