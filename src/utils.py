"""
几何碰撞检测工具模块

基于 shapely 库实现房间布局优化中的几何碰撞检测功能。
主要功能：
1. 考虑内开门的 N×N 避让区
2. 实现冰箱开门侧的禁区检测
3. 物体需与墙体平行或垂直摆放（0°或90°旋转）
"""

from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from typing import List, Tuple, Optional
import math


def create_room_polygon(boundary_points: List[List[float]]) -> Polygon:
    """
    根据边界点创建房间多边形
    
    Args:
        boundary_points: 边界点列表，格式为 [[x1, y1], [x2, y2], ...]
                        注意：最后一个点通常与第一个点相同（闭合多边形）
    
    Returns:
        shapely Polygon 对象表示房间边界
    """
    # 如果最后一个点与第一个点相同，去掉重复点
    points = boundary_points.copy()
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    
    # 创建多边形
    return Polygon(points)


def calculate_door_width(door_points: List[List[float]]) -> float:
    """
    计算门的宽度（门两端点之间的距离）
    
    Args:
        door_points: 门的两端点，格式为 [[x1, y1], [x2, y2]]
    
    Returns:
        门的宽度（距离）
    """
    p1 = Point(door_points[0])
    p2 = Point(door_points[1])
    return p1.distance(p2)


def create_door_avoidance_zone(
    door_points: List[List[float]], 
    is_open_inward: bool, 
    door_width: Optional[float] = None,
    room_polygon: Optional[Polygon] = None
) -> Optional[Polygon]:
    """
    创建门的避让区
    
    如果是内开门（isOpenInward = true），需要创建一个 N×N 的避让区（N为门宽）
    避让区位于门的内侧（房间内）
    
    Args:
        door_points: 门的两端点，格式为 [[x1, y1], [x2, y2]]
        is_open_inward: 是否为内开门
        door_width: 门的宽度，如果为None则自动计算
        room_polygon: 房间多边形（可选，用于验证避让区是否在房间内）
    
    Returns:
        避让区多边形，如果不需要避让区则返回None
    """
    if not is_open_inward:
        return None
    
    # 计算门宽
    if door_width is None:
        door_width = calculate_door_width(door_points)
    
    p1 = Point(door_points[0])
    p2 = Point(door_points[1])
    
    # 计算门的中心点
    center_x = (p1.x + p2.x) / 2
    center_y = (p1.y + p2.y) / 2
    
    # 计算门的方向向量
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    length = math.sqrt(dx*dx + dy*dy)
    
    if length == 0:
        return None
    
    # 归一化方向向量
    dx /= length
    dy /= length
    
    # 垂直向量（顺时针旋转90度），用于确定避让区的方向
    # 内开门时，避让区应该在门的内部（房间内）
    perp_x = -dy  # 垂直向量
    perp_y = dx
    
    # 创建 N×N 的正方形避让区
    # 避让区中心在门的中心，沿垂直于门的方向向内（房间内）偏移
    # 偏移距离为 door_width / 2（使得避让区完全在房间内）
    offset_x = center_x + perp_x * (door_width / 2)
    offset_y = center_y + perp_y * (door_width / 2)
    
    # 创建正方形避让区（边长为门宽N）
    half_size = door_width / 2
    avoidance_zone = box(
        offset_x - half_size,
        offset_y - half_size,
        offset_x + half_size,
        offset_y + half_size
    )
    
    # 如果提供了房间多边形，验证避让区是否在房间内
    if room_polygon is not None:
        # 如果避让区不在房间内，尝试反向
        if not room_polygon.contains(avoidance_zone):
            # 尝试反向垂直向量
            offset_x = center_x - perp_x * (door_width / 2)
            offset_y = center_y - perp_y * (door_width / 2)
            avoidance_zone = box(
                offset_x - half_size,
                offset_y - half_size,
                offset_x + half_size,
                offset_y + half_size
            )
    
    return avoidance_zone


