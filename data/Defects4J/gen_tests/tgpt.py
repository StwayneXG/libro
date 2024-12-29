import javalang
import os
import pandas as pd

def _find_body(code_snippet, start_position):
    lines = code_snippet.split('\n')
    current_line = start_position[0] - 1
    current_column = start_position[1] - 1
    total_open_braces = 0
    brace_count = 0
    in_string = False
    in_char = False
    in_block_comment = False
    escape_next = False
    body_lines = []

    while current_line < len(lines):
        line = lines[current_line]
        i = current_column if current_line == start_position[0] - 1 else 0
        in_line_comment = False

        while i < len(line):
            char = line[i]

            if escape_next:
                escape_next = False
            elif char == '\\':
                escape_next = True
            elif in_string:
                if char == '"':
                    in_string = False
            elif in_char:
                if char == "'":
                    in_char = False
            elif in_line_comment:
                pass
            elif in_block_comment:
                if char == '*' and i + 1 < len(line) and line[i + 1] == '/':
                    in_block_comment = False
                    i += 1
            else:
                if char == '"':
                    in_string = True
                elif char == "'":
                    in_char = True
                elif char == '/' and i + 1 < len(line):
                    if line[i + 1] == '/':
                        in_line_comment = True
                        i += 1
                    elif line[i + 1] == '*':
                        in_block_comment = True
                        i += 1
                elif char == '{':
                    total_open_braces += 1
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and total_open_braces != 0:
                        body_lines.append(line[:i + 1])
                        return '\n'.join(body_lines)

            i += 1

        body_lines.append(line)
        current_line += 1
        current_column = 0

    return '\n'.join(body_lines)

def clean_packages_imports(code_snippet):
    code_lines = code_snippet.split('\n')
    code_lines = [line for line in code_lines if not line.startswith('package')]
    code_lines = [line for line in code_lines if not line.startswith('import')]
    return '\n'.join(code_lines)

def extract_code(code_snippet):
    try:
        code_snippet = clean_packages_imports(code_snippet)
        # if there is already a wrapper, we extract all the code from the inside
        tree = javalang.parse.parse(code_snippet)

        # Extracting the code snippet from the biggest wrapper class
        for path, node in tree:
            if isinstance(node, javalang.tree.ClassDeclaration):
                body = _find_body(code_snippet, node.position)
                body = body.split('{', 1)[1].rsplit('}', 1)[0].strip()
                return body
    except Exception as e:
        # Otherwise, we return the code snippet as is because it is going directly in the test class
        return code_snippet
    return code_snippet


def main():
    experiment = "gpt-4o_openbook_rephrased"
    df = pd.read_csv(f"{experiment}_generatedtestcases.csv")
    df = df.fillna('[]')
    df['Generated Testcases'] = df['Generated Testcases'].apply(eval)
    os.makedirs(f"{experiment}", exist_ok=True)

    for i, row in df.iterrows():
        project = row['Project']
        bug_number = row['Bug Number']
        testcases = row['Generated Testcases']

        for j, testcase in enumerate(testcases):
            code_snippet = extract_code(testcase)
            with open(f"{experiment}/{project}_{bug_number}_n{j}.txt", "w", errors='ignore') as f:
                f.write(code_snippet)

if __name__ == "__main__":
    main()