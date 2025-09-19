
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