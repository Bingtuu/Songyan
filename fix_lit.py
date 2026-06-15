path = r"c:\vIbe Project\Songyan\src\songyan\workflows\_nodes.py"
content = open(path, encoding="utf-8").read()
old = "    if has_critical_literary:\n        return_state[\"_needs_revision\"] = True\n    return return_state"
new = "    return_state[\"_needs_revision\"] = has_critical_literary\n    return return_state"
if old in content:
    content = content.replace(old, new)
    open(path, "w", encoding="utf-8").write(content)
    print("Fixed")
else:
    print("Not found")
