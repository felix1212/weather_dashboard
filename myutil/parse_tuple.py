import ast

def parse_tuple(input_string):
    try:
        output_tuple = ast.literal_eval(input_string)
        if isinstance(output_tuple, tuple):
            return output_tuple
        else:
            raise ValueError
    except (ValueError, SyntaxError):
        raise ValueError(f"Invalid tuple format: {input_string}")