"""Offline Health & Readiness Diagnostic Probe CLI."""
import sys
import json
import urllib.request
import urllib.error

def check_health(host="127.0.0.1", port=8000):
    url = f"http://{host}:{port}/api/v1/health/ready"
    print(f"[*] Querying SAT-SA Readiness Probe: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SAT-SA-Diagnostic-Probe/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            data = json.loads(body)
            print(f"[+] HTTP {status_code} - System is READY and HEALTHY")
            print(json.dumps(data, indent=2))
            return 0
    except urllib.error.HTTPError as e:
        print(f"[-] HTTP Error {e.code}: {e.reason}")
        try:
            print(json.loads(e.read().decode("utf-8")))
        except Exception:
            pass
        return 1
    except Exception as e:
        print(f"[-] Connection failed: {str(e)}")
        return 1

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    sys.exit(check_health(port=port))
