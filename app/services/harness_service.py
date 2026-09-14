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
import math
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
        method_name: Optional[str] = None,
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
                return HarnessService._default_python_harness(assembled, method_name)
            return assembled

        # 2. Built-in Language-Specific Harnesses
        if lang in ("cpp", "c++"):
            return HarnessService._default_cpp_harness(user_code, method_name)
        elif lang in ("python", "py", "python3"):
            return HarnessService._default_python_harness(user_code, method_name)
        elif lang in ("java",):
            return HarnessService._default_java_harness(user_code, method_name)
        elif lang in ("javascript", "js"):
            return HarnessService._default_js_harness(user_code, method_name)

        # Fallback: return raw code if no wrapper applies
        return user_code

    # ==========================================
    # C++ HARNESS GENERATOR
    # ==========================================
    @staticmethod
    def _default_cpp_harness(user_code: str, method_name: Optional[str] = None) -> str:
        """
        Parses the C++ Solution class method signature, injects type deserializers,
        and generates a main() loop that calls the user's function for each testcase.
        """
        # If user already provided main(), run as standalone script
        if "int main(" in user_code or "main(" in user_code:
            return user_code

        # Extract method signature from `class Solution`
        # Matches: [return_type] [method_name]([params])
        match = None
        if method_name:
            target_pattern = re.compile(
                r'([a-zA-Z0-9_:<>*&]+(?:\s+[a-zA-Z0-9_:<>*&]+)?)\s+(' + re.escape(method_name) + r')\s*\(([^)]*)\)\s*\{',
                re.MULTILINE
            )
            match = target_pattern.search(user_code)

        if not match:
            method_pattern = re.compile(
                r'([a-zA-Z0-9_:<>*&]+(?:\s+[a-zA-Z0-9_:<>*&]+)?)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*\{',
                re.MULTILINE
            )
            match = method_pattern.search(user_code)

        call_generation = ""
        if match:
            return_type = match.group(1).strip()
            # FIX: Strip C++ visibility specifiers or qualifiers like 'public:', 'virtual', 'inline'
            return_type = re.sub(r'^(?:public|private|protected)\s*:\s*', '', return_type).strip()
            return_type = re.sub(r'^(?:virtual|inline|static)\s+', '', return_type).strip()
            method_name = match.group(2).strip()
            params_raw = match.group(3).strip()

            params = HarnessService._split_cpp_params(params_raw)
            arg_names = []
            arg_readers = []

            for idx, p in enumerate(params):
                p_clean = p.strip()
                parts = p_clean.rsplit(None, 1)
                # FIX (Bug 3 - C++ fallback parser producing type-mismatched variables):
                # When parameter type cannot be split cleanly, default to auto so type deduction matches.
                p_type = parts[0].replace("&", "").strip() if len(parts) > 1 else "auto"
                arg_name = f"arg{idx}"
                arg_names.append(arg_name)

                # Select parser based on C++ type
                # FIX (Bug 3 - C++ type parser coverage): Added long long, char, float, vector<long long> parsers.
                if "vector<vector<int>>" in p_type:
                    parser_fn = "parseMatrixInt"
                elif "vector<int>" in p_type:
                    parser_fn = "parseVectorInt"
                elif "vector<string>" in p_type:
                    parser_fn = "parseVectorString"
                elif "vector<long long>" in p_type or "vector<long>" in p_type:
                    parser_fn = "parseVectorLong"
                elif "string" in p_type:
                    parser_fn = "parseString"
                elif "bool" in p_type:
                    parser_fn = "parseBool"
                elif "double" in p_type:
                    parser_fn = "parseDouble"
                elif "float" in p_type:
                    parser_fn = "parseFloat"
                elif "long long" in p_type or "long" in p_type:
                    parser_fn = "parseLongLong"
                elif "char" in p_type:
                    parser_fn = "parseChar"
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

            # FIX (Bug 4 - C++ zero-argument void methods crashing generator):
            # Guard against IndexError when method has return_type == "void" and 0 arguments (arg_names is empty).
            if return_type == "void":
                if arg_names:
                    exec_call = f"        solver.{method_name}({args_pass});\n        printResult({arg_names[0]});"
                else:
                    exec_call = f'        solver.{method_name}();\n        cout << "null";'
            else:
                exec_call = f"        auto result = solver.{method_name}({args_pass});\n        printResult(result);"

            call_generation = f"""{readers_block}
{exec_call}"""
        else:
            # FIX (Bug 1 - C++ stdin desync on unmatched method signature):
            # When method signature fails to match, drain all remaining lines for this testcase block
            # until TESTCASE_DELIMITER or EOF so that subsequent testcases don't read leftover lines.
            call_generation = f"""        while (cin.peek() != EOF && line != "{TESTCASE_DELIMITER}") {{
            getline(cin, line);
            if (line == "{TESTCASE_DELIMITER}") break;
        }}
        cout << "Error: Method signature not matched";"""

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

