"""Generate a token locally. This script never writes credentials to source files."""
import argparse
import hashlib
import json
import secrets
parser=argparse.ArgumentParser(description='Create one optional local team user')
parser.add_argument('name')
parser.add_argument('--role',choices=['viewer','operator','approver','admin'],default='viewer')
args=parser.parse_args()
token=secrets.token_urlsafe(32)
print('API token (copy to the user once):\n'+token)
print('\nAdd this entry to TEAM_USERS_JSON in backend/.env:')
print(json.dumps({'name':args.name,'role':args.role,'token_sha256':hashlib.sha256(token.encode()).hexdigest()}))
