import os
import sys
import pytest

# Ensure executor is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "executor")))

from main import execute_code, ExecutionRequest, TestCase


# ==============================================================================
# 1. Primitives: int, long, double, bool, string
# ==============================================================================

def test_primitives_python():
    code = """
def check_primitives(a: int, b: int, c: float, flag: bool, s: str):
    if flag:
        return f"{s}_{a + b}_{c:.2f}"
    return "disabled"
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="check_primitives",
        tests=[
            TestCase(args=[5, 9000000000, 3.14159, True, "val"], expected="val_9000000005_3.14"),
            TestCase(args=[1, 2, 0.0, False, "test"], expected="disabled"),
        ],
        type_hints=["int", "long", "double", "bool", "string"],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.all_passed is True


def test_primitives_java():
    code = """
public class Solution {
    public String checkPrimitives(int a, long b, double c, boolean flag, String s) {
        if (flag) {
            return String.format("%s_%d_%.2f", s, (a + b), c);
        }
        return "disabled";
    }
}
"""
    req = ExecutionRequest(
        language="java",
        code=code,
        function_name="checkPrimitives",
        tests=[
            TestCase(args=[5, 9000000000, 3.14159, True, "val"], expected="val_9000000005_3.14"),
            TestCase(args=[1, 2, 0.0, False, "test"], expected="disabled"),
        ],
        type_hints=["int", "long", "double", "bool", "string"],
    )
    res = execute_code(req)
    assert res.status == "success", f"Java primitives failed: {res.compile_error or res.error}"
    assert res.all_passed is True


def test_primitives_cpp():
    code = """
#include <string>
#include <sstream>
#include <iomanip>

class Solution {
public:
    std::string checkPrimitives(int a, long long b, double c, bool flag, std::string s) {
        if (flag) {
            std::ostringstream ss;
            ss << s << "_" << (a + b) << "_" << std::fixed << std::setprecision(2) << c;
            return ss.str();
        }
        return "disabled";
    }
};
"""
    req = ExecutionRequest(
        language="cpp",
        code=code,
        function_name="checkPrimitives",
        tests=[
            TestCase(args=[5, 9000000000, 3.14159, True, "val"], expected="val_9000000005_3.14"),
            TestCase(args=[1, 2, 0.0, False, "test"], expected="disabled"),
        ],
        type_hints=["int", "long", "double", "bool", "string"],
    )
    res = execute_code(req)
    assert res.status == "success", f"C++ primitives failed: {res.compile_error or res.error}"
    assert res.all_passed is True


# ==============================================================================
# 2. 1D / 2D Arrays: int[], int[][], string[]
# ==============================================================================

def test_arrays_python():
    code = """
def matrix_row_sums(matrix, words):
    sums = [sum(row) for row in matrix]
    prefix = "-".join(words)
    return [f"{prefix}:{s}" for s in sums]
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="matrix_row_sums",
        tests=[
            TestCase(
                args=[[[1, 2, 3], [4, 5, 6]], ["alpha", "beta"]],
                expected=["alpha-beta:6", "alpha-beta:15"],
            )
        ],
        type_hints=["int[][]", "string[]"],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.all_passed is True


def test_arrays_java():
    code = """
public class Solution {
    public String[] matrixRowSums(int[][] matrix, String[] words) {
        String prefix = String.join("-", words);
        String[] res = new String[matrix.length];
        for (int i = 0; i < matrix.length; i++) {
            int sum = 0;
            for (int val : matrix[i]) sum += val;
            res[i] = prefix + ":" + sum;
        }
        return res;
    }
}
"""
    req = ExecutionRequest(
        language="java",
        code=code,
        function_name="matrixRowSums",
        tests=[
            TestCase(
                args=[[[1, 2, 3], [4, 5, 6]], ["alpha", "beta"]],
                expected=["alpha-beta:6", "alpha-beta:15"],
            )
        ],
        type_hints=["int[][]", "string[]"],
    )
    res = execute_code(req)
    assert res.status == "success", f"Java arrays failed: {res.compile_error or res.error}"
    assert res.all_passed is True


