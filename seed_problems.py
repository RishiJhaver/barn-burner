import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal as async_session_maker
from app.models.problem import Problem
from app.models.tag import Tag
from app.models.template import ProblemTemplate
from app.models.test_case import TestCase
from app.models.enums import ProblemDifficulty

SEED_DATA = [
    {
        "slug": "largest-overlap",
        "title": "Largest Overlap",
        "difficulty": ProblemDifficulty.MEDIUM,
        "published": True,
        "tags": ["Array", "Matrix"],
        "description": """You are given two images, `img1` and `img2`, represented as binary, square matrices of size `n x n`. A translation involves sliding one image left, right, up, or down any number of units, and placing it on top of the other image.

We then calculate the overlap by counting the number of positions that have a `1` in both images. Note that a translation does **not** include any kind of rotation.

Return the **largest possible overlap**.

### Example 1:
**Input:**
```
img1 = [[1,1,0],[0,1,0],[0,1,0]]
img2 = [[0,0,0],[0,1,1],[0,0,1]]
```
**Output:** `3`
**Explanation:** We translate img1 to the right by 1 unit and down by 1 unit. There are 3 positions with 1s in both images.

### Example 2:
**Input:**
```
img1 = [[1]]
img2 = [[1]]
```
**Output:** `1`

### Example 3:
**Input:**
```
img1 = [[1]]
img2 = [[0]]
```
**Output:** `0`

### Constraints:
* `n == img1.length == img1[i].length`
* `n == img2.length == img2[i].length`
* `1 <= n <= 30`
* `img1[i][j]` is either `0` or `1`.
* `img2[i][j]` is either `0` or `1`.
""",
        "templates": [
            {
                "language": "cpp",
                "starter_code": """class Solution {
public:
    int largestOverlap(vector<vector<int>>& img1, vector<vector<int>>& img2) {
        
    }
};
"""
            },
            {
                "language": "python",
                "starter_code": """class Solution:
    def largestOverlap(self, img1: List[List[int]], img2: List[List[int]]) -> int:
        
"""
            },
            {
                "language": "java",
                "starter_code": """class Solution {
    public int largestOverlap(int[][] img1, int[][] img2) {
        
    }
}
"""
            },
            {
                "language": "javascript",
                "starter_code": """/**
 * @param {number[][]} img1
 * @param {number[][]} img2
 * @return {number}
 */
var largestOverlap = function(img1, img2) {
    
};
"""
            }
        ],
        "test_cases": [
            {
                "input": "[[1,1,0],[0,1,0],[0,1,0]]\n[[0,0,0],[0,1,1],[0,0,1]]",
                "expected_output": "3",
                "is_sample": True
            },
            {
                "input": "[[1]]\n[[1]]",
                "expected_output": "1",
                "is_sample": True
            },
            {
                "input": "[[1]]\n[[0]]",
                "expected_output": "0",
                "is_sample": True
            },
            {
                "input": "[[0,0],[0,0]]\n[[1,1],[1,1]]",
                "expected_output": "0",
                "is_sample": False
            }
        ]
    },
    {
        "slug": "two-sum",
        "title": "Two Sum",
        "difficulty": ProblemDifficulty.EASY,
        "published": True,
        "tags": ["Array", "Hash Table"],
        "description": """Given an array of integers `nums` and an integer `target`, return *indices of the two numbers such that they add up to `target`*.

You may assume that each input would have ***exactly* one solution**, and you may not use the same element twice.

You can return the answer in any order.

### Example 1:
**Input:** `nums = [2,7,11,15], target = 9`  
**Output:** `[0,1]`  
**Explanation:** Because nums[0] + nums[1] == 9, we return [0, 1].

### Example 2:
**Input:** `nums = [3,2,4], target = 6`  
**Output:** `[1,2]`

### Example 3:
**Input:** `nums = [3,3], target = 6`  
**Output:** `[0,1]`

### Constraints:
* `2 <= nums.length <= 10^4`
* `-10^9 <= nums[i] <= 10^9`
* `-10^9 <= target <= 10^9`
* **Only one valid answer exists.**
""",
        "templates": [
            {
                "language": "cpp",
                "starter_code": """class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        
    }
};
"""
            },
            {
                "language": "python",
                "starter_code": """class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        
"""
            },
            {
                "language": "java",
                "starter_code": """class Solution {
    public int[] twoSum(int[] nums, int target) {
        
    }
}
"""
            },
            {
                "language": "javascript",
                "starter_code": """/**
 * @param {number[]} nums
 * @param {number} target
 * @return {number[]}
 */
var twoSum = function(nums, target) {
    
};
"""
            }
        ],
        "test_cases": [
            {
                "input": "[2,7,11,15]\n9",
                "expected_output": "[0,1]",
                "is_sample": True
            },
            {
                "input": "[3,2,4]\n6",
                "expected_output": "[1,2]",
                "is_sample": True
            },
            {
                "input": "[3,3]\n6",
                "expected_output": "[0,1]",
                "is_sample": True
            }
        ]
    },
    {
        "slug": "maximum-subarray",
        "title": "Maximum Subarray",
        "difficulty": ProblemDifficulty.MEDIUM,
        "published": True,
        "tags": ["Array", "Dynamic Programming"],
        "description": """Given an integer array `nums`, find the subarray with the largest sum, and return *its sum*.

### Example 1:
**Input:** `nums = [-2,1,-3,4,-1,2,1,-5,4]`  
**Output:** `6`  
**Explanation:** The subarray `[4,-1,2,1]` has the largest sum `6`.

### Example 2:
**Input:** `nums = [1]`  
**Output:** `1`

### Example 3:
**Input:** `nums = [5,4,-1,7,8]`  
**Output:** `23`

### Constraints:
* `1 <= nums.length <= 10^5`
* `-10^4 <= nums[i] <= 10^4`
""",
        "templates": [
            {
                "language": "cpp",
                "starter_code": """class Solution {
public:
    int maxSubArray(vector<int>& nums) {
        
    }
};
"""
            },
            {
                "language": "python",
                "starter_code": """class Solution:
    def maxSubArray(self, nums: List[int]) -> int:
        
"""
            },
            {
                "language": "java",
                "starter_code": """class Solution {
    public int maxSubArray(int[] nums) {
        
    }
}
"""
            },
            {
                "language": "javascript",
                "starter_code": """/**
 * @param {number[]} nums
 * @return {number}
 */
var maxSubArray = function(nums) {
    
};
"""
            }
        ],
        "test_cases": [
            {
                "input": "[-2,1,-3,4,-1,2,1,-5,4]",
                "expected_output": "6",
                "is_sample": True
            },
            {
                "input": "[1]",
                "expected_output": "1",
                "is_sample": True
            },
            {
                "input": "[5,4,-1,7,8]",
                "expected_output": "23",
                "is_sample": True
            }
        ]
    },
    {
        "slug": "trapping-rain-water",
        "title": "Trapping Rain Water",
        "difficulty": ProblemDifficulty.HARD,
        "published": True,
        "tags": ["Array", "Two Pointers", "Dynamic Programming", "Stack"],
        "description": """Given `n` non-negative integers representing an elevation map where the width of each bar is `1`, compute how much water it can trap after raining.

### Example 1:
**Input:** `height = [0,1,0,2,1,0,1,3,2,1,2,1]`  
**Output:** `6`  
**Explanation:** The elevation map traps 6 units of rain water.

### Example 2:
**Input:** `height = [4,2,0,3,2,5]`  
**Output:** `9`

### Constraints:
* `n == height.length`
* `1 <= n <= 2 * 10^4`
* `0 <= height[i] <= 10^5`
""",
        "templates": [
            {
                "language": "cpp",
                "starter_code": """class Solution {
public:
    int trap(vector<int>& height) {
        
    }
};
"""
            },
            {
                "language": "python",
                "starter_code": """class Solution:
    def trap(self, height: List[int]) -> int:
        
"""
            },
            {
                "language": "java",
                "starter_code": """class Solution {
    public int trap(int[] height) {
        
    }
}
"""
            },
            {
                "language": "javascript",
                "starter_code": """/**
 * @param {number[]} height
 * @return {number}
 */
var trap = function(height) {
    
};
"""
            }
        ],
        "test_cases": [
            {
                "input": "[0,1,0,2,1,0,1,3,2,1,2,1]",
                "expected_output": "6",
                "is_sample": True
            },
            {
                "input": "[4,2,0,3,2,5]",
                "expected_output": "9",
                "is_sample": True
            }
        ]
    }
]

