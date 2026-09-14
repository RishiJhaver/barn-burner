"""LeetCode-style Test Harness Service.

Stitches user algorithm code into hidden driver wrappers and batches multiple
test cases into a single Judge0 execution run for:
- C++ (class Solution with automatic signature parsing & deserialization)
- Python (class Solution with dynamic method dispatcher)
- Java (class Solution with Main class driver and array/matrix parsers)
- JavaScript (var function or class Solution with Node.js fs runner)
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TESTCASE_DELIMITER = "===TESTCASE_BOUNDARY==="
OUTPUT_DELIMITER = "===OUTPUT_BOUNDARY==="


class HarnessService:
    """Code assembly and multi-testcase batching service."""

    @staticmethod
    def assemble_code(
        language: str,
        user_code: str,
        custom_driver: Optional[str] = None,
    ) -> str:
        """
        Stitch user's Solution code with driver harness.
        Uses custom_driver if provided; otherwise generates an authentic language-specific harness.
        """
        lang = language.lower()

        # 1. Custom Driver Code with Placeholder
        if custom_driver:
            assembled = custom_driver
            for placeholder in [
                "// {{USER_CODE}}",
                "# {{USER_CODE}}",
                "/* {{USER_CODE}} */",
                "{{USER_CODE}}",
            ]:
                if placeholder in assembled:
                    assembled = assembled.replace(placeholder, user_code)
                    break
            else:
                assembled = f"{user_code}\n\n{custom_driver}"

            # If custom driver doesn't contain an active print/output loop, wrap with harness
            if lang in ("python", "py", "python3") and "print(" not in custom_driver and "sys.stdout" not in custom_driver:
                return HarnessService._default_python_harness(assembled)
            return assembled

        # 2. Built-in Language-Specific Harnesses
        if lang in ("cpp", "c++"):
            return HarnessService._default_cpp_harness(user_code)
        elif lang in ("python", "py", "python3"):
            return HarnessService._default_python_harness(user_code)
        elif lang in ("java",):
            return HarnessService._default_java_harness(user_code)
        elif lang in ("javascript", "js"):
            return HarnessService._default_js_harness(user_code)

        # Fallback: return raw code if no wrapper applies
        return user_code

    # ==========================================
    # C++ HARNESS GENERATOR
    # ==========================================
    @staticmethod
    def _default_cpp_harness(user_code: str) -> str:
        """
        Parses the C++ Solution class method signature, injects type deserializers,
        and generates a main() loop that calls the user's function for each testcase.
        """
        # If user already provided main(), run as standalone script
        if "int main(" in user_code or "main(" in user_code:
            return user_code

        # Extract method signature from `class Solution`
        # Matches: [return_type] [method_name]([params])
        method_pattern = re.compile(
            r'([a-zA-Z0-9_:<>*&]+(?:\s+[a-zA-Z0-9_:<>*&]+)?)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*\{',
            re.MULTILINE
        )
        match = method_pattern.search(user_code)

        call_generation = ""
        if match:
            return_type = match.group(1).strip()
            method_name = match.group(2).strip()
            params_raw = match.group(3).strip()

            params = HarnessService._split_cpp_params(params_raw)
            arg_names = []
            arg_readers = []

            for idx, p in enumerate(params):
                p_clean = p.strip()
                # e.g. "vector<vector<int>>& img1" -> type: "vector<vector<int>>", name: "img1"
                parts = p_clean.rsplit(None, 1)
                p_type = parts[0].replace("&", "").strip() if len(parts) > 1 else "string"
                arg_name = f"arg{idx}"
                arg_names.append(arg_name)

                # Select parser based on C++ type
                if "vector<vector<int>>" in p_type:
                    parser_fn = "parseMatrixInt"
                elif "vector<int>" in p_type:
                    parser_fn = "parseVectorInt"
                elif "vector<string>" in p_type:
                    parser_fn = "parseVectorString"
                elif "string" in p_type:
                    parser_fn = "parseString"
                elif "bool" in p_type:
                    parser_fn = "parseBool"
                elif "double" in p_type or "float" in p_type:
                    parser_fn = "parseDouble"
                elif "int" in p_type:
                    parser_fn = "parseInt"
                else:
                    parser_fn = "parseString"

                if idx == 0:
                    arg_readers.append(f"        auto {arg_name} = {parser_fn}(line);")
                else:
                    arg_readers.append(f"        getline(cin, line);\n        auto {arg_name} = {parser_fn}(line);")

            args_pass = ", ".join(arg_names)
            readers_block = "\n".join(arg_readers)

            if return_type == "void":
                exec_call = f"        solver.{method_name}({args_pass});\n        printResult({arg_names[0]});"
            else:
                exec_call = f"        auto result = solver.{method_name}({args_pass});\n        printResult(result);"

            call_generation = f"""{readers_block}
{exec_call}"""
        else:
            # Fallback if regex couldn't match method
            call_generation = "        cout << \"Compiled successfully\";"

        driver = f"""#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>
