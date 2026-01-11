import math
from typing import List, Tuple, Dict, Optional
from shapely.geometry import Polygon, Point, LineString, box
from shapely.affinity import rotate, translate
from utils import create_door_avoidance_zone

class LayoutSolver:
    def __init__(self, data: Dict):
        # 初始化基础数据 
        self.boundary_points = data['boundary']
        self.door_points = data['door']
        self.is_open_inward = data.get('isOpenInward', False)
        self.items_to_place = data['algoToPlace']
        
        self.room_polygon = Polygon(self.boundary_points)
        self.placed_items = []
        
        # 1. 预处理门禁区：如果是内开门，占据N x N空间 
        self.door_line = LineString(self.door_points)
        self.door_width = self.door_line.length
        if self.is_open_inward:
            # 使用utils中的函数创建 N x N 的正方形避让区
            door_avoidance = create_door_avoidance_zone(
                self.door_points, 
                self.is_open_inward, 
                self.door_width, 
                self.room_polygon
            )
            if door_avoidance is not None:
                self.door_restricted_zone = door_avoidance
            else:
                # 如果创建失败，使用默认的buffer方法作为后备
                self.door_restricted_zone = self.door_line.buffer(self.door_width / 2)
        else:
            # 外开门仅需避开门线本身（使用合适的buffer，确保物品不会遮挡门）
            # 外开门不需要像内开门那样占据N×N空间，但仍需要足够buffer防止遮挡
            # 使用门宽的5%或50单位，取较小值，确保物品不会太靠近门
            buffer_size = min(self.door_width * 0.05, 50)  # 门宽的5%或50单位，取较小值
            self.door_restricted_zone = self.door_line.buffer(buffer_size)

    def _get_wall_segments(self):
        """获取所有墙面线段"""
        coords = list(self.room_polygon.exterior.coords)
        return [LineString([coords[i], coords[i+1]]) for i in range(len(coords)-1)]
    
    def _try_free_placement(self, name, length, width, results):
        """尝试自由放置（不贴墙）"""
        # 获取房间的边界框
        minx, miny, maxx, maxy = self.room_polygon.bounds
        
        # 计算合适的网格间距（基于物体的最大尺寸）
        max_dim = max(length, width)
        step_size = max_dim * 1.2  # 间距略大于物体尺寸
        
        # 生成网格点（向内偏移，避免靠近边界）
        margin = max_dim / 2 + 10  # 留出边距
        
        # 尝试的角度（0, 90, 180, 270）
        angles = [0, 90, 180, 270]
        
        # 生成候选点（网格搜索）
        x_coords = []
        y_coords = []
        x = minx + margin
        while x < maxx - margin:
            x_coords.append(x)
            x += step_size
        # 如果只有一个点或没有点，添加中间点
        if len(x_coords) == 0:
            x_coords.append((minx + maxx) / 2)
        
        y = miny + margin
        while y < maxy - margin:
            y_coords.append(y)
            y += step_size
        if len(y_coords) == 0:
            y_coords.append((miny + maxy) / 2)
        
        # 尝试所有组合
        for angle in angles:
            for x in x_coords:
                for y in y_coords:
                    center = (x, y)
                    
                    # 检查点是否在房间内
                    if not self.room_polygon.contains(Point(center)):
                        continue
                    
                    # 特殊处理冰箱
                    clearance = None
                    if "fridge" in name:
                        poly, clearance = self.get_fridge_zones(center, length, width, angle)
                    else:
                        poly = self.create_item_poly(center, length, width, angle)
                    
                    if self.is_valid_position(poly, clearance):
                        self.placed_items.append({'name': name, 'poly': poly, 'clearance': clearance})
                        results[name] = {"center": center, "rotation": angle % 360, "placed": True}
                        return True
        
        return False

    def create_item_poly(self, center: Tuple[float, float], length: float, width: float, angle: float):
        """创建物体矩形多边形 """
        p = box(-length/2, -width/2, length/2, width/2)
        p = rotate(p, angle, origin=(0, 0))
        return translate(p, center[0], center[1])

    def get_fridge_zones(self, center, length, width, angle):
        """
        处理冰箱特有的开门侧禁区
        双开门：冰箱length边为开门边，门从中间向两边打开，半径为length/2
        禁区为矩形：宽度=length（整个开门边），深度=length/2（开门半径）
        """
        body = self.create_item_poly(center, length, width, angle)
        
        # 禁区：在length边（开门边）的正前方
        # 宽度：length（整个开门边的长度）
        # 深度：length/2（双开门打开半径）
        clearance_depth = length / 2
        
        # 创建禁区矩形（在length边的前方）
        # 在局部坐标系中：length沿x方向，width沿y方向
        # 开门边在+y方向（width/2处），禁区在前方
        clearance = box(-length/2, width/2, length/2, width/2 + clearance_depth)
        
        # 旋转和平移
        clearance = rotate(clearance, angle, origin=(0, 0))
        clearance = translate(clearance, center[0], center[1])
        
        return body, clearance

    def is_valid_position(self, item_poly, extra_zone=None):
        """多重碰撞检测 """
        # 1. 必须完全在房间内（允许边界重合，使用covers）
        # 如果covers失败，检查交集面积（处理浮点精度问题）
        if not self.room_polygon.covers(item_poly):
            intersection = self.room_polygon.intersection(item_poly)
            # 如果物体几乎完全在房间内（超过99.9%），认为有效
            if intersection.area < item_poly.area * 0.999:
                return False
        # 2. 不能遮挡门/进入门禁区
        # 严格检查：物品与门禁区不能有任何重叠（包括边界接触）
        if item_poly.intersects(self.door_restricted_zone):
            intersection = item_poly.intersection(self.door_restricted_zone)
            # 如果有任何重叠区域（面积大于0），则不允许
            if intersection.area > 1e-6:  # 使用很小的容差处理浮点误差
                return False
        # 3. 与已放置物体碰撞检测（使用overlaps检查内部重叠）
        for placed in self.placed_items:
            if item_poly.overlaps(placed['poly']) or \
               (item_poly.intersects(placed['poly']) and item_poly.intersection(placed['poly']).area > item_poly.area * 0.01):
                return False
            if 'clearance' in placed and placed['clearance'] is not None:
                if item_poly.overlaps(placed['clearance']) or \
                   (item_poly.intersects(placed['clearance']) and item_poly.intersection(placed['clearance']).area > item_poly.area * 0.01):
                    return False
        
        # 4. 冰箱自身的开门区检测
        if extra_zone:
            if not self.room_polygon.covers(extra_zone):
                intersection = self.room_polygon.intersection(extra_zone)
                if intersection.area < extra_zone.area * 0.999:
                    return False
            if extra_zone.overlaps(self.door_restricted_zone) or \
               (extra_zone.intersects(self.door_restricted_zone) and extra_zone.intersection(self.door_restricted_zone).area > extra_zone.area * 0.01):
                return False
            for placed in self.placed_items:
                if extra_zone.overlaps(placed['poly']) or \
                   (extra_zone.intersects(placed['poly']) and extra_zone.intersection(placed['poly']).area > extra_zone.area * 0.01):
                    return False
        return True

    def solve(self):
        # 重置已放置物品列表
        self.placed_items = []
        results = {}
        # 优先级排序：冰箱最优先 
        sorted_items = sorted(self.items_to_place.items(), key=lambda x: "fridge" not in x[0])
        walls = self._get_wall_segments()

        for name, dims in sorted_items:
            # 确保数值较大的作为length
            dim1, dim2 = dims
            length = max(dim1, dim2)
            width = min(dim1, dim2)
            placed_flag = False
            
            # 尝试所有墙面
            for wall in walls:
                # 计算墙面的角度
                wall_angle = math.degrees(math.atan2(wall.coords[1][1]-wall.coords[0][1], 
                                                   wall.coords[1][0]-wall.coords[0][0]))
                
                # 尝试与墙面平行或垂直（0度=平行，90度=垂直）
                for angle_offset in [0, 90]:
                    current_angle = wall_angle + angle_offset
                    
                    # 计算垂直于墙面指向内部的法线方向
                    dx, dy = (wall.coords[1][0]-wall.coords[0][0]), (wall.coords[1][1]-wall.coords[0][1])
                    norm = math.sqrt(dx**2 + dy**2)
                    if norm == 0:
                        continue
                    # 归一化墙方向向量
                    wall_dx, wall_dy = dx/norm, dy/norm
                    # 内部法线 (顺时针旋转90度: (-dy, dx))
                    nx, ny = -wall_dy, wall_dx
                    
                    # 验证法线方向是否正确指向内部（使用墙中点）
                    mid_wall_x = (wall.coords[0][0] + wall.coords[1][0]) / 2
                    mid_wall_y = (wall.coords[0][1] + wall.coords[1][1]) / 2
                    test_point = Point(mid_wall_x + nx * 100, mid_wall_y + ny * 100)
                    if not self.room_polygon.contains(test_point):
                        # 如果不在内部，反向
                        nx, ny = -nx, -ny
                    
                    # 创建物体在原点处的多边形（用于计算尺寸）
                    test_poly_temp = self.create_item_poly((0, 0), length, width, current_angle)
                    min_x, min_y, max_x, max_y = test_poly_temp.bounds
                    
                    # 计算物体在法线方向上的投影距离（物体中心到最近边的距离）
                    # 获取物体的所有顶点
                    coords = list(test_poly_temp.exterior.coords[:-1])
                    # 计算每个顶点在法线方向上的投影（点积）
                    projections = [px * nx + py * ny for px, py in coords]
                    min_proj = min(projections)  # 最靠近墙的顶点投影
                    max_proj = max(projections)  # 最远离墙的顶点投影
                    
                    # 物体中心到最近边的距离（绝对值）
                    offset_distance = -min_proj  # 因为物体中心在原点，min_proj是负值
                    
                    # 计算物体沿墙方向的长度（用于检查是否超出墙面）
                    # 计算每个顶点在墙方向上的投影
                    wall_projections = [px * wall_dx + py * wall_dy for px, py in coords]
                    min_wall_proj = min(wall_projections)
                    max_wall_proj = max(wall_projections)
                    item_length_along_wall = max_wall_proj - min_wall_proj
                    
                    # 检查物体长度是否超过墙面长度
                    wall_length = norm
                    if item_length_along_wall > wall_length:
                        continue  # 物体太长，无法放在这条墙上
                    
                    # 沿着墙面步进搜索，确保物体不会超出墙面范围
                    max_offset = wall_length - item_length_along_wall
                    if max_offset < 0:
                        continue  # 物体太长，无法放在这条墙上
                    # 增加搜索步数，提高搜索精度
                    steps = max(50, int(max_offset / 20))  # 根据可用空间调整步数，最小50步
                    if steps == 0:
                        steps = 1
                    
                    for s in range(steps + 1):
                        # 物体沿墙方向的偏移量（从墙起点开始）
                        offset_along_wall = (s / steps) * max_offset if steps > 0 else max_offset / 2
                        # 计算物体中心在墙上的位置
                        # 物体中心距离墙起点的距离 = offset_along_wall + item_length_along_wall/2
                        t = (offset_along_wall + item_length_along_wall / 2) / wall_length if wall_length > 0 else 0.5
                        t = max(0, min(1, t))  # 确保在[0,1]范围内
                        
                        # 计算墙面上的基准点（物体中心在墙上的投影点）
                        base_x = wall.coords[0][0] + t * (wall.coords[1][0] - wall.coords[0][0])
                        base_y = wall.coords[0][1] + t * (wall.coords[1][1] - wall.coords[0][1])
                        
                        # 将物体中心向内偏移，使物体的一条边与墙面重合（间距为0）
                        center = (base_x + nx * offset_distance, base_y + ny * offset_distance)
                        
                        # 特殊处理冰箱 
                        clearance = None
                        if "fridge" in name:
                            poly, clearance = self.get_fridge_zones(center, length, width, current_angle)
                        else:
                            poly = self.create_item_poly(center, length, width, current_angle)

                        if self.is_valid_position(poly, clearance):
                            self.placed_items.append({'name': name, 'poly': poly, 'clearance': clearance})
                            results[name] = {"center": center, "rotation": current_angle % 360, "placed": True}
                            placed_flag = True
                            break
                    if placed_flag: break
                if placed_flag: break
            
            # 如果贴墙放置失败，尝试自由放置（不贴墙）
            if not placed_flag:
                placed_flag = self._try_free_placement(name, length, width, results)
            
            if not placed_flag:
                results[name] = {"placed": False, "error": "无法找到有效位置"}
        
        # 缓存结果
        self._last_results = results
        return results
    
    def is_feasible(self) -> bool:
        """检查当前布局是否可行（所有物体都已放置）"""
        # 如果已经求解过，直接检查结果
        if hasattr(self, '_last_results'):
            return all(item.get('placed', False) for item in self._last_results.values())
        # 否则求解一次
        results = self.solve()
        self._last_results = results
        return all(item.get('placed', False) for item in results.values())