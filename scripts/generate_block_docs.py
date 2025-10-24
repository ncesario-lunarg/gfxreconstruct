#!/usr/bin/env python3

"""
Parses a GFXReconstruct YAML schema and generates Markdown documentation.

Usage:
    python generate_schema_docs.py <input_yaml_file> <output_markdown_file>

Requires:
    PyYAML (install with: pip install PyYAML)
"""

import sys
import yaml
import io
import html

# --- Helper functions for HTML table generation ---

def format_dispatch_param(param):
    """Formats a single dispatch parameter for an HTML list."""
    if isinstance(param, str):
        return f"<code>{html.escape(param)}</code>"
    if isinstance(param, dict):
        if 'from_context' in param:
            return f"from_context: <code>{html.escape(str(param['from_context']))}</code>"
        if 'construct_type' in param:
            fields = ", ".join([f"<code>{html.escape(f)}</code>" for f in param.get('from_fields', [])])
            return f"construct_type: <code>{html.escape(param['construct_type'])}</code><br>from_fields: [{fields}]"
        return f"<code>{html.escape(str(param))}</code>"
    return f"<code>{html.escape(str(param))}</code>"

def build_dispatch_html(dispatch_data):
    """Builds an HTML table for a block's dispatch information."""
    if not dispatch_data:
        return "(No dispatch)"

    dispatch_list = dispatch_data if isinstance(dispatch_data, list) else [dispatch_data]
    
    stream = io.StringIO()
    stream.write("<table style=\"border-collapse: collapse; width: 100%;\">")
    stream.write("<thead><tr style=\"background-color: #f2f2f2;\">")
    stream.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Method</th>")
    stream.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">When</th>")
    stream.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Params</th>")
    stream.write("</tr></thead><tbody>")
    
    for item in dispatch_list:
        method = item.get('method', 'N/A')
        handler = item.get('handler')
        
        if handler:
            method_str = f"Handler: <code>{handler}</code><br>Method: <code>{method}</code>"
        else:
            method_str = f"<code>{method}</code>"
            
        when_str = f"<code>{html.escape(item.get('when', 'Always'))}</code>"
        
        params = item.get('params', [])
        params_list_str = "<ul>" + "".join([f"<li>{format_dispatch_param(p)}</li>" for p in params]) + "</ul>"
        
        stream.write("<tr>")
        stream.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\">{method_str}</td>")
        stream.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\">{when_str}</td>")
        stream.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\">{params_list_str}</td>")
        stream.write("</tr>")

    stream.write("</tbody></table>")
    return stream.getvalue()

def build_fields_table_html(fields, title=None):
    """Builds an HTML table for a list of payload fields."""
    if not fields:
        return "(No fields)"

    stream = io.StringIO()
    if title:
        stream.write(f"<h5 style=\"margin: 5px 0;\">{html.escape(title)}</h5>")
        
    stream.write("<table style=\"border-collapse: collapse; width: 100%;\">")
    stream.write("<thead><tr style=\"background-color: #f2f2f2;\">")
    stream.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Name</th>")
    stream.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Type / Kind</th>")
    stream.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Count</th>")
    stream.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Details</th>")
    stream.write("</tr></thead><tbody>")

    for field in fields:
        name_str = f"<code>{html.escape(field.get('name', 'N/A'))}</code>"
        
        # Type / Kind
        if 'kind' in field:
            type_kind_str = f"<code>{html.escape(field.get('kind'))}</code>"
        elif field.get('type') == 'enum':
            type_kind_str = f"enum (<code>{html.escape(field.get('enum'))}</code>)"
        elif field.get('type') == 'array':
            elem_type = field.get('element', {}).get('type', '?')
            type_kind_str = f"array (elem: <code>{html.escape(elem_type)}</code>)"
        else:
            type_kind_str = f"<code>{html.escape(field.get('type', 'N/A'))}</code>"

        # Count
        if 'count' in field:
            count_str = f"<code>{html.escape(str(field.get('count')))}</code>"
        elif 'count_from' in field:
            count_str = f"from <code>{html.escape(field.get('count_from'))}</code>"
        else:
            count_str = "1"
            
        # Details
        details_list = []
        for key in ['has_uncompressed_size_prefix', 'uncompressed_len_field', 'uncompressed_len_expr', 
                    'base', 'len_field', 'offset_expr', 'interpretation', 'derived', 'expr', 'description']:
            if key in field:
                details_list.append(f"<b>{key}</b>: {html.escape(str(field[key]))}")
        
        if details_list:
            details_str = "<ul>" + "".join([f"<li>{d}</li>" for d in details_list]) + "</ul>"
        else:
            details_str = "N/A"

        stream.write("<tr>")
        stream.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\">{name_str}</td>")
        stream.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\">{type_kind_str}</td>")
        stream.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\">{count_str}</td>")
        stream.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\">{details_str}</td>")
        stream.write("</tr>")

    stream.write("</tbody></table>")
    return stream.getvalue()

