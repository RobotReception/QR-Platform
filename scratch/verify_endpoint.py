import requests

url = "http://localhost:8020/api/v1/templates/fonts/file/alfont_com_Zain-PC-VF.ttf"
try:
    response = requests.get(url)
    print("Status code:", response.status_code)
    print("Headers:", response.headers)
    print("Content length:", len(response.content))
except Exception as e:
    print("Error:", e)
