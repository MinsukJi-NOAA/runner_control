#!/usr/bin/env python3

import os, re, sys, json, time
from urllib.request import urlopen, Request
from datetime import datetime, timedelta

def check_build(request):
  """ Check if all build jobs are completed successfully
  API endpoint: api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs
  """
  all_completed = False
  while not all_completed:
    time.sleep(20)
    response = urlopen(request)
    data = json.loads(response.read().decode())["jobs"]
    ids = [x["id"] for x in data if re.search("Build", x["name"])]
    if len(ids) != int(os.environ["NO_BUILDS"]):
      continue
    all_completed = all([x["status"]=="completed" for x in data if x["id"] in ids])
  return all([x["conclusion"]=="success" for x in data if x["id"] in ids])


def check_test(request):
  """ Check if a workflow run is completed
  API endpoint: api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}
  """
  completed = False
  while not completed:
    time.sleep(20)
    response = urlopen(request)
    data = json.loads(response.read().decode())
    completed = (data["status"]=="completed")
  return completed


def check_ec2(url, request, myid):
  """ Check if all previous workflow runs started and stopped ec2 instances
  API endpoint: api.github.com/repos/{owner}/{repo}/actions/runs
  """
  response = urlopen(request)
  data = json.loads(response.read().decode())["workflow_runs"]
  tformat="%Y-%m-%dT%H:%M:%SZ"
  mytime = datetime.strptime(next(x["created_at"] for x in data if x["id"]==myid), tformat)

  workflows = {}
  in_progress = []
  for x in data:
    oldtime = datetime.strptime(x["created_at"], tformat)
    dt = mytime - oldtime
    if x["name"] == "Helpers" and dt >= timedelta():
      token = os.environ["AUTH"]
      request = Request(url+"/"+str(x["id"])+"/jobs")
      request.add_header("Authorization", "token %s" % token)
      workflows[x["id"]] = urlopen(request)
      in_progress.append(x["id"])

  while True: 
    time.sleep(1)
    done = []
    for cid, response in workflows.items():
      print(in_progress)
      print("cid:", cid)
      data = json.loads(response.read().decode())["jobs"]
      start_status = next(x["status"] for x in data if x["name"]=="Start runners")
      stop_status = next(x["status"] for x in data if x["name"]=="Stop runners")
      if start_status == "completed" and stop_status == "completed":
        in_progress.remove(cid)
        done.append(cid)
    if len(in_progress) == 0:
      break
    else:
      [workflows.pop(k) for k in done]

  return True

    
def main():
  url = sys.stdin.read()
  token = os.environ["AUTH"]
  request = Request(url)
  request.add_header("Authorization", "token %s" % token)

  if sys.argv[1] == "build_check":
    if check_build(request):
      print("success")
    else:
      print("failure")
  elif sys.argv[1] == "ec2_check":
    myid = int(sys.argv[2])
    if check_ec2(url, request, myid):
      print("success")
    else:
      print("failure")
  elif sys.argv[1] == "test_check":
    if check_test(request):
      print("success")
    else:
      print("failure")


if __name__ == "__main__": main()
