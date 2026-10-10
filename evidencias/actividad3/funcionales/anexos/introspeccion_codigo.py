import json
import urllib.request

QUERY = """
{
  __schema {
    queryType { fields { name } }
    mutationType { fields { name } }
  }
  ca: __type(name: "CreateAccountInput") { inputFields { name } }
  cc: __type(name: "CreateConceptInput") { inputFields { name } }
  ac: __type(name: "AssignConceptToAccountInput") { inputFields { name } }
  ct: __type(name: "CreateTransactionInput") { inputFields { name } }
  lr: __type(name: "LoginInput") { inputFields { name } }
  cr: __type(name: "CreateRoleInput") { inputFields { name } }
  cp: __type(name: "CreatePermissionInput") { inputFields { name } }
  ap: __type(name: "AssignPermissionToRoleInput") { inputFields { name } }
  cu: __type(name: "CreateCompanyUserInput") { inputFields { name } }
  ar: __type(name: "AssignRoleInput") { inputFields { name } }
  lp: __type(name: "LoginPayload") { fields { name } }
}
"""

body = json.dumps({"query": QUERY}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8000/graphql",
    data=body,
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=30) as resp:
    payload = json.loads(resp.read().decode())

data = payload["data"]
print("QUERIES:", sorted(f["name"] for f in data["__schema"]["queryType"]["fields"]))
print("MUTATIONS:", sorted(f["name"] for f in data["__schema"]["mutationType"]["fields"]))
for key in ("ca", "cc", "ac", "ct", "lr", "cr", "cp", "ap", "cu", "ar", "lp"):
    nodo = data[key]
    nombre = nodo.get("__typename") or key
    campos = [f["name"] for f in (nodo.get("inputFields") or nodo.get("fields") or [])]
    print("%s: %s" % (key, campos))