def test_arrays_cpp():
    code = """
#include <vector>
#include <string>
#include <numeric>

class Solution {
public:
    std::vector<std::string> matrixRowSums(std::vector<std::vector<int>>& matrix, std::vector<std::string>& words) {
        std::string prefix = "";
        for (size_t i = 0; i < words.size(); ++i) {
            if (i > 0) prefix += "-";
            prefix += words[i];
        }
        std::vector<std::string> res;
        for (const auto& row : matrix) {
            int sum = std::accumulate(row.begin(), row.end(), 0);
            res.push_back(prefix + ":" + std::to_string(sum));
        }
        return res;
    }
};
"""
    req = ExecutionRequest(
        language="cpp",
        code=code,
        function_name="matrixRowSums",
        tests=[
            TestCase(
                args=[[[1, 2, 3], [4, 5, 6]], ["alpha", "beta"]],
                expected=["alpha-beta:6", "alpha-beta:15"],
            )
        ],
        type_hints=["int[][]", "string[]"],
    )
    res = execute_code(req)
    assert res.status == "success", f"C++ arrays failed: {res.compile_error or res.error}"
    assert res.all_passed is True


# ==============================================================================
# 3. Linked Lists: ListNode (Singly-linked, cyclic-safe serialization)
# ==============================================================================

def test_linked_list_reverse_python():
    code = """
def reverseList(head):
    prev = None
    curr = head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="reverseList",
        tests=[
            TestCase(args=[[1, 2, 3, 4, 5]], expected=[5, 4, 3, 2, 1]),
            TestCase(args=[[]], expected=[]),
        ],
        type_hints=["ListNode"],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.all_passed is True


def test_linked_list_reverse_java():
    code = """
public class Solution {
    public ListNode reverseList(ListNode head) {
        ListNode prev = null;
        ListNode curr = head;
        while (curr != null) {
            ListNode nxt = curr.next;
            curr.next = prev;
            prev = curr;
            curr = nxt;
        }
        return prev;
    }
}
"""
    req = ExecutionRequest(
        language="java",
        code=code,
        function_name="reverseList",
        tests=[
            TestCase(args=[[1, 2, 3, 4, 5]], expected=[5, 4, 3, 2, 1]),
            TestCase(args=[[]], expected=[]),
        ],
        type_hints=["ListNode"],
    )
    res = execute_code(req)
    assert res.status == "success", f"Java ListNode failed: {res.compile_error or res.error}"
    assert res.all_passed is True


def test_linked_list_reverse_cpp():
    code = """
class Solution {
public:
    ListNode* reverseList(ListNode* head) {
        ListNode* prev = nullptr;
        ListNode* curr = head;
        while (curr != nullptr) {
            ListNode* nxt = curr->next;
            curr->next = prev;
            prev = curr;
            curr = nxt;
        }
        return prev;
    }
};
"""
    req = ExecutionRequest(
        language="cpp",
        code=code,
        function_name="reverseList",
        tests=[
            TestCase(args=[[1, 2, 3, 4, 5]], expected=[5, 4, 3, 2, 1]),
            TestCase(args=[[]], expected=[]),
        ],
        type_hints=["ListNode"],
    )
    res = execute_code(req)
    assert res.status == "success", f"C++ ListNode failed: {res.compile_error or res.error}"
    assert res.all_passed is True


# ==============================================================================
# 4. Binary Trees: TreeNode (BFS level-order with nulls)
# ==============================================================================

def test_tree_max_depth_python():
    code = """
def maxDepth(root):
    if not root:
        return 0
    return 1 + max(maxDepth(root.left), maxDepth(root.right))
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="maxDepth",
        tests=[
            TestCase(args=[[3, 9, 20, None, None, 15, 7]], expected=3),
            TestCase(args=[[1, None, 2]], expected=2),
            TestCase(args=[[]], expected=0),
        ],
        type_hints=["TreeNode"],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.all_passed is True


