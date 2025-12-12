import requests
import json
import time

url = "https://gateway.jpgcp.cloud/chat-api-svc/api/v1/purechat"
payload = {
    "message": "请讲一个关于人类文明演变的漫长故事，请尽量详细，写得越长越好。",
    "model": "gemini"
}
headers = {
    "Content-Type": "application/json"
}

print(f"Starting test request to {url}...")
start_time = time.time()

try:
    with requests.post(url, json=payload, headers=headers, stream=True) as response:
        if response.status_code != 200:
            print(f"Error: Status Code {response.status_code}")
            print(response.text)
            exit(1)
            
        print("Response received, reading stream...")
        chunk_count = 0
        for chunk in response.iter_content(chunk_size=None):
            if chunk:
                chunk_count += 1
                # print(chunk.decode('utf-8'), end='', flush=True) # Optional: print content
                if chunk_count % 10 == 0:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    print(f"Received {chunk_count} chunks. Elapsed time: {elapsed:.2f}s")
        
        total_time = time.time() - start_time
        print(f"\nStream finished successfully. Total time: {total_time:.2f}s")

except Exception as e:
    total_time = time.time() - start_time
    print(f"\nRequest failed after {total_time:.2f}s: {e}")