def create_rectangle(
    center: Tuple[float, float], 
    length: float, 
    width: float, 
    rotation: float
) -> Polygon:
    """
    创建矩形物体（支持0°、90°、180°、270°旋转）
    
    物体需与墙体平行或垂直摆放，因此只支持0°或90°的倍数的旋转
    
    Args:
        center: 矩形中心点坐标 (x, y)
        length: 矩形长度（初始状态下的x方向尺寸）
        width: 矩形宽度（初始状态下的y方向尺寸）
        rotation: 旋转角度（度），只能是0、90、180或270
    
    Returns:
        shapely Polygon 对象表示矩形（轴对齐）
    """
    # 标准化旋转角度
    rotation = rotation % 360
    if rotation not in [0, 90, 180, 270]:
        raise ValueError(f"旋转角度必须是0、90、180或270的倍数，当前为{rotation}")
    
    # 根据旋转角度确定实际的长宽
    # 对于轴对齐矩形，90°和270°需要交换长宽，0°和180°保持原样
    if rotation in [0, 180]:
        actual_length = length
        actual_width = width
    else:  # rotation in [90, 270]
        actual_length = width
        actual_width = length
    
    # 创建轴对齐矩形（使用box函数）
    half_length = actual_length / 2
    half_width = actual_width / 2
    
    # box函数创建轴对齐矩形（左下角和右上角）
    rect = box(
        center[0] - half_length,
        center[1] - half_width,
        center[0] + half_length,
        center[1] + half_width
    )
    
    # 注意：对于轴对齐矩形，0°、90°、180°、270°旋转后的形状相同
    # （因为只是交换了长宽，对于矩形来说形状是一样的）
    # 这里我们直接返回轴对齐矩形，旋转信息通过实际的长宽参数体现
    
    return rect


def rotate_polygon(polygon: Polygon, angle: float, origin: Tuple[float, float]) -> Polygon:
    """
    围绕指定原点旋转多边形
    
    Args:
        polygon: 要旋转的多边形
        angle: 旋转角度（度）
        origin: 旋转中心点 (x, y)
    
    Returns:
        旋转后的多边形
    """
    # 转换为弧度
    angle_rad = math.radians(angle)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    ox, oy = origin
    
    def rotate_point(point):
        px, py = point.x, point.y
        # 平移到原点
        px -= ox
        py -= oy
        # 旋转
        new_x = px * cos_a - py * sin_a
        new_y = px * sin_a + py * cos_a
        # 平移回去
        new_x += ox
        new_y += oy
        return (new_x, new_y)
    
    # 旋转所有点
    coords = list(polygon.exterior.coords[:-1])  # 去掉最后一个重复点
    rotated_coords = [rotate_point(Point(coord)) for coord in coords]
    
    return Polygon(rotated_coords)


def create_fridge_door_zone(
    fridge_center: Tuple[float, float],
    fridge_length: float,
    fridge_width: float,
    rotation: float,
    door_side: str = 'length'  # 'length' 或 'width'，表示开门边是length边还是width边
) -> Polygon:
    """
    创建冰箱开门侧的禁区
    
    冰箱的length边（或width边）为开门边，开门边不能放任何东西
    需要创建一个禁区区域，通常是在开门边前方的一定距离
    
    Args:
        fridge_center: 冰箱中心点坐标 (x, y)
        fridge_length: 冰箱长度
        fridge_width: 冰箱宽度
        rotation: 冰箱旋转角度（度），只能是0或90
        door_side: 开门边，'length' 表示length边是开门边，'width' 表示width边是开门边
    
    Returns:
        禁区多边形
    """
    # 标准化旋转角度
    rotation = rotation % 360
    if rotation not in [0, 90, 180, 270]:
        raise ValueError(f"旋转角度必须是0、90、180或270的倍数，当前为{rotation}")
    
    # 确定开门边的实际尺寸和位置
    if door_side == 'length':
        door_edge_length = fridge_length
        door_edge_width = fridge_width
    else:  # door_side == 'width'
        door_edge_length = fridge_width
        door_edge_width = fridge_length
    
    # 根据旋转角度确定实际的长宽
    if rotation in [0, 180]:
        actual_length = fridge_length
        actual_width = fridge_width
    else:  # rotation in [90, 270]
        actual_length = fridge_width
        actual_width = fridge_length
    
    # 确定开门边的位置（在冰箱的哪一边）
    # 假设开门边在length边的正前方（向外）
    # 创建一个禁区区域，通常需要一定的深度（比如门打开的最大距离）
    # 这里假设禁区的深度为门宽（door_edge_width），或者可以设置为一个固定值
    avoidance_depth = door_edge_width  # 禁区深度等于门的宽度（开门边的长度）
    
    # 创建冰箱矩形
    half_length = actual_length / 2
    half_width = actual_width / 2
    
    # 确定开门边的方向
    # 对于rotation=0: length边在x方向，开门边在+x或-x方向
    # 假设开门边在length边的正方向（+x方向）
    # 禁区在冰箱前方，宽度为door_edge_length，深度为avoidance_depth
    
    # 简化处理：创建一个与开门边相邻的矩形区域作为禁区
    # 需要根据rotation和door_side来确定禁区的具体位置
    
    if rotation == 0:
        if door_side == 'length':
            # 开门边在+x方向（右侧）
            # 禁区在冰箱右侧
            avoidance_zone = box(
                fridge_center[0] + half_length,  # 从冰箱右边界开始
                fridge_center[1] - half_width,   # 下边界
                fridge_center[0] + half_length + avoidance_depth,  # 右边界
                fridge_center[1] + half_width    # 上边界
            )
        else:  # door_side == 'width'
            # 开门边在+y方向（上侧）
            avoidance_zone = box(
                fridge_center[0] - half_length,
                fridge_center[1] + half_width,
                fridge_center[0] + half_length,
                fridge_center[1] + half_width + avoidance_depth
            )
    elif rotation == 90:
        if door_side == 'length':
            # 开门边在+y方向（上侧）
            avoidance_zone = box(
                fridge_center[0] - half_width,
                fridge_center[1] + half_length,
                fridge_center[0] + half_width,
                fridge_center[1] + half_length + avoidance_depth
            )
        else:  # door_side == 'width'
            # 开门边在-x方向（左侧）
            avoidance_zone = box(
                fridge_center[0] - half_length - avoidance_depth,
                fridge_center[1] - half_width,
                fridge_center[0] - half_length,
                fridge_center[1] + half_width
            )
    elif rotation == 180:
        if door_side == 'length':
            # 开门边在-x方向（左侧）
            avoidance_zone = box(
                fridge_center[0] - half_length - avoidance_depth,
                fridge_center[1] - half_width,
                fridge_center[0] - half_length,
                fridge_center[1] + half_width
            )
        else:  # door_side == 'width'
            # 开门边在-y方向（下侧）
            avoidance_zone = box(
                fridge_center[0] - half_length,
                fridge_center[1] - half_width - avoidance_depth,
                fridge_center[0] + half_length,
                fridge_center[1] - half_width
            )
    else:  # rotation == 270
        if door_side == 'length':
            # 开门边在-y方向（下侧）
            avoidance_zone = box(
                fridge_center[0] - half_width,
                fridge_center[1] - half_length - avoidance_depth,
                fridge_center[0] + half_width,
                fridge_center[1] - half_length
            )
        else:  # door_side == 'width'
            # 开门边在+x方向（右侧）
            avoidance_zone = box(
                fridge_center[0] + half_length,
                fridge_center[1] - half_width,
                fridge_center[0] + half_length + avoidance_depth,
                fridge_center[1] + half_width
            )
    
    return avoidance_zone


