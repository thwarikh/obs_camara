import urllib.request
import json
import time

for i in range(15):
    time.sleep(12)
    try:
        req = urllib.request.Request('https://api.github.com/repos/thwarikh/obs_camara/actions/runs?per_page=1', headers={'User-Agent': 'Mozilla/5.0'})
        data = json.loads(urllib.request.urlopen(req).read().decode())
        run = data['workflow_runs'][0]
        status = run.get('status')
        conclusion = run.get('conclusion')
        html_url = run.get('html_url')
        print(f"Check {i+1}: Run ID {run.get('id')} - {status} ({conclusion})")
        if status == 'completed':
            print(f"Final Conclusion: {conclusion}")
            print(f"URL: {html_url}")
            break
    except Exception as e:
        print("Polling error:", e)