#include <map>
#include <set>
#include <unordered_map>
#include <unordered_set>
#include <queue>
#include <stack>
#include <cmath>
using namespace std;

// === 1. BUILT-IN C++ DESERIALIZERS & PRINTERS ===
int parseInt(const string& s) {{
    try {{ return stoi(s); }} catch(...) {{ return 0; }}
}}

double parseDouble(const string& s) {{
    try {{ return stod(s); }} catch(...) {{ return 0.0; }}
}}

bool parseBool(const string& s) {{
    return s == "true" || s == "1";
}}

string parseString(string s) {{
    if (s.size() >= 2 && s.front() == '"' && s.back() == '"') {{
        return s.substr(1, s.size() - 2);
    }}
    return s;
}}

vector<int> parseVectorInt(const string& s) {{
    vector<int> res;
    stringstream ss(s);
    char c; int n;
    while (ss >> c) {{
        if (isdigit(c) || c == '-') {{
            ss.putback(c);
            ss >> n;
            res.push_back(n);
        }}
    }}
    return res;
}}

vector<string> parseVectorString(const string& s) {{
    vector<string> res;
    bool in_str = false;
    string cur = "";
    for (char c : s) {{
        if (c == '"') {{
            if (in_str) {{ res.push_back(cur); cur = ""; }}
            in_str = !in_str;
        }} else if (in_str) {{
            cur += c;
        }}
    }}
    return res;
}}

vector<vector<int>> parseMatrixInt(const string& s) {{
    vector<vector<int>> mat;
    vector<int> row;
    int n = 0; bool in_num = false, neg = false;
    for (size_t i = 1; i + 1 < s.size(); i++) {{
        char c = s[i];
        if (c == '[') {{ row.clear(); }}
        else if (c == ']') {{
            if (in_num) {{ row.push_back(neg ? -n : n); in_num = false; neg = false; n = 0; }}
            mat.push_back(row);
        }} else if (c == '-') {{ neg = true; }}
        else if (isdigit(c)) {{ n = n * 10 + (c - '0'); in_num = true; }}
        else if (c == ',' && in_num) {{
            row.push_back(neg ? -n : n); in_num = false; neg = false; n = 0;
        }}
    }}
    return mat;
}}

// Overloaded generic printers
void printResult(int val) {{ cout << val; }}
void printResult(long long val) {{ cout << val; }}
void printResult(double val) {{ cout << val; }}
void printResult(bool val) {{ cout << (val ? "true" : "false"); }}
void printResult(const string& val) {{ cout << "\\"" << val << "\\""; }}

template<typename T>
void printResult(const vector<T>& vec) {{
    cout << "[";
    for (size_t i = 0; i < vec.size(); i++) {{
        printResult(vec[i]);
        if (i + 1 < vec.size()) cout << ",";
    }}
    cout << "]";
}}

// === 2. USER SOLUTION ===
{user_code}

