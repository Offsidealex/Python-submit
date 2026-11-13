"""Règles pédagogiques AST de Python Submit.

Analyse de syntaxe sans exécuter le code élève : les commentaires, messages
et chaînes de caractères ne peuvent plus satisfaire une consigne technique.

La correction des résultats reste assurée par les tests d'exécution. Ce
fichier ne décide jamais seul de la réussite d'un exercice.
"""

import ast


# Les règles sont limitées aux constructions explicitement demandées.
# Elles ne prescrivent ni les noms des variables ni une présentation unique.
REQUIREMENTS = {
    "tp1q1": ("multiplication",),
    "tp1q2": ("call:type",),
    "tp1q3": ("call:input", "multiplication"),
    "tp1q4": ("multiplication",),
    "tp1q5": ("fstring",),
    "tp2q1": ("call:input", "conditional"),
    "tp2q2": ("call:input", "conditional"),
    "tp2q3": ("and",),
    "tp2q4": ("nested_for",),
    "tp2q5": ("call:input", "conditional"),
    "tp3q1": ("for",),
    "tp3q2": ("while",),
    "tp3q3": ("for",),
    "tp3q4": ("dice",),
    "tp3q5": ("nested_for",),
    "tp4q1": ("function:tension",),
    "tp4q2": ("function:puissance",),
    "tp4q3": ("function:mv_vers_v",),
    "tp4q4": ("function:etat",),
    "tp4q5": ("function:bilan",),
    "tp6q1": ("method:split",),
    "tp6q2": ("method:split",),
    "tp6q3": ("method:split",),
    "tp6q4": ("fstring",),
    "tp6q5": ("method:split",),
    "tp8q1": ("file_write",),
    "tp8q2": ("file_read",),
    "tp8q3": ("file_read",),
    "tp8q4": ("file_write",),
    "tp8q5": ("file_read",),
    "tp10q2": ("function:controle_tension",),
    "tp10q4": ("file_write",),
}

MESSAGES = {
    "multiplication": "Effectue réellement le calcul avec une multiplication (*).",
    "fstring": "Utilise une f-string Python, comme demandé dans l'énoncé.",
    "conditional": "Utilise une condition if/elif/else ou une expression conditionnelle.",
    "and": "Utilise l'opérateur logique « and » pour tester les deux conditions.",
    "nested_for": "Utilise deux boucles « for » imbriquées.",
    "for": "Utilise une boucle « for ».",
    "while": "Utilise une boucle « while ».",
    "dice": "Simule des paires de dés avec random.randint(1, 6) dans une boucle while, et teste l'égalité des dés.",
    "file_write": "Écris les données dans le fichier demandé.",
    "file_read": "Relis le fichier pour en exploiter les données.",
}


def _call_name(call):
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _nested_for(tree):
    return any(
        isinstance(node, (ast.For, ast.AsyncFor))
        and any(isinstance(desc, (ast.For, ast.AsyncFor))
                for child in node.body for desc in ast.walk(child))
        for node in ast.walk(tree)
    )


def _dice_loop(tree):
    """Accepte random.randint(...) et « from random import randint ».

    Les appels doivent être à l'intérieur du while, la condition d'arrêt
    doit comparer deux valeurs. Les cas aléatoires sont contrôlés ensuite
    par des tests déterministes, et non par cette analyse seule.
    """
    direct_import = any(
        isinstance(node, ast.ImportFrom) and node.module == "random"
        and any(alias.name == "randint" for alias in node.names)
        for node in ast.walk(tree)
    )
    module_names = {"random"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name == "random":
                    module_names.add(item.asname or item.name)

    def randint_call(node):
        if not isinstance(node, ast.Call):
            return False
        f = node.func
        valid = (isinstance(f, ast.Attribute) and f.attr == "randint"
                 and isinstance(f.value, ast.Name) and f.value.id in module_names)
        valid |= (isinstance(f, ast.Name) and f.id == "randint" and direct_import)
        if not valid or len(node.args) < 2:
            return False
        return all(isinstance(arg, ast.Constant) and arg.value == val
                   for arg, val in zip(node.args[:2], (1, 6)))

    for loop in ast.walk(tree):
        if not isinstance(loop, ast.While):
            continue
        inside = [desc for item in loop.body for desc in ast.walk(item)]
        dice = sum(randint_call(n) for n in inside)
        comparisons = [loop.test, *inside]
        equality = any(
            isinstance(node, ast.Compare)
            and any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops)
            for item in comparisons for node in ast.walk(item)
        )
        if dice >= 2 and equality:
            return True
    return False


