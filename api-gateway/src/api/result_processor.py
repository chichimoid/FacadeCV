_possibility_threshold = 0.1

def process_result(result_json: dict) -> list:
    img_preds = result_json['result']

    processed_img_preds = []
    for d in img_preds:
        img, pred = d.values()
        possible = {}
        key_0 = list(pred.keys())[0]
        possible[key_0] = pred.pop(key_0)

        top = dict(reversed(sorted(pred.items(), key=lambda item: item[1])))
        for k, v in top.items():
            if v > _possibility_threshold:
                possible[k] = v
        processed_img_preds.append(dict(zip(d.keys(), [img, possible])))

    return processed_img_preds