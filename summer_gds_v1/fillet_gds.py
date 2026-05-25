#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
通用GDS倒角脚本
使用KLayout的rounded_corners API对GDS文件中的所有多边形进行倒角处理
"""

import sys
import os
import klayout.db as db


def fillet_gds(input_file, output_file, radius_um, num_points=64):
    """对GDS文件中的所有多边形进行倒角处理

    参数:
        input_file: 输入GDS文件路径
        output_file: 输出GDS文件路径
        radius_um: 倒角半径（微米）
        num_points: 每个圆弧的点数，默认64
    """
    print(f"正在读取GDS文件: {input_file}")

    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在: {input_file}")
        return False

    # 读取GDS文件
    layout = db.Layout()
    layout.read(input_file)

    # 获取dbu（数据库单位）
    dbu = layout.dbu
    print(f"数据库单位: {dbu} um")

    # 将倒角半径转换为数据库单位
    radius_db = int(radius_um / dbu)
    print(f"倒角半径: {radius_um} um (数据库单位: {radius_db})")
    print(f"圆弧点数: {num_points}")

    # 统计信息
    num_cells = layout.cells()
    total_layers = set()
    total_polygons = 0
    processed_polygons = 0

    print(f"\n开始处理...")
    print(f"总cell数: {num_cells}")

    # 遍历所有cell
    for cell_idx in range(num_cells):
        cell = layout.cell(cell_idx)
        cell_name = cell.name

        # 获取该cell的所有layer
        layer_infos = []
        for layer_info in layout.layer_infos():
            layer_idx = layout.layer(layer_info)
            if cell.shapes(layer_idx).size() > 0:
                layer_infos.append((layer_info, layer_idx))
                total_layers.add((layer_info.layer, layer_info.datatype))

        if len(layer_infos) == 0:
            continue

        print(f"\n处理Cell: {cell_name} (包含{len(layer_infos)}个图层)")

        # 遍历该cell的所有有图形的layer
        for layer_info, layer_idx in layer_infos:
            layer_num = layer_info.layer
            datatype = layer_info.datatype

            # 获取原始shapes
            shapes = cell.shapes(layer_idx)
            num_shapes = shapes.size()

            if num_shapes == 0:
                continue

            total_polygons += num_shapes
            print(f"  图层 [{layer_num}, {datatype}]: {num_shapes} 个图形", end=" ")

            # 创建Region并收集所有多边形
            region = db.Region()
            for shape in shapes.each():
                if shape.is_polygon() or shape.is_box() or shape.is_path():
                    # 转换为多边形
                    if shape.is_polygon():
                        region.insert(shape.polygon)
                    elif shape.is_box():
                        # Box对象需要通过Polygon构造函数转换
                        region.insert(db.Polygon(shape.box))
                    elif shape.is_path():
                        region.insert(shape.path.polygon())

            if region.is_empty():
                print("-> 跳过（无多边形）")
                continue

            # 应用倒角
            # inner和outer使用相同的半径实现统一倒角
            rounded_region = region.rounded_corners(radius_db, radius_db, num_points)

            # 清空原shapes并插入倒角后的
            shapes.clear()
            shapes.insert(rounded_region)

            processed_polygons += num_shapes
            print(f"-> 完成")

    # 保存结果
    print(f"\n保存结果到: {output_file}")
    layout.write(output_file)

    # 输出统计信息
    print(f"\n=== 处理完成 ===")
    print(f"处理的Cell数: {num_cells}")
    print(f"处理的图层数: {len(total_layers)}")
    print(f"处理的多边形数: {processed_polygons}/{total_polygons}")

    return True


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python fillet_gds.py <input.gds> [output.gds] [radius_um] [num_points]")
        print("\n参数说明:")
        print("  input.gds    : 输入GDS文件路径（必需）")
        print("  output.gds   : 输出GDS文件路径（可选，默认为输入文件名_rounded.gds）")
        print("  radius_um    : 倒角半径（微米），可选，默认50")
        print("  num_points   : 每个圆弧的点数，可选，默认64")
        print("\n示例:")
        print("  python fillet_gds.py input.gds")
        print("  python fillet_gds.py input.gds output.gds")
        print("  python fillet_gds.py input.gds output.gds 50")
        print("  python fillet_gds.py input.gds output.gds 50 128")
        sys.exit(1)

    input_file = sys.argv[1]

    # 默认输出文件名
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_rounded.gds"

    # 默认半径
    radius_um = 50.0
    if len(sys.argv) >= 4:
        try:
            radius_um = float(sys.argv[3])
        except ValueError:
            print(f"错误: 倒角半径必须是数字: {sys.argv[3]}")
            sys.exit(1)

    # 默认圆弧点数
    num_points = 64
    if len(sys.argv) >= 5:
        try:
            num_points = int(sys.argv[4])
            if num_points < 4:
                print(f"警告: 圆弧点数至少为4，已自动调整")
                num_points = 4
        except ValueError:
            print(f"错误: 圆弧点数必须是整数: {sys.argv[4]}")
            sys.exit(1)

    # 执行倒角处理
    success = fillet_gds(input_file, output_file, radius_um, num_points)

    if success:
        print("\n处理成功!")
    else:
        print("\n处理失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()