// === 3. HIDDEN TEST HARNESS ===
int main() {{
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    Solution solver;
    string line;

    while (getline(cin, line)) {{
        if (line.empty() || line == "{TESTCASE_DELIMITER}") continue;
{call_generation}
        cout << "\\n{OUTPUT_DELIMITER}\\n";
    }}
    return 0;
}}
"""
        return driver

    @staticmethod
    def _split_cpp_params(params_str: str) -> List[str]:
        """Split parameter list respecting template brackets <...>."""
        params = []
        cur = []
        depth = 0
        for char in params_str:
            if char == '<':
                depth += 1
            elif char == '>':
                depth -= 1
            elif char == ',' and depth == 0:
                params.append("".join(cur).strip())
                cur = []
                continue
            cur.append(char)
        if cur:
            params.append("".join(cur).strip())
        return [p for p in params if p]

    # ==========================================
    # PYTHON HARNESS GENERATOR
    # ==========================================
    @staticmethod
    def _default_python_harness(user_code: str) -> str:
        """
        Wraps Python Solution class with dynamic method dispatcher
        reading testcases from stdin separated by TESTCASE_DELIMITER.
        """
        if "class Solution" not in user_code and "def " not in user_code:
            return user_code

        driver = f'''# System headers & standard LeetCode imports
import sys
import json
import math
import collections
import heapq
import bisect
from typing import *

# === USER SOLUTION ===
{user_code}

# === HIDDEN LEETCODE HARNESS ===
def _parse_arg(raw: str):
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        if raw.isdigit() or (raw.startswith('-') and raw[1:].isdigit()):
            return int(raw)
        try:
            return float(raw)
        except ValueError:
            return raw

def _run_harness():
    raw_input_data = sys.stdin.read()
    if not raw_input_data:
        return

    test_blocks = [
        b.strip() for b in raw_input_data.split("{TESTCASE_DELIMITER}")
        if b.strip()
    ]
    if not test_blocks and raw_input_data.strip():
        test_blocks = [raw_input_data.strip()]

    solve_fn = None
    if "Solution" in globals() and isinstance(globals()["Solution"], type):
        try:
            solver = Solution()
            methods = [m for m in dir(solver) if not m.startswith("_") and callable(getattr(solver, m))]
            if methods:
                solve_fn = getattr(solver, methods[0])
        except Exception:
            pass

    if solve_fn is None:
        if "solution" in globals() and callable(globals()["solution"]):
            solve_fn = globals()["solution"]
        else:
            candidates = [
                obj for name, obj in globals().items()
                if callable(obj) and not name.startswith("_")
                and name not in ("Solution", "math", "json", "sys", "collections", "heapq", "bisect", "inspect")
            ]
            if candidates:
                solve_fn = candidates[0]

    if solve_fn is None:
        return

    import inspect
    sig = None
    try:
        sig = inspect.signature(solve_fn)
    except Exception:
        pass

    for block in test_blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        args = [_parse_arg(line) for line in lines]

        # If single line with multiple space-separated arguments (e.g. "1 2" or "2 3")
        if len(args) == 1 and isinstance(args[0], str) and " " in args[0] and sig and len(sig.parameters) > 1:
            tokens = [t.strip() for t in args[0].split() if t.strip()]
            args = [_parse_arg(t) for t in tokens]

        try:
            res = solve_fn(*args)
            if isinstance(res, (list, dict, bool)):
                output_str = json.dumps(res, separators=(',', ':'))
            else:
                output_str = str(res)
            print(output_str)
        except Exception as exc:
            print(f"Error: {{exc}}")
        print("{OUTPUT_DELIMITER}")

if __name__ == "__main__":
    _run_harness()
'''
        return driver

    # ==========================================
    # JAVA HARNESS GENERATOR
    # ==========================================
    @staticmethod
    def _default_java_harness(user_code: str) -> str:
        """
        Wraps Java Solution class in Main class with standard deserializers and testcase loop.
        """
        # Parse method signature from Java Solution
        method_pattern = re.compile(
            r'public\s+([\w\[\]<>]+)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*\{',
            re.MULTILINE
        )
        match = method_pattern.search(user_code)

        readers_block = ""
        exec_call = ""

        if match:
            return_type = match.group(1).strip()
            method_name = match.group(2).strip()
            params_raw = match.group(3).strip()

            params = [p.strip() for p in params_raw.split(",") if p.strip()]
            arg_names = []
            arg_readers = []

            for idx, p in enumerate(params):
                parts = p.rsplit(None, 1)
                p_type = parts[0].strip() if len(parts) > 1 else "String"
                arg_name = f"arg{idx}"
                arg_names.append(arg_name)

                if "int[][]" in p_type:
                    parser_fn = "parse2DIntArray"
                elif "int[]" in p_type:
                    parser_fn = "parseIntArray"
                elif "String[]" in p_type:
                    parser_fn = "parseStringArray"
                elif "String" in p_type:
                    parser_fn = "parseString"
                elif "boolean" in p_type:
                    parser_fn = "Boolean.parseBoolean"
                elif "int" in p_type:
                    parser_fn = "Integer.parseInt"
                elif "double" in p_type:
                    parser_fn = "Double.parseDouble"
                else:
                    parser_fn = "parseString"

                if idx == 0:
                    arg_readers.append(f"            {p_type} {arg_name} = {parser_fn}(line);")
                else:
                    arg_readers.append(f"            line = reader.readLine();\n            {p_type} {arg_name} = {parser_fn}(line);")

            readers_block = "\n".join(arg_readers)
            args_pass = ", ".join(arg_names)

            if return_type == "void":
                exec_call = f"            solver.{method_name}({args_pass});\n            printResult({arg_names[0]});"
            else:
                exec_call = f"            var result = solver.{method_name}({args_pass});\n            printResult(result);"

        driver = f"""import java.io.*;
