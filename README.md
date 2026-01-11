# 房间布局优化器

基于 shapely 库的 Python 项目，用于解决房间内物体的自动布局问题。

## AI 工具使用说明

本项目在开发过程中使用了 **Cursor** AI 编程助手。

### 使用的 AI 工具
- **Cursor**: 用于代码生成、调试和优化

### AI 主要帮助的部分
1. **思路拆解**: AI 帮助将复杂的几何布局问题拆解为可实现的步骤
2. **代码生成**: 协助生成几何计算、碰撞检测等核心算法代码
3. **Debug**: 帮助定位和修复几何计算中的浮点精度问题、边界条件处理等bug
4. **代码优化**: 优化搜索算法和碰撞检测逻辑

### 关键逻辑的个人理解与调整
1. **贴墙搜索算法**: 通过遍历所有墙面，计算法线方向，使用投影计算确保物体精确贴墙（间距为0）
2. **法向偏移计算**: 通过计算物体顶点在法线方向上的投影，精确计算物体中心到墙面的偏移距离
3. **冰箱开门禁区处理**: 理解双开门逻辑，实现矩形禁区（宽度=length，深度=length/2）的正确创建和碰撞检测
4. **内开门 N×N 避让区**: 实现以门线为一条边的 N×N 正方形避让区的正确创建
5. **自由放置策略**: 在贴墙放置失败后，添加网格搜索的自由放置备选方案

## 功能特性

1. **几何碰撞检测**：使用 shapely 库实现精确的几何碰撞检测
2. **内开门避让区**：考虑内开门会占据 N×N 的避让区
3. **冰箱开门禁区**：为冰箱开门侧生成矩形禁区，确保该区域不被占用
4. **贴墙放置**：优先将物体贴着墙边放置
5. **旋转支持**：物体可以旋转 0°、90°、180°、270°，但必须与墙面平行或垂直

## 项目结构

```
room-layout-optimizer/
├── data/              # 输入数据文件（JSON格式）
│   ├── example1.json
│   ├── example2.json
│   ├── example3.json
│   └── example4.json
├── src/               # 源代码目录
│   ├── utils.py       # 几何工具函数
│   ├── sovler.py      # LayoutSolver 类（布局求解器）
│   └── main.py        # 主程序入口
├── output/            # 输出结果目录
├── venv/              # Python 虚拟环境
└── README.md          # 本文件
```

## 运行环境

- Python 3.7+
- shapely 库
- numpy（shapely 的依赖）
- matplotlib（用于可视化，可选）

## 安装依赖

### 方式一：使用 requirements.txt（推荐）

```bash
# 在项目根目录下
pip install -r requirements.txt
```

### 方式二：手动安装

```bash
pip install shapely numpy matplotlib
```

### 方式三：使用虚拟环境（推荐）

```bash
# 创建虚拟环境（如果还没有）
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 运行方式

### 运行主程序

**方式一：使用默认文件（example1.json）**

```bash
# 在项目根目录下
python src/main.py
```

**方式二：指定输入文件**

```bash
# 在项目根目录下
python src/main.py data/example2.json
```

**方式三：从 src 目录运行**

```bash
cd src
python main.py ../data/example2.json
```

### 查看结果

程序运行后会：
1. 在控制台打印布局结果
2. 将结果保存到 `output/` 目录下的 JSON 文件

### 可视化结果（可选）

```bash
# 在项目根目录下
python src/visualize.py data/example2.json
```

## 输入数据格式

JSON 文件格式如下：

```json
{
    "boundary": [
        [x1, y1], [x2, y2], ..., [xN, yN]
    ],
    "door": [[x1, y1], [x2, y2]],
    "isOpenInward": false,
    "algoToPlace": {
        "fridge": [length, width],
        "shelf-1": [length, width],
        "shelf-2": [length, width],
        ...
    }
}
```

字段说明：
- `boundary`: 房间边界点列表（多边形顶点，首尾相连）
- `door`: 门的两端点坐标
- `isOpenInward`: 是否为内开门（true/false）
- `algoToPlace`: 待摆放物体字典，键为物体名称，值为 [长度, 宽度]

## 输出结果格式

```json
{
    "item_name": {
        "center": [x, y],
        "rotation": 0,
        "placed": true
    },
    ...
}
```

或如果无法放置：

```json
{
    "item_name": {
        "placed": false,
        "error": "无法找到有效位置"
    }
}
```

## 使用示例

### 示例 1：基本使用

```python
import json
from src.sovler import LayoutSolver

# 加载数据
with open('data/example1.json', 'r') as f:
    data = json.load(f)

# 创建求解器
solver = LayoutSolver(data)

# 求解布局
results = solver.solve()

# 打印结果
for item_name, result in results.items():
    if result['placed']:
        print(f"{item_name}: 中心点 {result['center']}, 旋转 {result['rotation']}°")
    else:
        print(f"{item_name}: 无法放置")

# 检查是否可行
if solver.is_feasible():
    print("所有物体都已成功放置！")
```

### 示例 2：单独放置一个物体

```python
from src.sovler import LayoutSolver
import json

with open('data/example1.json', 'r') as f:
    data = json.load(f)

solver = LayoutSolver(data)

# 放置单个物体
placement = solver.find_position('fridge', 1220, 1330)
if placement:
    print(f"找到位置: {placement['center']}, 旋转: {placement['rotation']}°")