def test_tree_max_depth_java():
    code = """
public class Solution {
    public int maxDepth(TreeNode root) {
        if (root == null) return 0;
        return 1 + Math.max(maxDepth(root.left), maxDepth(root.right));
    }
}
"""
    req = ExecutionRequest(
        language="java",
        code=code,
        function_name="maxDepth",
        tests=[
            TestCase(args=[[3, 9, 20, None, None, 15, 7]], expected=3),
            TestCase(args=[[1, None, 2]], expected=2),
            TestCase(args=[[]], expected=0),
        ],
        type_hints=["TreeNode"],
    )
    res = execute_code(req)
    assert res.status == "success", f"Java TreeNode failed: {res.compile_error or res.error}"
    assert res.all_passed is True


def test_tree_max_depth_cpp():
    code = """
#include <algorithm>

class Solution {
public:
    int maxDepth(TreeNode* root) {
        if (!root) return 0;
        return 1 + std::max(maxDepth(root->left), maxDepth(root->right));
    }
};
"""
    req = ExecutionRequest(
        language="cpp",
        code=code,
        function_name="maxDepth",
        tests=[
            TestCase(args=[[3, 9, 20, None, None, 15, 7]], expected=3),
            TestCase(args=[[1, None, 2]], expected=2),
            TestCase(args=[[]], expected=0),
        ],
        type_hints=["TreeNode"],
    )
    res = execute_code(req)
    assert res.status == "success", f"C++ TreeNode failed: {res.compile_error or res.error}"
    assert res.all_passed is True


# ==============================================================================
# 5. Graphs: int n, int[][] edges (adjacency list traversal)
# ==============================================================================

def test_graph_reachable_python():
    code = """
from collections import defaultdict, deque

def countReachable(n, edges, start):
    adj = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    visited = {start}
    q = deque([start])
    while q:
        curr = q.popleft()
        for nei in adj[curr]:
            if nei not in visited:
                visited.add(nei)
                q.append(nei)
    return len(visited)
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="countReachable",
        tests=[
            TestCase(args=[5, [[0, 1], [0, 2], [1, 2], [3, 4]], 0], expected=3),
            TestCase(args=[4, [[0, 1], [1, 2], [2, 3]], 0], expected=4),
        ],
        type_hints=["int", "int[][]", "int"],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.all_passed is True


def test_graph_reachable_java():
    code = """
import java.util.*;

public class Solution {
    public int countReachable(int n, int[][] edges, int start) {
        Map<Integer, List<Integer>> adj = new HashMap<>();
        for (int i = 0; i < n; i++) adj.put(i, new ArrayList<>());
        for (int[] e : edges) {
            adj.get(e[0]).add(e[1]);
            adj.get(e[1]).add(e[0]);
        }
        Set<Integer> visited = new HashSet<>();
        Queue<Integer> q = new LinkedList<>();
        visited.add(start);
        q.add(start);
        while (!q.isEmpty()) {
            int curr = q.poll();
            for (int nei : adj.get(curr)) {
                if (!visited.contains(nei)) {
                    visited.add(nei);
                    q.add(nei);
                }
            }
        }
        return visited.size();
    }
}
"""
    req = ExecutionRequest(
        language="java",
        code=code,
        function_name="countReachable",
        tests=[
            TestCase(args=[5, [[0, 1], [0, 2], [1, 2], [3, 4]], 0], expected=3),
            TestCase(args=[4, [[0, 1], [1, 2], [2, 3]], 0], expected=4),
        ],
        type_hints=["int", "int[][]", "int"],
    )
    res = execute_code(req)
    assert res.status == "success", f"Java Graph failed: {res.compile_error or res.error}"
    assert res.all_passed is True


def test_graph_reachable_cpp():
    code = """
#include <vector>
#include <queue>
#include <unordered_set>