import java.util.*;

// === 1. USER SOLUTION ===
{user_code}

// === 2. HIDDEN LEETCODE HARNESS ===
public class Main {{
    public static void main(String[] args) throws Exception {{
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
        Solution solver = new Solution();
        String line;

        while ((line = reader.readLine()) != null) {{
            line = line.trim();
            if (line.isEmpty() || line.equals("{TESTCASE_DELIMITER}")) continue;
{readers_block}
{exec_call}
            System.out.println("\\n{OUTPUT_DELIMITER}");
        }}
    }}

    // Deserializers
    static int[] parseIntArray(String s) {{
        s = s.replaceAll("[\\[\\]\\\\s]", "");
        if (s.isEmpty()) return new int[0];
        String[] parts = s.split(",");
        int[] res = new int[parts.length];
        for (int i = 0; i < parts.length; i++) res[i] = Integer.parseInt(parts[i]);
        return res;
    }}

    static int[][] parse2DIntArray(String s) {{
        s = s.trim();
        if (s.equals("[]")) return new int[0][0];
        List<int[]> list = new ArrayList<>();
        int start = -1;
        for (int i = 1; i < s.length() - 1; i++) {{
            if (s.charAt(i) == '[') start = i;
            else if (s.charAt(i) == ']') {{
                list.add(parseIntArray(s.substring(start, i + 1)));
            }}
        }}
        return list.toArray(new int[list.size()][]);
    }}

    static String parseString(String s) {{
        if (s.startsWith("\\"") && s.endsWith("\\"")) return s.substring(1, s.length() - 1);
        return s;
    }}

    static void printResult(Object obj) {{
        if (obj instanceof int[][]) {{
            System.out.print(Arrays.deepToString((int[][]) obj).replace(" ", ""));
        }} else if (obj instanceof int[]) {{
            System.out.print(Arrays.toString((int[]) obj).replace(" ", ""));
        }} else {{
            System.out.print(obj);
        }}
    }}
}}
"""
        return driver

    # ==========================================
    # JAVASCRIPT HARNESS GENERATOR
    # ==========================================
    @staticmethod
    def _default_js_harness(user_code: str) -> str:
        """
        Wraps JavaScript Solution with dynamic Node.js fs reader and JSON parser.
        Supports both `var solve = function(...)` and `class Solution`.
        """
        driver = f"""const fs = require('fs');