def build_payload_html(block):
    """Builds the complete HTML for the 'Payload / Variants' cell."""
    payload = block.get('payload')
    prefix = block.get('prefix')
    variants = block.get('variants')
    
    stream = io.StringIO()
    if payload:
        stream.write(build_fields_table_html(payload))
        
    if prefix:
        stream.write(build_fields_table_html(prefix, title="Prefix"))
        
    if variants:
        stream.write("<h4 style=\"margin: 10px 0 5px 0;\">Variants</h4>")
        for variant in variants:
            title = f"Variant: <code>{variant.get('meta_data_type')}</code>"
            stream.write(build_fields_table_html(variant.get('payload'), title=title))
            
    result = stream.getvalue()
    return result or "N/A"


# --- Main Markdown Generation Functions ---

def generate_key_value_table(data):
    """Generates a 2-column Markdown table for a simple dictionary."""
    stream = io.StringIO()
    stream.write("| Property | Value |\n")
    stream.write("| --- | --- |\n")
    for key, value in data.items():
        value_str = str(value).replace("\n", " ")
        stream.write(f"| `{key}` | {value_str} |\n")
    return stream.getvalue()

def generate_external_enums_table(data):
    """Generates a table for the 'external_enums' section."""
    stream = io.StringIO()
    stream.write("| Enum Name | C++ Enum | Headers |\n")
    stream.write("| --- | --- | --- |\n")
    for name, info in data.items():
        headers = ", ".join([f"`{h}`" for h in info.get('headers', [])])
        stream.write(f"| `{name}` | `{info.get('cxx_enum', '')}` | {headers} |\n")
    return stream.getvalue()

def generate_primitives_table(data):
    """Generates a table for the 'primitives' section."""
    stream = io.StringIO()
    stream.write("| Primitive | Definition |\n")
    stream.write("| --- | --- |\n")
    for name, definition in data.items():
        stream.write(f"| `{name}` | `{str(definition)}` |\n")
    return stream.getvalue()

def generate_field_kinds_table(data):
    """Generates a table for the 'field_kinds' section."""
    stream = io.StringIO()
    stream.write("| Kind | Definition |\n")
    stream.write("| --- | --- |\n")
    for name, definition in data.items():
        def_str = str(definition).replace("\n", "<br>")
        stream.write(f"| `{name}` | {def_str} |\n")
    return stream.getvalue()