def check_collision(item1: Polygon, item2: Polygon) -> bool:
    """
    检查两个物体是否碰撞（重叠）
    
    Args:
        item1: 第一个物体的多边形
        item2: 第二个物体的多边形
    
    Returns:
        True表示碰撞，False表示不碰撞
    """
    return item1.intersects(item2)


def check_in_boundary(item: Polygon, room_polygon: Polygon) -> bool:
    """
    检查物体是否完全在房间边界内
    
    Args:
        item: 物体的多边形
        room_polygon: 房间边界多边形
    
    Returns:
        True表示物体完全在房间内，False表示不完全在房间内
    """
    return room_polygon.contains(item)


def check_axis_aligned(rotation: float) -> bool:
    """
    检查旋转角度是否与坐标轴对齐（0°或90°的倍数）
    
    Args:
        rotation: 旋转角度（度）
    
    Returns:
        True表示与坐标轴对齐，False表示不对齐
    """
    rotation = rotation % 360
    return rotation in [0, 90, 180, 270]


def check_item_validity(
    item: Polygon,
    room_polygon: Polygon,
    avoidance_zones: List[Polygon]
) -> Tuple[bool, str]:
    """
    综合检查物体放置的有效性
    
    检查项目：
    1. 物体是否完全在房间内
    2. 物体是否与避让区重叠
    
    Args:
        item: 物体的多边形
        room_polygon: 房间边界多边形
        avoidance_zones: 避让区列表（包括门的避让区和冰箱的开门禁区）
    
    Returns:
        (是否有效, 错误信息)
    """
    # 检查是否在房间内
    if not check_in_boundary(item, room_polygon):
        return False, "物体超出房间边界"
    
    # 检查是否与避让区重叠
    for zone in avoidance_zones:
        if zone is not None and check_collision(item, zone):
            return False, "物体与避让区重叠"
    
    return True, ""


def check_items_overlap(items: List[Polygon]) -> Tuple[bool, Tuple[int, int], str]:
    """
    检查多个物体之间是否重叠
    
    Args:
        items: 物体多边形列表
    
    Returns:
        (是否有重叠, (重叠的物体索引1, 物体索引2), 错误信息)
    """
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if check_collision(items[i], items[j]):
                return True, (i, j), f"物体 {i} 和物体 {j} 重叠"
    
    return False, (-1, -1), ""