def _file_calls(tree, action):
    methods = {"file_write": {"write", "writelines", "to_csv"},
               "file_read": {"read", "readline", "readlines", "read_text"}}
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    if any(_call_name(n) in methods[action] for n in calls):
        return True
    # « for ligne in fichier » et « [float(x) for x in f] » sont des
    # méthodes idiomatiques de lecture, sans appel .read().
    if action == "file_read":
        opens = any(_call_name(n) == "open" for n in calls)
        iterations = any(isinstance(n, (ast.For, ast.comprehension))
                         for n in ast.walk(tree))
        return opens and iterations
    return False


def _meets(tree, rule):
    nodes = list(ast.walk(tree))
    if rule == "multiplication":
        return any(isinstance(n, (ast.Mult, ast.MatMult)) for n in nodes)
    if rule == "fstring":
        return any(isinstance(n, ast.JoinedStr) for n in nodes)
    if rule == "conditional":
        return any(isinstance(n, (ast.If, ast.IfExp)) for n in nodes)
    if rule == "and":
        return any(isinstance(n, ast.BoolOp) and isinstance(n.op, ast.And)
                   for n in nodes)
    if rule == "for":
        return any(isinstance(n, ast.For) for n in nodes)
    if rule == "while":
        return any(isinstance(n, ast.While) for n in nodes)
    if rule == "nested_for":
        return _nested_for(tree)
    if rule == "dice":
        return _dice_loop(tree)
    if rule in ("file_write", "file_read"):
        return _file_calls(tree, rule)
    if rule.startswith("call:"):
        name = rule.split(":", 1)[1]
        return any(isinstance(n, ast.Call) and _call_name(n) == name for n in nodes)
    if rule.startswith("method:"):
        name = rule.split(":", 1)[1]
        return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr == name for n in nodes)
    if rule.startswith("function:"):
        name = rule.split(":", 1)[1]
        return any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name == name for n in nodes)
    raise ValueError("Règle inconnue : " + rule)


def validate_code(exercise_id, source):
    """Renvoie un diagnostic lisible, sans exécuter le code ni toucher au cloud."""
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return {"ok": False, "message": "Erreur de syntaxe Python : " + str(error.msg)}
    except Exception:
        return {"ok": False, "message": "Le programme ne peut pas être analysé."}
    missing = []
    for rule in REQUIREMENTS.get(exercise_id, ()):
        if not _meets(tree, rule):
            if rule.startswith("call:"):
                msg = "Utilise la fonction " + rule.split(":", 1)[1] + "(), comme demandé."
            elif rule.startswith("function:"):
                msg = "Définis une fonction " + rule.split(":", 1)[1] + "(), comme demandé."
            elif rule.startswith("method:"):
                msg = "Utilise la méthode " + rule.split(":", 1)[1] + "(), comme demandé."
            else:
                msg = MESSAGES.get(rule, "Respecte la méthode demandée.")
            missing.append(msg)
    return {"ok": not missing, "message": " ".join(missing)}


if __name__ == "__main__":
    import json
    import sys
    item = json.load(sys.stdin)
    print(json.dumps(validate_code(item["exercise_id"], item["source"]),
                     ensure_ascii=False))
