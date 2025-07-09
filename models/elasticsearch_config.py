from odoo import models, fields, api
from odoo.exceptions import ValidationError
from elasticsearch import Elasticsearch
import logging

# Connection states
CONNECTION_STATE = [('connected', 'Connected'),
                    ('disconnected', 'Disconnected')]

class ElasticsearchConfig(models.Model):
    _name = 'elasticsearch.config'
    _description = 'Elasticsearch Server Configuration'

    name = fields.Char(required=True, string='Connection Name')
    host = fields.Char(required=True, string='Host', default='localhost')
    port = fields.Integer(required=True, string='Port', default=9200)
    username = fields.Char(string='Username')
    password = fields.Char(string='Password')
    use_ssl = fields.Boolean(string='Use SSL', default=False)
    verify_ssl = fields.Boolean(string='Verify SSL', default=True)

    index_name = fields.Char(string='Index Name', required=True, default='odoo_products')

    state = fields.Selection(
        CONNECTION_STATE, string='Connection State', readonly=True, default='disconnected')

    def toggle_state(self):
        """Change state of the connection connected ==> disconnected
        """
        if self.state == "connected":
            self.state = "disconnected"

    def _get_elasticsearch_client(self):
        self.ensure_one()
    
        if not self.host and not self.port:
            raise ValidationError("Elasticsearch host & port are required.")

        connection_params = {
            'hosts': [f"{'https' if self.use_ssl else 'http'}://{self.host}:{self.port}"] 
        }

        if self.username and self.password:
            connection_params['basic_auth'] = (self.username, self.password)

        if self.verify_ssl:
            connection_params['verify_certs'] = self.verify_ssl

        try:
            return Elasticsearch(**connection_params)
        except Exception as e:
            raise ValidationError(f"Failed to connect to Elasticsearch: {str(e)}")

    def test_elasticsearch_connection(self):
        """Test Elasticsearch connection"""

        try:
            es = Elasticsearch(
                hosts=[f"{'https' if self.use_ssl else 'http'}://{self.host}:{self.port}"],
                basic_auth=(self.username, self.password) if self.username else None,
                verify_certs=self.verify_ssl
            )
            connection_successful = es.ping()
            
            if connection_successful:
                self.write({'state': "connected"})
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': 'Elasticsearch connection successful!',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                self.write({'state': "disconnected"})
                raise ValidationError("Connection Failed: Unable to connect to Elasticsearch")
        except Exception as e:
            raise ValidationError(f"Connection Failed: {str(e)}")