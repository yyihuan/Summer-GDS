#!/usr/bin/env python3
"""
GDS 文件对比脚本
用于验证重构后生成的 GDS 文件与基准文件是否一致
"""

import os
import sys
import hashlib
from pathlib import Path


def calculate_md5(file_path):
    """计算文件的 MD5 哈希值"""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def compare_gds_files(baseline_dir, current_dir, output_file=None):
    """
    对比基准 GDS 文件和当前生成的 GDS 文件
    
    Args:
        baseline_dir: 基准文件目录
        current_dir: 当前文件目录
        output_file: 输出报告文件路径（可选）
    
    Returns:
        bool: 所有文件都匹配返回 True，否则返回 False
    """
    baseline_path = Path(baseline_dir)
    current_path = Path(current_dir)
    
    if not baseline_path.exists():
        print(f"❌ 基准目录不存在: {baseline_dir}")
        return False
    
    if not current_path.exists():
        print(f"❌ 当前目录不存在: {current_dir}")
        return False
    
    # 获取所有基准 GDS 文件
    baseline_files = {f.name: f for f in baseline_path.glob("*.gds")}
    current_files = {f.name: f for f in current_path.glob("*.gds")}
    
    if not baseline_files:
        print(f"⚠️  基准目录中没有 GDS 文件: {baseline_dir}")
        return False
    
    # 统计结果
    total = len(baseline_files)
    matched = 0
    missing = 0
    different = 0
    
    results = []
    
    print(f"\n{'='*70}")
    print(f"GDS 文件对比报告")
    print(f"{'='*70}")
    print(f"基准目录: {baseline_dir}")
    print(f"当前目录: {current_dir}")
    print(f"{'='*70}\n")
    
    # 对比每个基准文件
    for filename, baseline_file in sorted(baseline_files.items()):
        if filename not in current_files:
            print(f"❌ 缺失: {filename}")
            results.append(f"MISSING: {filename}")
            missing += 1
            continue
        
        current_file = current_files[filename]
        
        # 计算哈希值
        baseline_md5 = calculate_md5(baseline_file)
        current_md5 = calculate_md5(current_file)
        
        if baseline_md5 == current_md5:
            print(f"✅ 匹配: {filename}")
            results.append(f"MATCH: {filename}")
            matched += 1
        else:
            print(f"❌ 不同: {filename}")
            print(f"   基准 MD5: {baseline_md5}")
            print(f"   当前 MD5: {current_md5}")
            results.append(f"DIFFERENT: {filename}")
            results.append(f"  Baseline MD5: {baseline_md5}")
            results.append(f"  Current MD5:  {current_md5}")
            different += 1
    
    # 检查是否有新增的文件
    extra_files = set(current_files.keys()) - set(baseline_files.keys())
    if extra_files:
        print(f"\n⚠️  新增文件（不在基准中）:")
        for filename in sorted(extra_files):
            print(f"   + {filename}")
            results.append(f"EXTRA: {filename}")
    
    # 打印汇总
    print(f"\n{'='*70}")
    print(f"汇总统计")
    print(f"{'='*70}")
    print(f"总文件数: {total}")
    print(f"✅ 匹配:   {matched}")
    print(f"❌ 不同:   {different}")
    print(f"❌ 缺失:   {missing}")
    print(f"{'='*70}\n")
    
    # 保存报告
    if output_file:
        with open(output_file, 'w') as f:
            f.write(f"GDS 文件对比报告\n")
            f.write(f"{'='*70}\n")
            f.write(f"基准目录: {baseline_dir}\n")
            f.write(f"当前目录: {current_dir}\n")
            f.write(f"{'='*70}\n\n")
            f.write("\n".join(results))
            f.write(f"\n\n{'='*70}\n")
            f.write(f"汇总统计\n")
            f.write(f"{'='*70}\n")
            f.write(f"总文件数: {total}\n")
            f.write(f"匹配:     {matched}\n")
            f.write(f"不同:     {different}\n")
            f.write(f"缺失:     {missing}\n")
            f.write(f"{'='*70}\n")
        print(f"📄 报告已保存到: {output_file}")
    
    # 返回是否全部匹配
    return different == 0 and missing == 0


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python compare_gds.py <baseline_dir> [current_dir] [output_file]")
        print("\n示例:")
        print("  python compare_gds.py tests/baseline_outputs")
        print("  python compare_gds.py tests/baseline_outputs . report.txt")
        sys.exit(1)
    
    baseline_dir = sys.argv[1]
    current_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    success = compare_gds_files(baseline_dir, current_dir, output_file)
    
    if success:
        print("✅ 所有文件都匹配！")
        sys.exit(0)
    else:
        print("❌ 存在不匹配的文件！")
        sys.exit(1)


if __name__ == "__main__":
    main()

