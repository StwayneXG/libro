import javalang
import os
import pandas as pd

# Given a code snippet, you need to extract methods from it

def wrapper(code_snippet):
    code_snippet_lines = code_snippet.split('\n')
    code_snippet_lines = [line if not line.startswith('import ') and not line.startswith('package ') else '' for line in code_snippet_lines]
    code_snippet = '\n'.join(code_snippet_lines)
    if ' class ' in code_snippet:
        pass
    else:
        code_snippet = f"class Dummy {{\n{code_snippet}\n}}"
    return code_snippet


def _find_method_body(code_snippet, start_position):
    lines = code_snippet.split('\n')
    current_line = start_position[0] - 1
    current_column = start_position[1] - 1
    total_open_braces = 0
    brace_count = 0
    in_string = False
    in_char = False
    in_block_comment = False
    escape_next = False
    method_lines = []

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
                        method_lines.append(line[:i + 1])
                        return '\n'.join(method_lines)

            i += 1

        method_lines.append(line)
        current_line += 1
        current_column = 0

    return '\n'.join(method_lines)

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
            code_snippet = wrapper(testcase)
            try:
                tree = javalang.parse.parse(code_snippet)
            except:
                with open(f"{experiment}/{project}_{bug_number}_n{j}.txt", "w", errors='ignore') as f:
                    f.write(testcase)
                continue

            class_codes = []
            for path, node in tree:
                if isinstance(node, javalang.tree.ClassDeclaration):
                    class_code = _find_method_body(code_snippet, node.position)
                    class_code = class_code.split('{', 1)[1].rsplit('}', 1)[0].strip()

                    in_code = False
                    for c_c in class_codes:
                        if class_code in c_c:
                            in_code = True
                            break

                    if not in_code:
                        class_codes.append(class_code)

            test_code = "\n\n".join(class_codes)

            # method_codes = []
            # for path, node in tree:
            #     if isinstance(node, javalang.tree.MethodDeclaration):
            #         method_code = _find_method_body(code_snippet, node.position)
            #         decorators = [annotation.name for annotation in node.annotations]
            #         # Remove 'Test' from decorators
            #         decorators = [d for d in decorators if d != 'Test']
            #         in_code = False
            #         for m_c in method_codes:
            #             if method_code in m_c:
            #                 in_code = True
            #                 break
            #         if not in_code:
            #             decorator_code = ""
            #             for decorator in decorators:
            #                 decorator_code += f"@{decorator}\n"
            #             method_code = f"{decorator_code}{method_code}"
            #             method_codes.append(method_code)

            # test_code = "\n\n".join(method_codes)
            with open(f"{experiment}/{project}_{bug_number}_n{j}.txt", "w", errors='ignore') as f:
                f.write(test_code)
        #     break
        # break

            # with open(f"{experiment}/{project}_{bug_number}_n{j}.txt", "w", errors='ignore') as f:
            #     f.write(testcase)



if __name__ == "__main__":
    main()