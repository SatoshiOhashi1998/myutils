import requests
import json

def send_to_gas(data, gas_url, action_name=None, verbose=True):
    """
    Google Apps Scriptにデータを送信する共通関数
    
    Args:
        data (dict | list): 送信するデータ
        action_name (str, optional): 処理の種類をログに表示するための名前
        verbose (bool): Trueならレスポンス詳細を表示
    """
    headers = {"Content-Type": "application/json; charset=utf-8"}

    try:
        response = requests.post(gas_url, headers=headers, json=data)

        if verbose:
            label = f"[{action_name}] " if action_name else ""
            print(f"{label}Response status code: {response.status_code}")

            # JSONとして解釈できれば整形して出力
            try:
                print(json.dumps(response.json(), ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                print("Raw response text:", response.text)

        return response

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return None
