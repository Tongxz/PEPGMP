import time

import requests

BASE_URL = "http://localhost:8000/api/v1/mlops"


def test_deployments_list():
    print("Testing GET /deployments...")
    try:
        resp = requests.get(f"{BASE_URL}/deployments")
        resp.raise_for_status()
        deployments = resp.json()
        print(f"Success. Found {len(deployments)} deployments.")
        for d in deployments:
            print(f" - {d.get('name')} ({d.get('status')})")
    except Exception as e:
        print(f"Failed to list deployments: {e}")
        # Don't fail the whole script, continue to workflow test


def test_workflow_execution():
    print("\nTesting Workflow Execution (Model Deployment Step)...")

    # 1. Create Workflow
    workflow_payload = {
        "name": "Test Deployment Workflow (Auto-generated)",
        "type": "model_deployment",
        "description": "Created by verification script to test model deployment step",
        "trigger": "manual",
        "steps": [
            {
                "name": "Deploy Dummy Model",
                "type": "model_deployment",
                "config": {
                    "model_id": "dummy_model_001",
                    "model_path": "models/dummy.pt",
                    "detection_task": "hairnet_detection",
                    "apply_immediately": False,
                },
            },
            {
                "name": "Notify Admin",
                "type": "notification",
                "config": {"message": "Deployment test completed"},
            },
        ],
    }

    try:
        print("Creating workflow...")
        resp = requests.post(f"{BASE_URL}/workflows", json=workflow_payload)
        resp.raise_for_status()
        workflow_data = resp.json()
        workflow_id = workflow_data["workflow_id"]
        print(f"Workflow created: {workflow_id}")

        # 2. Run Workflow
        print(f"Running workflow {workflow_id}...")
        resp = requests.post(f"{BASE_URL}/workflows/{workflow_id}/run")
        resp.raise_for_status()
        run_data = resp.json()
        run_id = run_data["run_id"]
        print(f"Run started: {run_id}")

        # 3. Poll for status
        print("Polling for status...")
        for i in range(10):
            time.sleep(1)
            resp = requests.get(f"{BASE_URL}/workflows/{workflow_id}/runs/{run_id}")
            if resp.status_code == 200:
                status_data = resp.json()
                status = status_data["status"]
                print(f"Status: {status}")
                if status in ["success", "completed", "failed", "cancelled"]:
                    if status in ["success", "completed"]:
                        print("Workflow execution successful!")

                        # Check step outputs
                        steps = status_data.get("step_outputs", [])
                        for step in steps:
                            print(
                                f"  Step: {step.get('name')} -> Output: {step.get('output')}"
                            )
                    else:
                        print(
                            f"Workflow execution failed: {status_data.get('error_message')}"
                        )
                        print(f"Logs: {status_data.get('run_log')}")
                    break
            else:
                print(f"Failed to get run status: {resp.status_code}")

    except Exception as e:
        print(f"Workflow test failed: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")


if __name__ == "__main__":
    test_deployments_list()
    test_workflow_execution()
