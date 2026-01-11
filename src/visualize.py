"""
房间布局可视化工具

使用matplotlib可视化房间边界和摆放后的物体
"""

import json
import sys
import os
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import Polygon, LineString, box
from shapely.affinity import rotate, translate
from utils import (
    create_room_polygon,
    create_door_avoidance_zone,
    create_rectangle,
    create_fridge_door_zone,
    calculate_door_width
)


def load_data(file_path: str) -> dict:
    """加载JSON格式的房间数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def plot_polygon(ax, polygon: Polygon, **kwargs):
    """绘制shapely多边形"""
    x, y = polygon.exterior.xy
    ax.fill(x, y, **kwargs)
    ax.plot(x, y, color=kwargs.get('edgecolor', kwargs.get('color', 'black')), linewidth=1.5)


def visualize_layout(input_file: str, result_file: str = None):
    """
    可视化房间布局
    
    Args:
        input_file: 输入数据文件路径
        result_file: 结果文件路径，如果为None则自动查找
    """
    # 加载输入数据
    data = load_data(input_file)
    
    # 如果没有指定结果文件，自动查找
    if result_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        input_basename = os.path.splitext(os.path.basename(input_file))[0]
        result_file = os.path.join(project_root, 'output', f'{input_basename}_result.json')
    
    # 加载结果数据
    if os.path.exists(result_file):
        with open(result_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
    else:
        print(f"警告: 结果文件 '{result_file}' 不存在，仅绘制房间边界和门")
        results = {}
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # 1. 绘制房间边界
    room_polygon = create_room_polygon(data['boundary'])
    x, y = room_polygon.exterior.xy
    ax.fill(x, y, color='lightgray', edgecolor='black', linewidth=2, alpha=0.3, label='房间边界')
    ax.plot(x, y, color='black', linewidth=2)
    
    # 2. 绘制门
    door_points = data['door']
    door_line = LineString(door_points)
    ax.plot([door_points[0][0], door_points[1][0]], 
            [door_points[0][1], door_points[1][1]], 
            color='red', linewidth=4, label='门')
    
    # 2.5. 绘制门线缓冲区（用于检查物品是否遮挡门）
    from utils import calculate_door_width
    door_width = calculate_door_width(door_points)
    door_buffer = door_line.buffer(door_width / 2)
    x_buffer, y_buffer = door_buffer.exterior.xy
    ax.fill(x_buffer, y_buffer, color='red', edgecolor='darkred', 
            alpha=0.15, linewidth=1, linestyle='--', label='门线缓冲区')
    
    # 3. 绘制门的避让区（如果是内开门）
    is_open_inward = data.get('isOpenInward', False)
    if is_open_inward:
        door_avoidance_zone = create_door_avoidance_zone(
            door_points,
            is_open_inward,
            room_polygon=room_polygon
        )
        if door_avoidance_zone is not None:
            plot_polygon(ax, door_avoidance_zone, 
                        facecolor='red', edgecolor='darkred', 
                        alpha=0.3, label='门的避让区 (N×N)')
    
    # 4. 绘制已放置的物体
    items_to_place = data['algoToPlace']
    colors = {
        'fridge': 'blue',
        'shelf': 'green',
        'overShelf': 'orange',
        'iceMaker': 'purple'
    }
    
    placed_count = 0
    for item_name, item_data in items_to_place.items():
        if item_name in results and results[item_name].get('placed', False):
            placed_count += 1
            result = results[item_name]
            # 确保数值较大的作为length
            dim1, dim2 = item_data
            length = max(dim1, dim2)
            width = min(dim1, dim2)
            center = result['center']
            rotation = result['rotation']
            
            # 创建物体多边形（支持任意角度旋转）
            # 使用与sovler.py相同的方法创建旋转后的矩形
            p = box(-length/2, -width/2, length/2, width/2)
            p = rotate(p, rotation, origin=(0, 0))
            item_polygon = translate(p, center[0], center[1])
            
            # 确定颜色
            item_color = 'gray'
            for key, color in colors.items():
                if item_name.startswith(key):
                    item_color = color
                    break
            
            # 绘制物体
            plot_polygon(ax, item_polygon, 
                        facecolor=item_color, edgecolor='black', 
                        alpha=0.6, linewidth=1.5)
            
            # 标注物体名称
            ax.text(center[0], center[1], item_name, 
                   ha='center', va='center', fontsize=8, 
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))
            
            # 如果是冰箱，绘制开门禁区
            if item_name.startswith('fridge'):
                try:
                    # 使用与sovler.py相同的方法创建冰箱开门禁区（支持任意角度）
                    # 双开门：冰箱length边为开门边，门从中间向两边打开，半径为length/2
                    # 禁区为矩形：宽度=length（整个开门边），深度=length/2（开门半径）
                    clearance_depth = length / 2
                    clearance = box(-length/2, width/2, length/2, width/2 + clearance_depth)
                    clearance = rotate(clearance, rotation, origin=(0, 0))
                    door_zone = translate(clearance, center[0], center[1])
                    
                    x_zone, y_zone = door_zone.exterior.xy
                    ax.fill(x_zone, y_zone, 
                           facecolor='lightblue', edgecolor='blue', 
                           alpha=0.3, linewidth=1, linestyle='--')
                    ax.plot(x_zone, y_zone, color='blue', linewidth=1, linestyle='--')
                    # 在禁区中心标注
                    zone_center = door_zone.centroid
                    ax.text(zone_center.x, zone_center.y, '开门禁区', 
                           ha='center', va='center', fontsize=7, 
                           color='blue', style='italic')
                except Exception as e:
                    print(f"警告: 无法创建冰箱开门禁区 - {e}")
    
    # 设置图形属性
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='upper right', fontsize=9)
    
    # 设置标题
    input_basename = os.path.splitext(os.path.basename(input_file))[0]
    ax.set_title(f'房间布局可视化 - {input_basename}\n已放置: {placed_count}/{len(items_to_place)}', 
                fontsize=12, fontweight='bold')
    
    ax.set_xlabel('X坐标', fontsize=10)
    ax.set_ylabel('Y坐标', fontsize=10)
    
    # 显示图形
    plt.tight_layout()
    plt.show()


def main():
    """主函数"""
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # 默认输入文件
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        if not os.path.isabs(input_file):
            if not os.path.exists(input_file):
                project_path = os.path.join(project_root, input_file)
                if os.path.exists(project_path):
                    input_file = project_path
    else:
        input_file = os.path.join(project_root, 'data', 'example1.json')
    
    # 可选的结果文件
    result_file = None
    if len(sys.argv) > 2:
        result_file = sys.argv[2]
        if not os.path.isabs(result_file):
            if not os.path.exists(result_file):
                project_path = os.path.join(project_root, result_file)
                if os.path.exists(project_path):
                    result_file = project_path
    
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 文件 '{input_file}' 不存在")
        print(f"用法: python visualize.py [输入文件路径] [结果文件路径(可选)]")
        print(f"示例: python visualize.py ../data/example1.json")
        return
    
    try:
        visualize_layout(input_file, result_file)
    except Exception as e:
        print(f"错误: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
