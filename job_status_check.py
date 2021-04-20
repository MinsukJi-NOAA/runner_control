#!/usr/bin/env python3

import os, re, sys, json, time
from urllib.request import urlopen, Request
from datetime import datetime, timedelta

def check_build(request, no_builds):
  """ Check if all build jobs are completed successfully
  API endpoint: api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs
  """
  all_completed = False
  while not all_completed:
    time.sleep(20)
    response = urlopen(request)
    data = json.loads(response.read().decode())["jobs"]
    ids = [x["id"] for x in data if re.search("Build", x["name"])]
    if len(ids) != no_builds:
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
    if x["name"] == "Helpers" and dt >= timedelta() and x["id"] != myid:
      token = os.environ["AUTH"]
      request = Request(url+"/"+str(x["id"])+"/jobs")
      request.add_header("Authorization", "token %s" % token)
      workflows[x["id"]] = request
      in_progress.append(x["id"])

  while True: 
    if len(in_progress) == 0:
      break
    time.sleep(20)
    done = []
    for cid in reversed(in_progress):
      data = json.loads(urlopen(workflows[cid]).read().decode())["jobs"]
      start_status = next((x["status"] for x in data if x["name"]=="Start runners"), "not found")
      stop_status = next((x["status"] for x in data if x["name"]=="Stop runners"), "not found")
      if start_status == "not found" or stop_status == "not found":
        break
      if start_status == "completed" and stop_status == "completed":
        done.append(cid)
    if len(done) != 0:
      [workflows.pop(k) for k in done]
      [in_progress.remove(k) for k in done]

  return True

    
def main():
  url = sys.stdin.read()
  token = os.environ["AUTH"]
  request = Request(url)
  request.add_header("Authorization", "token %s" % token)

  if sys.argv[1] == "build_check":
    no_builds = int(sys.argv[2])
    if check_build(request, no_builds):
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
