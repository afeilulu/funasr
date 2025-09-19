import os
import json
import re
from cos import upload_file


def extract_json_content(text):
    """
    从文本中提取第一个被```json和```包裹的JSON内容
    :param text: 包含JSON内容的原始文本
    :return: 提取到的JSON字符串，如果没有找到则返回None
    """
    pattern = r'```json\s*(.*?)\s*```'
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else None

def merge_consecutive_items(items):
    if not items:
        return []
    
    merged_items = []
    current_item = items[0].copy()  # 创建当前项的副本以避免修改原项
    if ("timestamp" in current_item):
        del current_item["timestamp"]
    
    for i in range(1, len(items)):
        next_item = items[i]
        if ("timestamp" in next_item):
            del next_item["timestamp"]
        
        # 检查是否满足合并条件：相同说话人且当前结束时间等于下一项开始时间
        if (current_item['spk'] == next_item['spk'] and 
            current_item['end'] == next_item['start']):
            
            # 合并文本
            current_item['text'] += next_item['text']
            # 更新结束时间为下一项的结束时间
            current_item['end'] = next_item['end']
        else:
            # 如果不满足合并条件，将当前项添加到结果列表
            merged_items.append(current_item)
            # 重置当前项为下一项
            current_item = next_item.copy()
    
    # 添加最后一个当前项
    merged_items.append(current_item)
    
    return merged_items

def split_and_save_json_list(data_list, base_filename="part", output_dir="output"):
    """
    将列表按每50个元素分割并保存为多个JSON文件
    
    Args:
        data_list: 要处理的列表
        base_filename: 生成文件的基础文件名
        output_dir: 输出目录
    """
    # 创建输出目录（如果不存在）
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 计算需要分割成几部分
    chunk_size = 50
    total_chunks = (len(data_list) + chunk_size - 1) // chunk_size
    
    urls = []
    # 分割并保存列表
    for i in range(total_chunks):
        start_index = i * chunk_size
        end_index = start_index + chunk_size
        chunk = data_list[start_index:end_index]
        
        # 生成文件名
        filename = f"{base_filename}_{i+1}.json"
        filepath = os.path.join(output_dir, filename)
        
        # 保存为JSON文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, ensure_ascii=False, indent=2)
        
        print(f"已保存: {filepath} (包含 {len(chunk)} 个元素)")
        url = upload_file(filename, filepath)
        if (url):
            urls.append(url)

    return urls

def save_file(data, filename="part.json", output_dir="output"):
    # 创建输出目录（如果不存在）
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 生成文件名
    filepath = os.path.join(output_dir, filename)
    
    # 保存为JSON文件
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"已保存: {filepath}")
    return filepath