def generate_complex_types_table(data):
    """
    Generates a table for the 'complex_types' section, with a
    nested HTML table for fields.
    """
    stream = io.StringIO()
    stream.write("| Type Name | Fields |\n")
    stream.write("| --- | --- |\n")
    
    for name, definition in data.items():
        stream.write(f"| **`{name}`** | ")
        
        sub_table = io.StringIO()
        sub_table.write("<table style=\"border-collapse: collapse; width: 100%;\">")
        sub_table.write("<thead>")
        sub_table.write("<tr style=\"background-color: #f2f2f2;\">")
        sub_table.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Name</th>")
        sub_table.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Type</th>")
        sub_table.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Count</th>")
        sub_table.write("</tr>")
        sub_table.write("</thead>")
        sub_table.write("<tbody>")
        
        fields = definition.get('fields', [])
        if not fields:
            sub_table.write("<tr><td colspan=\"3\" style=\"border: 1px solid #ddd; padding: 8px;\">(No fields defined)</td></tr>")
        else:
            for field in fields:
                field_name = field.get('name', 'N/A')
                
                field_type_str = field.get('type', 'N/A')
                type_str = ""
                if field_type_str == 'array':
                    element_type = field.get('element', {}).get('type', '?')
                    type_str = f"array (element: <code>{html.escape(element_type)}</code>)"
                elif field_type_str == 'enum':
                    type_str = f"enum (<code>{html.escape(field.get('enum', '?'))}</code>)"
                else:
                    type_str = f"<code>{html.escape(field_type_str)}</code>"
                
                count_str = "1"
                if 'count' in field:
                    count_str = str(field['count'])
                elif 'count_from' in field:
                    count_str = f"from <code>{html.escape(field['count_from'])}</code>"
                elif field_type_str == 'array':
                     if 'count' not in field and 'count_from' not in field:
                         count_str = "N/A"

                sub_table.write("<tr>")
                sub_table.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\"><code>{html.escape(field_name)}</code></td>")
                sub_table.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\">{type_str}</td>")
                sub_table.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\"><code>{html.escape(count_str)}</code></td>")
                sub_table.write("</tr>")

        sub_table.write("</tbody></table>")
        sub_table_str = sub_table.getvalue()
        stream.write(f"{sub_table_str} |\n")
        
    return stream.getvalue()

def generate_levels_table(data):
    """Generates a table for the 'levels' section."""
    stream = io.StringIO()
    stream.write("| Name | Handled By |\n")
    stream.write("| --- | --- |\n")
    for level in data:
        stream.write(f"| `{level.get('name')}` | `{level.get('handled_by')}` |\n")
    return stream.getvalue()

def generate_blocks_table(data):
    """Generates a table for the 'blocks' section with HTML sub-tables."""
    stream = io.StringIO()
    stream.write("| Name | Block Type | Payload / Variants | Dispatch |\n")
    stream.write("| --- | --- | --- | --- |\n")
    
    for block in data:
        name = block.get('name', 'N/A')
        block_type = block.get('block_type', 'N/A')
        
        # Generate HTML for payload and dispatch cells
        payload_html = build_payload_html(block)
        dispatch_html = build_dispatch_html(block.get('dispatch'))
        
        # Write the main table row
        stream.write(
            f"| **{name}** | `{block_type}` "
            f"| {payload_html} "
            f"| {dispatch_html} |\n"
        )
    return stream.getvalue()

def generate_documentation(schema_data):
    """Generates the full Markdown documentation string from the parsed schema."""
    stream = io.StringIO()
    
    schema_name = schema_data.get('schema', {}).get('name', 'Schema')
    schema_version = schema_data.get('schema', {}).get('version', '')
    stream.write(f"# {schema_name.capitalize()} Schema Documentation (v{schema_version})\n\n")

    generators = {
        'schema': ("Schema Properties", generate_key_value_table),
        'external_enums': ("External Enums", generate_external_enums_table),
        'primitives': ("Primitives", generate_primitives_table),
        'field_kinds': ("Special Field Kinds", generate_field_kinds_table),
        'complex_types': ("Complex Types (Structs)", generate_complex_types_table),
        'block_header': ("Block Header", generate_key_value_table),
        'levels': ("Decoding Levels", generate_levels_table),
        'blocks': ("Block Payloads", generate_blocks_table),
    }

    for key, (title, func) in generators.items():
        if key in schema_data:
            stream.write(f"## {title}\n\n")
            stream.write(func(schema_data[key]))
            stream.write("\n\n---\n\n")
            
    return stream.getvalue()

def main():
    """Main script entry point."""
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_yaml> <output_markdown>", file=sys.stderr)
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"Loading schema from '{input_file}'...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            schema_data = yaml.load(f, Loader=yaml.CLoader)
    except AttributeError:
        with open(input_file, 'r', encoding='utf-8') as f:
            schema_data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}", file=sys.stderr)
        sys.exit(1)

    print("Generating Markdown documentation...")
    try:
        markdown_content = generate_documentation(schema_data)
    except Exception as e:
        print(f"An unexpected error occurred during documentation generation: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Writing documentation to '{output_file}'...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
    except IOError as e:
        print(f"Error writing to output file: {e}", file=sys.stderr)
        sys.exit(1)
        
    print("Done.")

if __name__ == "__main__":
    main()