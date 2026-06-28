import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from storage.database import execute_query, execute_write
from utils.config import DATA_DIR

rows = execute_query("SELECT id, name, avatar FROM contacts WHERE avatar IS NOT NULL AND avatar != ''")
for r in rows:
    cid, name, old = r[0], r[1], r[2]
    filename = os.path.basename(old)
    correct = os.path.join(DATA_DIR, 'avatars', filename)
    if os.path.exists(correct):
        execute_write('UPDATE contacts SET avatar = ? WHERE id = ?', (correct, cid))
        print(f'Fixed: {name} -> {correct}')
    else:
        print(f'NOT FOUND: {correct}')
print('Done')
