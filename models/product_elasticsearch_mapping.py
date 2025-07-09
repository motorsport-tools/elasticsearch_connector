from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
from elasticsearch import Elasticsearch, helpers
from odoo.addons.elasticsearch_connector.models.json_field import JSONField
import logging
import json

_logger = logging.getLogger(__name__)

class ProductElasticsearchMapping(models.Model):
    _name = 'product.elasticsearch.mapping'
    _description = 'Product Elasticsearch Mapping Configuration'

    config_id = fields.Many2one('elasticsearch.config', required=True)
    model = fields.Selection([
        ('product.product', 'Product Variant'),
        #('product.template', 'Product Template')
    ], required=True)
    
    index_name = fields.Char(compute='_compute_index_name', store=True)
    index_created = fields.Boolean(string='Index Created', compute='_compute_index_status', default=False)
    index_mapping = JSONField(string='Index Mapping', default=lambda self: self._default_index_mapping(), help='Not editable with created index, accepts JSON')
    indexing_domain = fields.Char(string='Indexing Domain')
    
    """
    def write(self, vals):
        index_mapping = vals.get('index_mapping')
        vals['index_mapping'] = self.set_json_data(index_mapping)
        
        return super().write(vals)
    """
    """
    def create(self, vals):
        index_mapping = vals.get('index_mapping')

        vals['index_mapping'] = self.set_json_data(index_mapping)
        
        return super().create(vals)
    """

    def set_json_data(self, raw_data):
        try:
            parsed_data = json.loads(raw_data)  
            return json.dumps(parsed_data, indent=4)  
        except json.JSONDecodeError:
            return raw_data

    def _default_index_mapping(self):
        
        mapping = {
                "dynamic": True,
                "dynamic_templates": [
                    {
                        "id_long_or_null": {
                            "match_mapping_type": "*",
                            "match":   "*_id",
                            "mapping": {
                                'type': 'long',
                                'ignore_malformed': True,
                            },
                        },
                    },
                ],
                "properties": {
                    "name": {
                        'type': 'text',
                        'search_analyzer': 'autocomplete_analyzer'
                    },
                    "description_sale": {
                        "type": "text",
                    },
                    "pprint_json_ld": {
                        'type': 'text',
                        'index': False,
                    },
                    "json_ld": {
                        'type': 'text',
                        'index': False,
                    },
                    "image_ids": {
                        'type': 'object'
                    },
                    "website_meta_title": {
                        'type': 'text',
                    },
                    "website_meta_description": {
                        'type': 'text',
                    },
                    "website_meta_keywords": {
                        'type': 'text',
                    },
                    "hs_code": {
                        'type': 'text',
                    }
                }
            }
        return {
                    "settings": {
                        "index" : {
                            "number_of_replicas" : 0
                        },
                        "analysis": {
                            "analyzer": {
                                "autocomplete_analyzer": {
                                    "tokenizer": 'autocomplete_analyzer',
                                    "filter": 'lowercase',
                                },
                            },
                            "tokenizer": {
                                "autocomplete_analyzer": {
                                    "type": 'ngram',
                                    "min_gram": 3,
                                    "max_gram": 3,
                                    "token_chars": ['letter', 'digit'],
                                },
                            },
                        },
                    },
                    "mappings": mapping
                }
    @api.depends('model')
    def _compute_index_name(self):
        for record in self:
            if record.model:
                record.index_name = f"odoo_{record.model.replace('.', '_')}"
            else:
                record.index_name = False

    def _compute_index_status(self):
        """Check if index exists in Elasticsearch"""
        for record in self:
            if not record.index_name:
                record.index_created = False
                continue
            
            try:
                es = self._get_elasticsearch_client()
                record.index_created = es.indices.exists(index=record.index_name)
            except Exception:
                record.index_created = False

    def _get_elasticsearch_client(self):
        """
        Wrapper method to get Elasticsearch client from configuration
        
        :return: Elasticsearch client instance
        """
        return self.config_id._get_elasticsearch_client()

    def create_elasticsearch_index_and_mapping(self):
        """Create index and mapping in Elasticsearch"""
        self.ensure_one()
        es = self._get_elasticsearch_client()
    
        try:
            es.indices.create(
                index=self.index_name, 
                body=self.index_mapping
            )
        except Exception as e:
            # Raise a more informative error
            raise ValidationError(f"Failed to Create Elasticsearch index: {str(e)}")
        finally:
            self.write({'index_created': True})

    def index_all_products(self):
        self.ensure_one()

        es = self._get_elasticsearch_client()

        domain = []
        if self.indexing_domain:
            try:
                domain = safe_eval(self.indexing_domain)
            except Exception as e:
                raise ValidationError(f"Invalid indexing domain: {str(e)}")
            
        def product_generator():

            products = self.env['product.product'].search(domain, order='id')
            
            for product in products:
                try:
                    product._sync_product_to_elasticsearch()
                except Exception as e:
                    logging.error(f"Error syncing product {product.id} to Elasticsearch: {str(e)}")

        try:
            product_generator()
            
            logging.info(f"Completed indexing all products")
            
            return True
        except Exception as e:
            raise ValidationError(f"Bulk indexing failed: {str(e)}")

    def delete_elasticsearch_index(self):
        """Delete index from Elasticsearch"""
        self.ensure_one()
        es = self._get_elasticsearch_client()
        
        # Check if index exists before attempting to delete
        if es.indices.exists(index=self.index_name):
            try:
                es.indices.delete(index=self.index_name)
                # Log the deletion
                logging.info(f"Deleted Elasticsearch index: {self.index_name}")
            except Exception as e:
                # Raise a more informative error
                raise ValidationError(f"Failed to delete Elasticsearch index: {str(e)}")

    def index_mapping_reset_default(self):
        self.index_mapping = self._default_index_mapping()
