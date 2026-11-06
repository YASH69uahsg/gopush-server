import os
import shutil
import stat
import subprocess
import tempfile

def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

source = r"c:\Users\yashb\Desktop\SubwayRunner\services\gopush"
temp_dir = os.path.join(tempfile.gettempdir(), "gopush_deploy_hf")

if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir, onerror=remove_readonly)
os.makedirs(temp_dir)

# Copy files
for item in os.listdir(source):
    s = os.path.join(source, item)
    d = os.path.join(temp_dir, item)
    if os.path.isdir(s):
        shutil.copytree(s, d)
    else:
        shutil.copy2(s, d)

print("Files copied to:", temp_dir)

def run(cmd):
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr)
    if res.returncode != 0:
        raise Exception(f"Failed: {cmd}")

run(["git", "init", "-b", "main"])
run(["git", "config", "user.name", "YASH69uahsg"])
run(["git", "config", "user.email", "221310862+YASH69uahsg@users.noreply.github.com"])
run(["git", "add", "."])
run(["git", "commit", "-m", "feat: optimize for 24/7 Hugging Face Docker Space (port 7860, never sleeps)"])
run(["git", "remote", "add", "origin", "https://github.com/YASH69uahsg/gopush-server.git"])
run(["git", "push", "-u", "origin", "main", "--force"])

print("SUCCESSFULLY UPDATED GITHUB REPOSITORY!")
