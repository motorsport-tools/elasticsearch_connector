/** @odoo-module */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class JsonViewerWidget extends Component {
    static template = "elasticsearch_connector.JsonViewerWidget";
    static props = {
        ...standardFieldProps,
    };

    get formattedJson() {
        try {
            const jsonData = JSON.parse(this.props.record.data[this.props.name] || '{}');
            return JSON.stringify(jsonData, null, 4);
        } catch (e) {
            return this.props.record.data[this.props.name] || '';
        }
    }

    onJsonChange(ev) {
        if (!this.props.readonly) {
            try {
                const parsedJson = JSON.parse(ev.target.value);
                this.props.record.update({
                    [this.props.name]: JSON.stringify(parsedJson, null, 4)
                });
            } catch (e) {
                console.warn("Invalid JSON input", e);
            }
        }
    }
}

registry.category("fields").add("json_viewer", {
    component: JsonViewerWidget,
    supportedTypes: ["char", "text"],
});


