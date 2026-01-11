"""
房间布局优化主程序

使用LayoutSolver类来解决房间内物体的布局问题
"""

import json
import sys
import os
from sovler import LayoutSolver


def load_data(file_path: str) -> dict:
    """
    加载JSON格式的房间数据
    
    Args:
        file_path: JSON文件路径
    
    Returns:
        房间数据字典
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_results(results: dict, output_path: str):
    """
    保存布局结果到JSON文件
    
    Args:
        results: 布局结果字典
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def print_results(results: dict):
    """
    打印布局结果
    
    Args:
        results: 布局结果字典
    """
    print("\n=== 布局结果 ===")
    print(f"总计物体数量: {len(results)}")
    
    placed_count = sum(1 for r in results.values() if r.get('placed', False))
    print(f"成功放置: {placed_count}")
    print(f"未放置: {len(results) - placed_count}")
    
    print("\n详细结果:")
    for item_name, result in results.items():
        if result.get('placed', False):
            center = result['center']
            rotation = result['rotation']
            print(f"  {item_name}:")
            print(f"    中心点: ({center[0]:.2f}, {center[1]:.2f})")
            print(f"    旋转角度: {rotation}°")
        else:
            error = result.get('error', '未知错误')
            print(f"  {item_name}: 未放置 - {error}")


def main():
    """主函数"""
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # src的父目录（项目根目录）
    
    # 默认输入文件（相对于项目根目录）
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        # 如果是相对路径，尝试相对于项目根目录
        if not os.path.isabs(input_file):
            # 先尝试相对于当前目录
            if not os.path.exists(input_file):
                # 再尝试相对于项目根目录
                project_path = os.path.join(project_root, input_file)
                if os.path.exists(project_path):
                    input_file = project_path
    else:
        # 默认文件，使用项目根目录下的data目录
        input_file = os.path.join(project_root, 'data', 'example1.json')
    
    # 检查文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 文件 '{input_file}' 不存在")
        print(f"用法: python main.py [输入文件路径]")
        print(f"示例: python main.py ../data/example1.json")
        print(f"示例: python main.py data/example1.json")
        return
    
    print(f"加载数据文件: {input_file}")
    
    try:
        # 加载数据
        data = load_data(input_file)
        print(f"房间边界点数: {len(data['boundary'])}")
        print(f"待放置物体数量: {len(data['algoToPlace'])}")
        
        # 创建求解器
        print("\n开始求解布局...")
        solver = LayoutSolver(data)
        
        # 求解布局
        results = solver.solve()
        
        # 打印结果
        print_results(results)
        
        # 检查是否可行
        is_feasible = solver.is_feasible()
        print(f"\n布局是否可行: {'是' if is_feasible else '否'}")
        
        # 保存结果到output目录（相对于项目根目录）
        output_dir = os.path.join(project_root, 'output')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        input_basename = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(output_dir, f'{input_basename}_result.json')
        save_results(results, output_file)
        print(f"\n结果已保存到: {output_file}")
        
    except FileNotFoundError as e:
        print(f"错误: 文件未找到 - {e}")
    except json.JSONDecodeError as e:
        print(f"错误: JSON格式错误 - {e}")
    except KeyError as e:
        print(f"错误: 数据格式错误，缺少字段 - {e}")
    except Exception as e:
        print(f"错误: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
