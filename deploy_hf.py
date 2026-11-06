import os
import sys
from huggingface_hub import HfApi, login

def deploy(token: str):
    print("1. Logging into Hugging Face...")
    login(token=token, add_to_git_credential=True)
    
    api = HfApi(token=token)
    user_info = api.whoami()
    username = user_info["name"]
    print(f"✓ Authenticated as: {username}")
    
    repo_id = f"{username}/gopush"
    print(f"2. Creating/Verifying Space '{repo_id}' (Docker SDK)...")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
    )
    print("✓ Space created successfully!")
    
    source_folder = os.path.dirname(os.path.abspath(__file__))
    print(f"3. Uploading GoPush server files from {source_folder}...")
    api.upload_folder(
        repo_id=repo_id,
        repo_type="space",
        folder_path=source_folder,
        ignore_patterns=["dev_server.py", "test_client.py", "push_to_github.py", "deploy_hf.py", ".git*"],
    )
    print("✓ All files uploaded!")
    
    # Hugging Face direct public URL format
    # Example: username-gopush.hf.space
    clean_user = username.replace("_", "-").lower()
    live_url = f"https://{clean_user}-gopush.hf.space"
    ws_url = f"wss://{clean_user}-gopush.hf.space/ws"
    
    print("\n" + "="*50)
    print("🚀 SUCCESS! GoPush is deploying on Hugging Face 24/7!")
    print(f"Dashboard: https://huggingface.co/spaces/{repo_id}")
    print(f"Live Web URL: {live_url}")
    print(f"WebSocket URL: {ws_url}")
    print("="*50)
    return ws_url

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deploy_hf.py <HF_TOKEN>")
        sys.exit(1)
    deploy(sys.argv[1].strip())