class Solution {
public:
    int countReachable(int n, std::vector<std::vector<int>>& edges, int start) {
        std::vector<std::vector<int>> adj(n);
        for (const auto& e : edges) {
            adj[e[0]].push_back(e[1]);
            adj[e[1]].push_back(e[0]);
        }
        std::unordered_set<int> visited;
        std::queue<int> q;
        visited.insert(start);
        q.push(start);
        while (!q.empty()) {
            int curr = q.front();
            q.pop();
            for (int nei : adj[curr]) {
                if (!visited.count(nei)) {
                    visited.insert(nei);
                    q.push(nei);
                }
            }
        }
        return visited.size();
    }
};
"""
    req = ExecutionRequest(
        language="cpp",
        code=code,
        function_name="countReachable",
        tests=[
            TestCase(args=[5, [[0, 1], [0, 2], [1, 2], [3, 4]], 0], expected=3),
            TestCase(args=[4, [[0, 1], [1, 2], [2, 3]], 0], expected=4),
        ],
        type_hints=["int", "int[][]", "int"],
    )
    res = execute_code(req)
    assert res.status == "success", f"C++ Graph failed: {res.compile_error or res.error}"
    assert res.all_passed is True


# ==============================================================================
# 6. In-place modification problems: sortColors (mutates input array in-place)
# ==============================================================================

def test_inplace_sort_colors_python():
    code = """
def sortColors(nums):
    # Dutch National Flag Algorithm
    p0, curr, p2 = 0, 0, len(nums) - 1
    while curr <= p2:
        if nums[curr] == 0:
            nums[p0], nums[curr] = nums[curr], nums[p0]
            p0 += 1
            curr += 1
        elif nums[curr] == 2:
            nums[curr], nums[p2] = nums[p2], nums[curr]
            p2 -= 1
        else:
            curr += 1
"""
    req = ExecutionRequest(
        language="python",
        code=code,
        function_name="sortColors",
        tests=[
            TestCase(args=[[2, 0, 2, 1, 1, 0]], expected=[0, 0, 1, 1, 2, 2]),
            TestCase(args=[[2, 0, 1]], expected=[0, 1, 2]),
        ],
        type_hints=["int[]"],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.all_passed is True


def test_inplace_sort_colors_java():
    code = """
public class Solution {
    public void sortColors(int[] nums) {
        int p0 = 0, curr = 0, p2 = nums.length - 1;
        while (curr <= p2) {
            if (nums[curr] == 0) {
                int tmp = nums[p0];
                nums[p0++] = nums[curr];
                nums[curr++] = tmp;
            } else if (nums[curr] == 2) {
                int tmp = nums[p2];
                nums[p2--] = nums[curr];
                nums[curr] = tmp;
            } else {
                curr++;
            }
        }
    }
}
"""
    req = ExecutionRequest(
        language="java",
        code=code,
        function_name="sortColors",
        tests=[
            TestCase(args=[[2, 0, 2, 1, 1, 0]], expected=[0, 0, 1, 1, 2, 2]),
            TestCase(args=[[2, 0, 1]], expected=[0, 1, 2]),
        ],
        type_hints=["int[]"],
    )
    res = execute_code(req)
    assert res.status == "success", f"Java in-place sortColors failed: {res.compile_error or res.error}"
    assert res.all_passed is True


def test_inplace_sort_colors_cpp():
    code = """
#include <vector>
#include <utility>

