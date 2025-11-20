#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建测试用的GDS文件
包含多个cell、多个layer、多种形状（正方形、环形等）
"""

import klayout.db as db


def create_test_gds():
    """创建一个包含多种形状的测试GDS文件"""
    layout = db.Layout()
    layout.dbu = 0.001  # 1nm = 0.001um

    # 创建主cell
    top_cell = layout.create_cell("TOP")

    # 定义多个图层
    layer1 = layout.layer(1, 0)
    layer2 = layout.layer(2, 0)
    layer3 = layout.layer(3, 0)

    # === 图层1: 正方形 ===
    square = db.Polygon([
        db.Point(0, 0),
        db.Point(100000, 0),      # 100um
        db.Point(100000, 100000),
        db.Point(0, 100000)
    ])
    top_cell.shapes(layer1).insert(square)

    # === 图层2: 方形环（带孔洞）===
    ring = db.Polygon([
        db.Point(150000, 0),      # 外框从x=150um开始
        db.Point(250000, 0),      # 100um宽
        db.Point(250000, 100000),
        db.Point(150000, 100000)
    ])
    # 插入内孔 (20um x 20um，居中)
    inner_hole = [
        db.Point(190000, 40000),
        db.Point(210000, 40000),
        db.Point(210000, 60000),
        db.Point(190000, 60000)
    ]
    ring.insert_hole(inner_hole)
    top_cell.shapes(layer2).insert(ring)

    # === 图层3: L形多边形 ===
    l_shape = db.Polygon([
        db.Point(300000, 0),
        db.Point(400000, 0),
        db.Point(400000, 40000),
        db.Point(340000, 40000),
        db.Point(340000, 100000),
        db.Point(300000, 100000)
    ])
    top_cell.shapes(layer3).insert(l_shape)

    # 保存
    output_file = "test_input.gds"
    layout.write(output_file)
    print(f"测试GDS文件已创建: {output_file}")
    print("\n内容说明:")
    print("  图层1 (1/0): 100um x 100um 正方形")
    print("  图层2 (2/0): 100um x 100um 方形环，内孔20um x 20um")
    print("  图层3 (3/0): L形多边形")
    print("\n可使用以下命令进行倒角测试:")
    print(f"  python fillet_gds.py {output_file}")


if __name__ == "__main__":
    create_test_gds()