// === 1. USER SOLUTION ===
{user_code}

// === 2. HIDDEN LEETCODE HARNESS ===
function _runHarness() {{
    const rawInput = fs.readFileSync(0, 'utf-8');
    if (!rawInput.trim()) return;

    let solveFn = null;
    let context = null;

    // 1. Check if class Solution exists
    if (typeof Solution === 'function') {{
        try {{
            const inst = new Solution();
            const methods = Object.getOwnPropertyNames(Solution.prototype).filter(m => m !== 'constructor');
            if (methods.length > 0) {{
                solveFn = inst[methods[0]];
                context = inst;
            }}
        }} catch(e) {{}}
    }}

    // 2. Check global function (e.g. var largestOverlap = function(...) or function largestOverlap(...))
    if (!solveFn) {{
        const fnMatch = `{user_code}`.match(/(?:var|let|const|function)\\s+([a-zA-Z_$][\\w$]*)/);
        if (fnMatch) {{
            const fnName = fnMatch[1];
            try {{
                const candidate = eval(fnName);
                if (typeof candidate === 'function') solveFn = candidate;
            }} catch(e) {{}}
        }}
    }}

    if (!solveFn) return;

    const testBlocks = rawInput.split('{TESTCASE_DELIMITER}').map(b => b.trim()).filter(Boolean);
    const blocksToRun = testBlocks.length > 0 ? testBlocks : [rawInput.trim()];

    for (const block of blocksToRun) {{
        const lines = block.split('\\n').map(l => l.trim()).filter(Boolean);
        const args = lines.map(l => {{
            try {{ return JSON.parse(l); }} catch(e) {{ return l; }}
        }});

        try {{
            const res = solveFn.apply(context, args);
            console.log(JSON.stringify(res));
        }} catch(err) {{
            console.log("Error: " + err.message);
        }}
        console.log("{OUTPUT_DELIMITER}");
    }}
}}

_runHarness();
"""
        return driver

    # ==========================================
    # BATCHING & OUTPUT VERIFICATION
    # ==========================================
    @staticmethod
    def batch_inputs(test_cases: List[str]) -> str:
        """
        Concatenates all testcase inputs into a single batched stdin stream
        separated by TESTCASE_DELIMITER.
        """
        cleaned = [tc.strip() for tc in test_cases if tc is not None]
        return f"\n{TESTCASE_DELIMITER}\n".join(cleaned)

    @staticmethod
    def parse_outputs(
        stdout: str,
        expected_outputs: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Splits single batched stdout using OUTPUT_DELIMITER and matches
        against expected test case outputs.
        """
        if OUTPUT_DELIMITER in stdout:
            actual_chunks = [
                c.strip() for c in stdout.split(OUTPUT_DELIMITER)
                if c.strip() != ""
            ]
        else:
            actual_chunks = [c.strip() for c in stdout.splitlines() if c.strip() != ""]

        results = []
        for idx, expected in enumerate(expected_outputs):
            exp_clean = expected.strip() if expected else ""
            act_clean = actual_chunks[idx] if idx < len(actual_chunks) else ""

            passed = HarnessService._outputs_match(act_clean, exp_clean)

            results.append({
                "index": idx + 1,
                "passed": passed,
                "actual": act_clean,
                "expected": exp_clean,
            })

        return results

    @staticmethod
    def _outputs_match(actual: str, expected: str) -> bool:
        """Compare actual output against expected output with JSON normalization."""
        if actual == expected:
            return True

        if actual.strip().lower() == expected.strip().lower():
            return True

        # Try JSON comparison (handles [0, 1] == [0,1], [[0]] == [[0]])
        try:
            return json.loads(actual) == json.loads(expected)
        except Exception:
            pass

        return False


harness_service = HarnessService()
