#!/usr/bin/env python3

"""
Generates Markdown documentation from "GFXReconstruct yaml schema."

Usage:
    python generate_schema_docs.py <input_yaml_file> <output_markdown_file>
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
    stream.write("<table style=\"border: 1px solid;\">")
    stream.write("<thead><tr>")
    stream.write("<th>Method</th>")
    stream.write("<th>When</th>")
    stream.write("<th>Params</th>")
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
        stream.write(f"<td>{method_str}</td>")
        stream.write(f"<td>{when_str}</td>")
        stream.write(f"<td>{params_list_str}</td>")
        stream.write("</tr>")

    stream.write("</tbody></table>")
    return stream.getvalue()

def build_fields_table_html(schema_data, fields, title=None):
    """Builds an HTML table for a list of payload fields."""
    if not fields:
        return "(No fields)"

    stream = io.StringIO()
    if title:
        stream.write(f"<h5 style=\"margin: 5px 0;\">{html.escape(title)}</h5>")
        
    stream.write("<table style=\"border: 1px solid\">")
    stream.write("<thead><tr>")
    stream.write("<th>Name</th>")
    stream.write("<th>Type</th>")
    stream.write("<th>Count</th>")
    stream.write("<th>Details</th>")
    stream.write("</tr></thead><tbody>")

    for field in fields:
        name_str = f"<code>{html.escape(field.get('name', 'N/A'))}</code>"

        # Type / Kind
        if 'kind' in field:
            type_kind_str = f"<a href=\"#special-{field.get('kind')}\">{field.get('kind')}</a>"
        elif field.get('type') == 'enum':
            type_kind_str = f"<a href=\"#enum-{field.get('enum')}\">{field.get('enum')}</a>"
        elif field.get('type') == 'array':
            elem_type = field.get('element', {}).get('type', '?')
            if elem_type in schema_data.get('complex_types', {}).keys():
                elem_type = f"<a href=\"#complex-type-{elem_type}\">{elem_type}</a>"
            elif elem_type in schema_data.get('primitives', {}).keys():
                elem_type = f"<a href=\"#primitive-{elem_type}\">{elem_type}</a>"
            type_kind_str = f"<code>{elem_type}[]</code>"
        else:
            ty = field.get('type', 'N/A')
            if ty in schema_data.get('complex_types', {}).keys():
                ty = f"<a href=\"#complex-type-{ty}\">{ty}</a>"
            elif ty in schema_data.get('primitives', {}).keys():
                ty = f"<a href=\"#primitive-{ty}\">{ty}</a>"
            type_kind_str = f"<code>{ty}</code>"

        # Count
        if 'count' in field:
            count_str = f"<code>{html.escape(str(field.get('count')))}</code>"
        elif 'count_from' in field:
            count_str = f"from <code>{html.escape(field.get('count_from'))}</code>"
        else:
            count_str = "1"

        # Details
        # details_list = []
        # for key in ['has_uncompressed_size_prefix', 'uncompressed_len_field', 'uncompressed_len_expr', 
        #             'base', 'len_field', 'offset_expr', 'interpretation', 'derived', 'expr', 'description']:
        #     if key in field:
        #         details_list.append(f"<b>{key}</b>: {html.escape(str(field[key]))}")
        
        # if details_list:
        #     details_str = "<ul>" + "".join([f"<li>{d}</li>" for d in details_list]) + "</ul>"
        # else:
        #     details_str = "N/A"
        details_str = field.get('description', '')

        stream.write("<tr>")
        stream.write(f"<td>{name_str}</td>")
        stream.write(f"<td>{type_kind_str}</td>")
        stream.write(f"<td>{count_str}</td>")
        stream.write(f"<td>{details_str}</td>")
        stream.write("</tr>")

    stream.write("</tbody></table>")
    return stream.getvalue()

def build_payload_html(schema_data, payload_fields):
    """Builds the complete HTML for a simple 'payload' list."""
    if not payload_fields:
        return "N/A"
    return build_fields_table_html(schema_data, payload_fields)


# --- Main Markdown Generation Functions ---

def generate_key_value_table(data):
    """Generates a 2-column Markdown table for a simple dictionary."""
    stream = io.StringIO()
    stream.write("| Property | Value |\n")
    stream.write("| --- | --- |\n")
    for key, value in data.items():
        if isinstance(value, list):
            value_str = "".join([f"<li>{str(v)}</li>" for v in value])
        else:
            value_str = str(value).replace("\n", " ")
        stream.write(f"| `{key}` | {value_str} |\n")
    return stream.getvalue()

def generate_block_header_table(_, data):
    """Generates a 2-column Markdown table for a simple dictionary."""
    stream = io.StringIO()
    stream.write(f'A "frame" is delimited by a <a href="#complex-type-{data["use_type"]}">{data["use_type"]}</a>.\n\n')
    compression = data['compression']
    stream.write(f'Whether or not the "frame" is compressed is determined by `{compression["indicator"]}`.\n\n')
    stream.write(compression["note"])
    return stream.getvalue()

def generate_external_enums_table(_, data):
    """Generates a table for the 'external_enums' section."""
    stream = io.StringIO()
    stream.write("| Enum Name | C++ Enum | Headers |\n")
    stream.write("| --- | --- | --- |\n")
    for name, info in data.items():
        headers = ", ".join([f"`{h}`" for h in info.get('headers', [])])
        stream.write(f"| <a id=\"enum-{name}\"></a>`{name}` | `{info.get('cxx_enum', '')}` | {headers} |\n")
    return stream.getvalue()

def generate_primitives_table(_, data):
    """Generates a table for the 'primitives' section."""
    stream = io.StringIO()
    stream.write("| Primitive | Size in Bytes | Type |\n")
    stream.write("| --- | --- | --- |\n")
    for name, definition in data.items():
        ty = 'Unknown'
        if 'wchar' == name:
            ty = '"Wide" Character (for UTF-16/32)'
        elif 'signed' in definition:
            if definition['signed']:
                ty = 'Signed Integer'
            else:
                ty = 'Unsigned Integer'
        elif definition.get('float'):
            ty = 'Floating Point'
        stream.write(f"| <a id=\"primitive-{name}\"></a>`{name}` | `{str(definition['bytes'])}` | {ty} |\n")
    return stream.getvalue()

def generate_field_kinds_table(_, data):
    """Generates a table for the 'field_kinds' section."""
    stream = io.StringIO()
    stream.write("| Kind | Definition |\n")
    stream.write("| --- | --- |\n")
    for name, definition in data.items():
        def_str = str(definition['description']).rstrip()
        stream.write(f"| <a id=\"special-{name}\"></a>`{name}` | {def_str} |\n")
    return stream.getvalue()

def generate_complex_types_table(schema_data, data):
    """
    Generates a table for the 'complex_types' section, with a
    nested HTML table for fields.
    """
    stream = io.StringIO()
    stream.write("| Type Name | Fields |\n")
    stream.write("| --- | --- |\n")
    
    for name, definition in data.items():
        stream.write(f"| **<a id=\"complex-type-{name}\"></a>`{name}`** | ")
        
        sub_table = io.StringIO()
        sub_table.write("<table style=\"border: 1px solid\">")
        sub_table.write("<thead>")
        sub_table.write("<tr>")
        sub_table.write("<th>Name</th>")
        sub_table.write("<th>Type</th>")
        sub_table.write("<th>Count</th>")
        sub_table.write("<th>Description</th>")
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
                    elem_type = field.get('element', {}).get('type', '?')
                    if elem_type in schema_data.get('complex_types', {}).keys():
                        elem_type = f"<a href=\"#complex-type-{elem_type}\">{elem_type}</a>"
                    elif elem_type in schema_data.get('primitives', {}).keys():
                        elem_type = f"<a href=\"#primitive-{elem_type}\">{elem_type}</a>"
                    type_str = f"<code>{elem_type}</code>[]"
                elif field_type_str == 'enum':
                    type_str = f"<a href=\"#enum-{field.get('enum', '?')}\">{field.get('enum', '?')}</a>"
                else:
                    ty = field.get('type', 'N/A')
                    if ty in schema_data.get('complex_types', {}).keys():
                        ty = f"<a href=\"#complex-type-{ty}\">{ty}</a>"
                    elif ty in schema_data.get('primitives', {}).keys():
                        ty = f"<a href=\"#primitive-{ty}\">{ty}</a>"
                    type_str = f"<code>{ty}</code>"
                
                count_str = "1"
                if 'count' in field:
                    count_str = str(field['count'])
                elif 'count_from' in field:
                    count_str = f"from <code>{html.escape(field['count_from'])}</code>"
                elif field_type_str == 'array':
                     if 'count' not in field and 'count_from' not in field:
                         count_str = "N/A"
                
                desc_str = field.get('description', '')

                sub_table.write("<tr>")
                sub_table.write(f"<td><code>{html.escape(field_name)}</code></td>")
                sub_table.write(f"<td>{type_str}</td>")
                sub_table.write(f"<td><code>{html.escape(count_str)}</code></td>")
                sub_table.write(f"<td>{desc_str}</td>")
                sub_table.write("</tr>")

        sub_table.write("</tbody></table>")
        sub_table_str = sub_table.getvalue()
        stream.write(f"{sub_table_str} |\n")
        
    return stream.getvalue()

def generate_levels_table(schema_data, data):
    """Generates a table for the 'levels' section."""
    stream = io.StringIO()
    stream.write("| Name | Handled By |\n")
    stream.write("| --- | --- |\n")
    for level in data:
        stream.write(f"| `{level.get('name')}` | `{level.get('handled_by')}` |\n")
    return stream.getvalue()

def generate_blocks_table(schema_data, data):
    """Generates a table for the 'blocks' section with HTML sub-tables."""
    stream = io.StringIO()
    stream.write("| Name | Block Type | Payload / Variants | Dispatch |\n")
    stream.write("| --- | --- | --- | --- |\n")
    
    for block in data:
        name = block.get('name', 'N/A')
        block_type = block.get('block_type', 'N/A')
        
        if name == 'MetaData':
            # Special handling for MetaData block
            prefix_html = build_fields_table_html(schema_data, block.get('prefix'), title="Prefix")
            payload_html = (
                f"{prefix_html}"
                "<p style=\"margin-top: 10px;\">"
                "<i>See the <b>MetaData Blocks</b> table below for individual command variants.</i>"
                "</p>"
            )
            dispatch_html = "N/A (See <b>MetaData Blocks</b> table)"
        else:
            # Standard handling for all other blocks
            payload_html = build_payload_html(schema_data, block.get('payload'))
            dispatch_html = build_dispatch_html(block.get('dispatch'))
        
        # Write the main table row
        stream.write(
            f"| **{name}** | `{block_type}` "
            f"| {payload_html} "
            f"| {dispatch_html} |\n"
        )
    return stream.getvalue()

def generate_metadata_blocks_table(schema_data, variants_data):
    """Generates a table for the MetaData variants, treating each like a block."""
    stream = io.StringIO()
    stream.write("| Name (MetaDataType) | Payload | Dispatch |\n")
    stream.write("| --- | --- | --- |\n")

    for variant in variants_data:
        name = variant.get('meta_data_type', 'N/A')
        
        # Generate HTML for payload and dispatch cells
        payload_html = build_fields_table_html(schema_data, variant.get('payload'))
        dispatch_html = build_dispatch_html(variant.get('dispatch'))
        
        # Write the main table row
        stream.write(
            f"| **`{name}`** "
            f"| {payload_html} "
            f"| {dispatch_html} |\n"
        )
    return stream.getvalue()

def generate_documentation(schema_data):
    """Generates the full Markdown documentation string from the parsed schema."""
    stream = io.StringIO()
    
    # schema_name = schema_data.get('schema', {}).get('name', 'Schema')
    # schema_version = schema_data.get('schema', {}).get('version', '')
    # stream.write(f"# {schema_name.capitalize()} Schema Documentation (v{schema_version})\n\n")
    stream.write('# GFXReconstruct Schema Documentation\n\n')

    generators = {
        'block_header': ("Universal block framing definition", generate_block_header_table),
        'blocks': ("Block Payloads", generate_blocks_table),
        #'schema': ("Schema Properties", generate_key_value_table),
        'external_enums': ("External Enums", generate_external_enums_table),
        'primitives': ("Primitives", generate_primitives_table),
        'field_kinds': ("Special Field Kinds", generate_field_kinds_table),
        'complex_types': ("Complex Types", generate_complex_types_table),
        'levels': ("Decoding Levels", generate_levels_table),
    }

    stream.write('''This file documents the existing block types in GFXReconstruct as of 10/2025.
This file is manually maintained for now, and so may be out of date with respect to what currently exists in the source code.
''')

    stream.write("## Index\n\n")
    for key, (title, _) in generators.items():
        stream.write(f"- [{title}](#{title.lower().replace(' ', '-')})\n")

    # Find MetaData variants before looping
    metadata_block = next((b for b in schema_data.get('blocks', []) if b.get('name') == 'MetaData'), None)
    metadata_variants = metadata_block.get('variants', []) if metadata_block else []

    # Generate all standard sections
    for key, (title, func) in generators.items():
        if key in schema_data:
            stream.write(f"## {title}\n\n")
            stream.write(func(schema_data, schema_data[key]))
            stream.write("\n\n---\n\n")
            
    # Manually generate the new MetaData Blocks section at the end
    if metadata_variants:
        stream.write(f"## MetaData Blocks\n\n")
        stream.write(
            "This table details the specific payload and dispatch logic for each "
            "`MetaDataType` variant within the main `MetaData` block.\n\n"
        )
        stream.write(generate_metadata_blocks_table(schema_data, metadata_variants))
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
    markdown_content = generate_documentation(schema_data)

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