else:
    print("无法找到位置")
```

## 核心代码实现逻辑

### 功能实现：贴墙搜索与法向偏移

本项目的核心算法通过**贴墙搜索**和**法向偏移**解决了冰箱开门禁区等硬性约束问题。

#### 1. 贴墙搜索算法

**核心思想**：遍历房间的所有墙面，尝试将物体贴着墙边放置。

**实现步骤**：
1. **墙面遍历**：提取房间边界的所有线段作为墙面
2. **角度计算**：对每个墙面，计算其角度，尝试物体与墙面平行（0°）或垂直（90°）
3. **法线方向计算**：
   - 计算墙面的方向向量 `(dx, dy)`
   - 计算垂直于墙面的法线向量 `(-dy, dx)`，指向房间内部
   - 验证法线方向是否正确（通过测试点是否在房间内）
4. **沿墙搜索**：
   - 计算物体沿墙方向的长度
   - 沿墙面步进搜索，生成多个候选位置
   - 对每个位置进行碰撞检测

#### 2. 法向偏移计算

**核心思想**：通过计算物体顶点在法线方向上的投影，精确计算物体中心到墙面的偏移距离，确保物体的一条边与墙面重合（间距为0）。

**实现步骤**：
1. **投影计算**：
   ```python
   # 获取物体的所有顶点
   coords = list(test_poly_temp.exterior.coords[:-1])
   # 计算每个顶点在法线方向上的投影（点积）
   projections = [px * nx + py * ny for px, py in coords]
   min_proj = min(projections)  # 最靠近墙的顶点投影
   ```
2. **偏移距离计算**：
   ```python
   # 物体中心到最近边的距离（绝对值）
   offset_distance = -min_proj  # 因为物体中心在原点，min_proj是负值
   ```
3. **位置计算**：
   ```python
   # 将物体中心向内偏移，使物体的一条边与墙面重合（间距为0）
   center = (base_x + nx * offset_distance, base_y + ny * offset_distance)
   ```

#### 3. 冰箱开门禁区处理

**硬性约束**：冰箱的 length 边为开门边，双开门从中间向两边打开，半径为 length/2。开门边前方不能放置任何物体。

**实现方法**：
1. **禁区创建**：
   - 禁区为矩形：宽度 = length（整个开门边），深度 = length/2（开门半径）
   - 在局部坐标系中创建禁区矩形，然后旋转和平移到世界坐标系
2. **碰撞检测**：
   - 在 `is_valid_position()` 中检查：
     - 物体本身不能与冰箱开门禁区重叠
     - 其他物体的开门禁区不能与已放置物体重叠
     - 开门禁区不能与门禁区重叠

#### 4. 内开门 N×N 避让区

**硬性约束**：内开门会占据 N×N 的空间（N为门宽）。

**实现方法**：
- 使用 `create_door_avoidance_zone()` 创建以门线为一条边的 N×N 正方形避让区
- 避让区位于门的内侧（房间内）
- 在碰撞检测中严格检查，不允许任何重叠

#### 5. 自由放置备选策略

如果贴墙放置失败，算法会尝试自由放置：
- 在房间内生成网格点
- 尝试 0°、90°、180°、270° 四个角度
- 检查每个候选位置是否满足所有约束条件

### 代码模块说明

#### utils.py

包含几何工具函数：
- `create_room_polygon()`: 创建房间多边形
- `create_door_avoidance_zone()`: 创建内开门 N×N 避让区
- `create_fridge_door_zone()`: 创建冰箱开门禁区
- `calculate_door_width()`: 计算门宽

#### sovler.py

包含 `LayoutSolver` 类：
- `__init__()`: 初始化，加载房间数据和待放置物体，创建门禁区
- `_get_wall_segments()`: 获取所有墙面线段
- `create_item_poly()`: 创建物体矩形多边形（支持旋转）
- `get_fridge_zones()`: 创建冰箱本体和开门禁区
- `is_valid_position()`: 多重碰撞检测（房间边界、门禁区、物体重叠、冰箱开门禁区）
- `_try_free_placement()`: 自由放置（不贴墙）的备选策略
- `solve()`: 求解所有物体的布局（优先贴墙，失败则尝试自由放置）
- `is_feasible()`: 检查布局是否可行

#### main.py

主程序入口，提供命令行接口，加载数据、运行求解器、保存结果。

## 注意事项

1. 确保虚拟环境已激活
2. 输入文件路径可以是相对路径或绝对路径
3. 物体名称以 "fridge" 开头的会被识别为冰箱，会生成开门禁区
4. 程序会优先尝试贴墙放置，如果无法贴墙放置，会返回失败
5. 物体只能旋转 0°、90°、180°、270°，必须与墙面平行或垂直

## 故障排除

### 问题：ModuleNotFoundError: No module named 'shapely'

**解决**：确保虚拟环境已激活，并且 shapely 已安装

```bash
source venv/bin/activate
pip install shapely
```

### 问题：找不到输入文件

**解决**：检查文件路径是否正确，可以使用绝对路径或相对于项目根目录的路径

### 问题：某些物体无法放置

**解决**：
- 检查房间空间是否足够
- 检查是否有足够的墙边空间
- 尝试调整物体的尺寸或数量
