from datetime import datetime

def process_warning_data(warnsum_json, warninginfo_json):
    # Step 1: Sort warnsum_json by updateTime (latest 3)
    sorted_items = sorted(
        warnsum_json.items(),
        key=lambda item: datetime.fromisoformat(item[1]['updateTime'].replace(' ', '').replace('+08:00', '')),
        reverse=True
    )[:3]

    # Step 2: Prepare warnsum_items with key logic
    warnsum_items = {}
    for i, (key, val) in enumerate(sorted_items, 1):
        code = key
        if code in ['WRAIN', 'WFIRE']:
            label = f"{val.get('type', '')}{val['name']}"
        elif code == 'WTCSGNL':
            label = val.get('type', '')
        else:
            label = val['name']
        warnsum_items[str(i)] = label

    # Step 3: Map to warninginfo.json by warningStatementCode
    warninfo_items = {}
    details_list = warninginfo_json.get('details', [])
    for idx, (key, label) in enumerate(warnsum_items.items(), 1):
        # Use label to find matching 'warningStatementCode' from details
        for detail in details_list:
            # Match by warningStatementCode (which should equal key from warnsum_json)
            if detail.get('warningStatementCode') == sorted_items[idx - 1][0]:
                warninfo_items[str(idx)] = detail.get('contents', [])
                break
        else:
            warninfo_items[str(idx)] = ["No detailed info found."]

    return warnsum_items, warninfo_items