async def seed():
    async with async_session_maker() as session:
        # Cache existing tags
        tag_result = await session.execute(select(Tag))
        tag_map = {t.name: t for t in tag_result.scalars().all()}

        for p_data in SEED_DATA:
            # Check if problem exists
            prob_result = await session.execute(
                select(Problem).where(Problem.slug == p_data["slug"])
            )
            problem = prob_result.scalar_one_or_none()

            # Ensure tags exist
            prob_tags = []
            for tag_name in p_data["tags"]:
                if tag_name not in tag_map:
                    new_tag = Tag(name=tag_name, slug=tag_name.lower().replace(" ", "-"))
                    session.add(new_tag)
                    await session.flush()
                    tag_map[tag_name] = new_tag
                prob_tags.append(tag_map[tag_name])

            if not problem:
                problem = Problem(
                    slug=p_data["slug"],
                    title=p_data["title"],
                    description=p_data["description"],
                    difficulty=p_data["difficulty"],
                    published=p_data["published"],
                    tags=prob_tags,
                )
                session.add(problem)
                await session.flush()
                print(f"Created problem: {problem.title} (slug: {problem.slug})")
            else:
                problem.title = p_data["title"]
                problem.description = p_data["description"]
                problem.difficulty = p_data["difficulty"]
                problem.published = p_data["published"]
                problem.tags = prob_tags
                print(f"Updated problem: {problem.title}")

            # Templates
            for tmpl in p_data["templates"]:
                existing_tmpl_res = await session.execute(
                    select(ProblemTemplate).where(
                        ProblemTemplate.problem_id == problem.id,
                        ProblemTemplate.language == tmpl["language"],
                    )
                )
                existing_tmpl = existing_tmpl_res.scalar_one_or_none()
                if not existing_tmpl:
                    session.add(
                        ProblemTemplate(
                            problem_id=problem.id,
                            language=tmpl["language"],
                            starter_code=tmpl["starter_code"],
                        )
                    )
                else:
                    existing_tmpl.starter_code = tmpl["starter_code"]

            # Test Cases
            existing_tc_res = await session.execute(
                select(TestCase).where(TestCase.problem_id == problem.id)
            )
            existing_tc = existing_tc_res.scalars().all()
            if not existing_tc:
                for tc in p_data["test_cases"]:
                    session.add(
                        TestCase(
                            problem_id=problem.id,
                            input=tc["input"],
                            expected_output=tc["expected_output"],
                            is_sample=tc["is_sample"],
                        )
                    )

        await session.commit()
        print("Database successfully seeded with LeetCode problems!")

if __name__ == "__main__":
    asyncio.run(seed())