class Solution {
public:
    void sortColors(std::vector<int>& nums) {
        int p0 = 0, curr = 0, p2 = (int)nums.size() - 1;
        while (curr <= p2) {
            if (nums[curr] == 0) {
                std::swap(nums[p0++], nums[curr++]);
            } else if (nums[curr] == 2) {
                std::swap(nums[curr], nums[p2--]);
            } else {
                curr++;
            }
        }
    }
};
"""
    req = ExecutionRequest(
        language="cpp",
        code=code,
        function_name="sortColors",
        tests=[
            TestCase(args=[[2, 0, 2, 1, 1, 0]], expected=[0, 0, 1, 1, 2, 2]),
            TestCase(args=[[2, 0, 1]], expected=[0, 1, 2]),
        ],
        type_hints=["int[]"],
    )
    res = execute_code(req)
    assert res.status == "success", f"C++ in-place sortColors failed: {res.compile_error or res.error}"
    assert res.all_passed is True


# ==============================================================================
# 7. Custom checkers: exact, unordered, float_tolerance, valid_palindrome
# ==============================================================================

def test_custom_checkers():
    # 1. Unordered checker
    code_py = "def get_elements(): return [4, 1, 3, 2]"
    req_un = ExecutionRequest(
        language="python",
        code=code_py,
        function_name="get_elements",
        tests=[TestCase(args=[], expected=[1, 2, 3, 4])],
        checker="unordered",
    )
    assert execute_code(req_un).all_passed is True

    # 2. Float tolerance checker
    code_fl = "def get_pi(): return 3.14159265"
    req_fl = ExecutionRequest(
        language="python",
        code=code_fl,
        function_name="get_pi",
        tests=[TestCase(args=[], expected=3.14159)],
        checker="float_tolerance(1e-4)",
    )
    assert execute_code(req_fl).all_passed is True

    # 3. Valid palindrome checker
    code_pal = "def make_pal(): return 'A man, a plan, a canal: Panama'"
    req_pal = ExecutionRequest(
        language="python",
        code=code_pal,
        function_name="make_pal",
        tests=[TestCase(args=[], expected="dummy")],
        checker="valid_palindrome",
    )
    assert execute_code(req_pal).all_passed is True


# ==============================================================================
# 8. Security Tests for Java and C++ Runners (Section 7)
# ==============================================================================

def test_java_network_blocked():
    code = """
import java.net.*;

public class Solution {
    public String solution() {
        try {
            Socket s = new Socket();
            s.connect(new InetSocketAddress("8.8.8.8", 53), 1000);
            return "connected";
        } catch (Exception e) {
            return "network_blocked";
        }
    }
}
"""
    req = ExecutionRequest(
        language="java",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected="network_blocked")],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.results[0].actual == "network_blocked"


def test_cpp_network_blocked():
    code = """
#include <string>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

class Solution {
public:
    std::string solution() {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) return "network_blocked";
        sockaddr_in addr;
        addr.sin_family = AF_INET;
        addr.sin_port = htons(53);
        inet_pton(AF_INET, "8.8.8.8", &addr.sin_addr);
        int res = connect(sock, (struct sockaddr*)&addr, sizeof(addr));
        close(sock);
        return (res == 0) ? "connected" : "network_blocked";
    }
};
"""
    req = ExecutionRequest(
        language="cpp",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected="network_blocked")],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.results[0].actual == "network_blocked"


def test_java_infinite_loop_timeout():
    code = """
public class Solution {
    public int solution() {
        while (true) {}
    }
}
"""
    req = ExecutionRequest(
        language="java",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected=1)],
        timeout_seconds=2.0,
    )
    res = execute_code(req)
    assert res.status == "timeout"
    assert res.all_passed is False


def test_cpp_infinite_loop_timeout():
    code = """
class Solution {
public:
    int solution() {
        while (true) {}
    }
};
"""
    req = ExecutionRequest(
        language="cpp",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected=1)],
        timeout_seconds=2.0,
    )
    res = execute_code(req)
    assert res.status == "timeout"
    assert res.all_passed is False


def test_java_filesystem_writes_outside_tmpfs_blocked():
    code = """
import java.io.*;

public class Solution {
    public String solution() {
        try {
            File f = new File("/etc/pwned.txt");
            FileWriter fw = new FileWriter(f);
            fw.write("hacked");
            fw.close();
            return "write_succeeded";
        } catch (Exception e) {
            return "write_prevented";
        }
    }
}
"""
    req = ExecutionRequest(
        language="java",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected="write_prevented")],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.results[0].actual == "write_prevented"


def test_cpp_filesystem_writes_outside_tmpfs_blocked():
    code = """
#include <string>
#include <fstream>

class Solution {
public:
    std::string solution() {
        std::ofstream f("/etc/pwned.txt");
        if (f.is_open()) {
            f << "hacked";
            f.close();
            return "write_succeeded";
        }
        return "write_prevented";
    }
};
"""
    req = ExecutionRequest(
        language="cpp",
        code=code,
        function_name="solution",
        tests=[TestCase(args=[], expected="write_prevented")],
    )
    res = execute_code(req)
    assert res.status == "success"
    assert res.results[0].actual == "write_prevented"