long long parseLongLong(const string& s) {{
    try {{ return stoll(s); }} catch(...) {{ return 0LL; }}
}}

double parseDouble(const string& s) {{
    try {{ return stod(s); }} catch(...) {{ return 0.0; }}
}}

float parseFloat(const string& s) {{
    try {{ return stof(s); }} catch(...) {{ return 0.0f; }}
}}

bool parseBool(const string& s) {{
    return s == "true" || s == "1";
}}

char parseChar(string s) {{
    if (s.size() >= 2 && s.front() == '\'' && s.back() == '\'') return s[1];
    if (s.size() >= 2 && s.front() == '"' && s.back() == '"') return s[1];
    return s.empty() ? ' ' : s[0];
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

vector<long long> parseVectorLong(const string& s) {{
    vector<long long> res;
    stringstream ss(s);
    char c; long long n;
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
void printResult(float val) {{ cout << val; }}
void printResult(bool val) {{ cout << (val ? "true" : "false"); }}
void printResult(char val) {{ cout << "'" << val << "'"; }}
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
    def _default_python_harness(user_code: str, method_name: Optional[str] = None) -> str:
        """
        Wraps Python Solution class with dynamic method dispatcher
        reading testcases from stdin separated by TESTCASE_DELIMITER.
        """
        if "class Solution" not in user_code and "def " not in user_code:
            return user_code

        target_method_literal = f'"{method_name}"' if method_name else "None"

        driver = f'''from __future__ import annotations
# System headers & standard LeetCode imports
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
    # FIX (Bug 8 - Python boolean literal parsing case-sensitivity):
    # json.loads fails on title-cased "True" / "False". Parse booleans case-insensitively before fallback.
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False

    try:
        return json.loads(raw)
    except Exception:
        # Fallback to ast.literal_eval to safely parse Python literals like (1, 2) or [True, False]
        import ast
        try:
            return ast.literal_eval(raw)
        except Exception:
            pass
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

    target_method = {target_method_literal}
    solve_fn = None
    if "Solution" in globals() and isinstance(globals()["Solution"], type):
        try:
            solver = Solution()
            if target_method and hasattr(solver, target_method) and callable(getattr(solver, target_method)):
                solve_fn = getattr(solver, target_method)
            else:
                methods = [m for m in dir(solver) if not m.startswith("_") and callable(getattr(solver, m))]
                if methods:
                    solve_fn = getattr(solver, methods[0])
        except Exception:
            pass

    if solve_fn is None and target_method and target_method in globals() and callable(globals()[target_method]):
        solve_fn = globals()[target_method]

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
            # FIX (Bug 5 - Python tuple return values not JSON-serialized):
            # Include tuple in serialization check so tuples are serialized as JSON arrays rather than str() "(1, 2)".
            if isinstance(res, (list, dict, bool, tuple)):
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
    def _default_java_harness(user_code: str, method_name: Optional[str] = None) -> str:
        """
        Wraps Java Solution class in Main class with standard deserializers and testcase loop.
        """
        match = None
        if method_name:
            target_pattern = re.compile(
                r'(?:public\s+|protected\s+)?(?:static\s+|final\s+)?([\w\[\]<>]+)\s+(' + re.escape(method_name) + r')\s*\(([^)]*)\)\s*\{',
                re.MULTILINE
            )
            match = target_pattern.search(user_code)

        if not match:
            method_pattern = re.compile(
                r'(?:public\s+|protected\s+)?(?:static\s+|final\s+)?([\w\[\]<>]+)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*\{',
                re.MULTILINE
            )
            match = method_pattern.search(user_code)

        readers_block = ""
        exec_call = ""

        if match:
            return_type = match.group(1).strip()
            method_name = match.group(2).strip()
            params_raw = match.group(3).strip()

            # FIX (Bug 2 - Java naive comma-split breaking generic parameters):
            # Use bracket-aware splitter _split_cpp_params so parameters like Map<String, Integer> aren't split on inner commas.
            params = HarnessService._split_cpp_params(params_raw)
            arg_names = []
            arg_readers = []

            for idx, p in enumerate(params):
                parts = p.rsplit(None, 1)
                p_type = parts[0].strip() if len(parts) > 1 else "String"
                arg_name = f"arg{idx}"
                arg_names.append(arg_name)

                # FIX (Bug 3 - Java fallback parser producing type-mismatched/wrong-typed variables):
                # Added support for long, float, char, String[], List<Integer>, List<String>.
                # If unknown, fall back to String and parseString to avoid type mismatch declarations.
                if "int[][]" in p_type:
                    parser_fn = "parse2DIntArray"
                elif "int[]" in p_type:
                    parser_fn = "parseIntArray"
                elif "long[]" in p_type:
                    parser_fn = "parseLongArray"
                elif "String[]" in p_type:
                    parser_fn = "parseStringArray"
                elif "List<Integer>" in p_type or "List<int>" in p_type:
                    parser_fn = "parseListInt"
                elif "List<String>" in p_type:
                    parser_fn = "parseListString"
                elif "String" in p_type:
                    parser_fn = "parseString"
                elif "boolean" in p_type or "Boolean" in p_type:
                    parser_fn = "Boolean.parseBoolean"
                elif "long" in p_type or "Long" in p_type:
                    parser_fn = "Long.parseLong"
                elif "int" in p_type or "Integer" in p_type:
                    parser_fn = "Integer.parseInt"
                elif "double" in p_type or "Double" in p_type:
                    parser_fn = "Double.parseDouble"
                elif "float" in p_type or "Float" in p_type:
                    parser_fn = "Float.parseFloat"
                elif "char" in p_type or "Character" in p_type:
                    parser_fn = "parseChar"
                else:
                    parser_fn = "parseString"
                    p_type = "String"

                if idx == 0:
                    arg_readers.append(f"            {p_type} {arg_name} = {parser_fn}(line);")
                else:
                    arg_readers.append(f"            line = reader.readLine();\n            {p_type} {arg_name} = {parser_fn}(line);")

            readers_block = "\n".join(arg_readers)
            args_pass = ", ".join(arg_names)

            # FIX (Bug 4 - Java zero-argument void methods crashing generator):
            # Guard against IndexError when method has return_type == "void" and 0 arguments (arg_names is empty).
            if return_type == "void":
                if arg_names:
                    exec_call = f"            solver.{method_name}({args_pass});\n            printResult({arg_names[0]});"
                else:
                    exec_call = f'            solver.{method_name}();\n            System.out.print("null");'
            else:
                exec_call = f"            var result = solver.{method_name}({args_pass});\n            printResult(result);"
        else:
            # FIX (Bug 1 - Java stdin desync on unmatched method signature):
            # Drain remaining lines for this testcase block until delimiter or EOF so subsequent testcases don't desync.
            readers_block = f"""            while ((line = reader.readLine()) != null) {{
                if (line.trim().equals("{TESTCASE_DELIMITER}")) break;
            }}"""
            exec_call = '            System.out.print("Error: Method signature not matched");'

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

    static long[] parseLongArray(String s) {{
        s = s.replaceAll("[\\[\\]\\\\s]", "");
        if (s.isEmpty()) return new long[0];
        String[] parts = s.split(",");
        long[] res = new long[parts.length];
        for (int i = 0; i < parts.length; i++) res[i] = Long.parseLong(parts[i]);
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

    static String[] parseStringArray(String s) {{
        s = s.trim();
        if (s.startsWith("[") && s.endsWith("]")) s = s.substring(1, s.length() - 1).trim();
        if (s.isEmpty()) return new String[0];
        List<String> list = new ArrayList<>();
        boolean inStr = false;
        StringBuilder cur = new StringBuilder();
        for (int i = 0; i < s.length(); i++) {{
            char c = s.charAt(i);
            if (c == '"') {{
                if (inStr) {{ list.add(cur.toString()); cur.setLength(0); }}
                inStr = !inStr;
            }} else if (inStr) {{
                cur.append(c);
            }}
        }}
        return list.toArray(new String[0]);
    }}

    static char parseChar(String s) {{
        s = s.trim();
        if (s.startsWith("'") && s.endsWith("'") && s.length() >= 3) return s.charAt(1);
        if (s.startsWith("\\"") && s.endsWith("\\"")) return s.substring(1, s.length() - 1).charAt(0);
        return s.isEmpty() ? ' ' : s.charAt(0);
    }}

    static List<Integer> parseListInt(String s) {{
        int[] arr = parseIntArray(s);
        List<Integer> list = new ArrayList<>();
        for (int v : arr) list.add(v);
        return list;
    }}

    static List<String> parseListString(String s) {{
        return Arrays.asList(parseStringArray(s));
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
    def _default_js_harness(user_code: str, method_name: Optional[str] = None) -> str:
        """
        Wraps JavaScript Solution with dynamic Node.js fs reader and JSON parser.
        Supports both `var solve = function(...)` and `class Solution`.
        """
        target_name_literal = f'"{method_name}"' if method_name else "null"

        # FIX (Bug 6 - JavaScript user code embedded unsanitized in template literals):
        # Extract candidate function name in Python via regex instead of embedding raw user_code in a JS template literal.
        fn_match = re.search(r'(?:var|let|const|function)\s+([a-zA-Z_$][\w$]*)', user_code)
        fallback_fn_name = f'"{fn_match.group(1)}"' if fn_match else "null"

        driver = f"""const fs = require('fs');

// === 1. USER SOLUTION ===
{user_code}

// === 2. HIDDEN LEETCODE HARNESS ===
function _runHarness() {{
    const rawInput = fs.readFileSync(0, 'utf-8');
    if (!rawInput.trim()) return;

    let solveFn = null;
    let context = null;
    const targetMethod = {target_name_literal};

    // 1. Check if class Solution exists
    if (typeof Solution === 'function') {{
        try {{
            const inst = new Solution();
            if (targetMethod && typeof inst[targetMethod] === 'function') {{
                solveFn = inst[targetMethod];
                context = inst;
            }} else {{
                const methods = Object.getOwnPropertyNames(Solution.prototype).filter(m => m !== 'constructor');
                if (methods.length > 0) {{
                    solveFn = inst[methods[0]];
                    context = inst;
                }}
            }}
        }} catch(e) {{}}
    }}

    // 2. Check global function (e.g. targetMethod or var largestOverlap = function(...))
    if (!solveFn && targetMethod) {{
        try {{
            const candidate = eval(targetMethod);
            if (typeof candidate === 'function') solveFn = candidate;
        }} catch(e) {{}}
    }}

    // FIX (Bug 6 - Safe function resolution without template literal string interpolation):
    if (!solveFn) {{
        const fallbackName = {fallback_fn_name};
        if (fallbackName) {{
            try {{
                const candidate = eval(fallbackName);
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
        """Compare actual output against expected output with JSON normalization and float tolerance."""
        if actual == expected:
            return True

        if actual.strip().lower() == expected.strip().lower():
            return True

        # Helper for approximate float comparison in nested JSON structures
        def _approx_equal(a: Any, b: Any, tol: float = 1e-5) -> bool:
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                return math.isclose(a, b, rel_tol=tol, abs_tol=tol)
            if isinstance(a, list) and isinstance(b, list):
                if len(a) != len(b):
                    return False
                return all(_approx_equal(x, y, tol) for x, y in zip(a, b))
            if isinstance(a, dict) and isinstance(b, dict):
                if a.keys() != b.keys():
                    return False
                return all(_approx_equal(a[k], b[k], tol) for k in a)
            return a == b

        # Try JSON comparison (handles [0, 1] == [0,1], [[0]] == [[0]], and nested floats)
        try:
            act_obj = json.loads(actual)
            exp_obj = json.loads(expected)
            if _approx_equal(act_obj, exp_obj):
                return True
        except Exception:
            pass

        # FIX (Bug 7 - _outputs_match: add floating-point tolerance):
        # Support scalar float/double comparisons with tolerance (e.g. 0.50000 vs 0.5 or 3.1415926 vs 3.14159)
        try:
            act_f = float(actual.strip())
            exp_f = float(expected.strip())
            if math.isclose(act_f, exp_f, rel_tol=1e-5, abs_tol=1e-5):
                return True
        except (ValueError, TypeError, OverflowError):
            pass

        return False

    @staticmethod
    def truncate_text(text: Optional[str], max_len: int = 1000) -> str:
        """Truncate long string to avoid browser overload on massive testcase inputs."""
        if not text:
            return ""
        if len(text) <= max_len:
            return text
        return text[:max_len] + f"... (truncated, total {len(text)} chars)"

    @staticmethod
    def extract_first_failure(
        parsed_results: List[Dict[str, Any]],
        inputs: List[str],
        expected_outputs: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Identify the first failed test case with input, expected, and actual values."""
        for idx, item in enumerate(parsed_results):
            if not item.get("passed"):
                inp = inputs[idx] if idx < len(inputs) else ""
                exp = expected_outputs[idx] if idx < len(expected_outputs) else ""
                act = item.get("actual", "")
                return {
                    "test_case_number": idx + 1,
                    "total_test_cases": len(parsed_results),
                    "input": HarnessService.truncate_text(inp),
                    "expected_output": HarnessService.truncate_text(exp),
                    "actual_output": HarnessService.truncate_text(act),
                }
        return None


harness_service = HarnessService()
