#!/usr/bin/env python3
"""Audit pédagogique V2 de Python Submit : réponses, contournements, cas limites.

Ne touche jamais Supabase ni aux données réelles. Un contournement accepté
est un RISQUE dans le rapport, pas une réussite pédagogique.
"""
from __future__ import annotations

import ast
import collections
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from virtual_student import SOLUTIONS, catalogue, check, execute
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pedagogical_checks import REQUIREMENTS, validate_code

REPORT = Path(__file__).with_name("rapport-pedagogique.md")
DATA = Path(__file__).with_name("rapport-pedagogique.json")

# Exemples indépendants des tests actuellement affichés dans l'application.
BOUNDARIES = {
    "tp1q3": [(["100", "0.5"], "Tension U = 50.0 V"),
              (["25", "0.4"], "Tension U = 10.0 V")],
    "tp2q1": [(["2.0"], "LED éteinte"), (["2.01"], "LED allumée"),
              (["-1"], "LED éteinte")],
    "tp2q2": [(["4.49"], "Tension faible"), (["4.5"], "Tension nominale"),
              (["5.5"], "Tension nominale"), (["5.51"], "Tension élevée")],
    "tp2q5": [(["17.99"], "Chauffage allumé"), (["18"], "Maintien"),
              (["22"], "Maintien"), (["22.01"], "Chauffage coupé")],
}
FILES = {
    "tp8q1": ("mesures.txt", "5.0\n5.1\n4.9\n"),
    "tp8q2": ("mesures.txt", "5.0\n5.1\n4.9\n"),
    "tp8q3": ("mesures.txt", "4.8\n5.2\n5.0\n"),
    "tp8q4": ("mesures.csv", "temps,tension\n0,5.0\n1,5.1\n2,4.9\n"),
    "tp8q5": ("mesures.csv", "temps,tension\n0,5.0\n1,6.4\n2,5.2\n"),
    "tp10q4": ("diagnostic.txt", "Tension: 1 alerte\nTemperature: 1 alerte\n"),
}
OTHER_METHODS = {
    "tp1q1": "R,I=470,0.02\nprint('Tension U = {} V'.format(R*I))",
    "tp1q2": "valeurs=(470,0.02,'Résistance')\nfor v in valeurs: print(type(v))",
    "tp1q3": "R,I=map(float,(input(),input()))\nprint('Tension U =',I*R,'V')",
    "tp1q4": "U=470*0.02\nP=U*0.02\nprint('Puissance P =',round(P,4),'watts')",
    "tp1q5": "R,I=470,0.02\nU=R*I\nP=round(R*I**2,3)\nprint(f'R = {R} Ω | I = {I} A | U = {U} V | P = {P} W')",
    "tp2q1": "v=float(input())\nprint(['LED éteinte','LED allumée'][v>2])",
    "tp2q2": "v=float(input())\nprint('Tension faible' if v<4.5 else 'Tension élevée' if v>5.5 else 'Tension nominale')",
    "tp2q3": "for U,I in [(15,3),(10,3),(15,1)]:\n print(f'U={U} I={I} : Système '+('déclenché' if U>12 and I>2 else 'non déclenché'))",
    "tp2q4": "for A in range(2):\n for B in range(2):\n  print(f'A={A} B={B} : {int(bool(A)*bool(B))}')",
    "tp2q5": "v=float(input())\nprint('Chauffage coupé' if v>22 else 'Chauffage allumé' if v<18 else 'Maintien')",
    "tp3q1": "c=20000\nfor j in range(20):\n c=round(c*1.06)\n print(f'Année {j+1} : {c} €')",
    "tp3q2": "U,n=100,0\nwhile not U<1:\n U/=2\n n+=1\nprint(n)",
    "tp3q3": "s=0\nfor k in range(1,201): s+=k\nprint(s)\nn=200\nprint(n*(n+1)//2)",
    "tp3q4": "import random\nn=0\nwhile True:\n a=random.randint(1,6)\n b=random.randint(1,6)\n n+=1\n if a==b: break\nprint(n)",
    "tp3q5": "for i in range(1,6):\n print(''.join([f'{i*j:>4d}' for j in range(1,6)]))",
}
NEEDED = {
    "tp1q1":["multiplication"],"tp1q2":["type()"],"tp1q3":["input()"],
    "tp1q4":["calcul"],"tp1q5":["f-string"],"tp2q1":["comparaison"],
    "tp2q2":["condition"],"tp2q3":["and"],"tp2q4":["boucles imbriquées"],
    "tp2q5":["condition"],"tp3q1":["for"],"tp3q2":["while"],
    "tp3q3":["for"],"tp3q4":["random et while"],"tp3q5":["for imbriqués"],
    "tp4q1":["fonction"],"tp4q2":["fonction"],"tp4q3":["fonction"],
    "tp4q4":["fonction"],"tp4q5":["fonction"],
    "tp6q1":["split"],"tp6q2":["split"],"tp6q3":["split"],
    "tp6q4":["f-string"],"tp6q5":["split"],
    "tp8q1":["écriture fichier"],"tp8q2":["lecture fichier"],
    "tp8q3":["lecture fichier"],"tp8q4":["écriture fichier"],
    "tp8q5":["lecture fichier"],"tp10q2":["fonction"],
    "tp10q4":["écriture fichier"],
}

def accepted(ex, program):
    # Même logique que la plateforme : AST, sorties et fichiers.
    # Exécution dans un espace temporaire distinct à chaque test.
    if not validate_code(ex["id"], program)["ok"]:
        return False
    for t in ex["tests"]:
        output=execute(program,t.get("inputs",[]),t.get("dice"))
        if not check(program,t,output):
            return False
        if t.get("file"):
            expected=t["file"]
            result=check_file(program,expected["path"])
            if not result["exists"] or result["content"].replace("\\r\\n","\\n").rstrip()!=expected["content"].replace("\\r\\n","\\n").rstrip():
                return False
    return True

def syntax_variant(program):
    """Changement de syntaxe inoffensif, plutôt que simple ajout de commentaire."""
    tree=ast.parse(program)
    class Rewrite(ast.NodeTransformer):
        changed=False
        def visit_Constant(self,node):
            if not self.changed and type(node.value) in (int,float):
                self.changed=True
                return ast.copy_location(
                    ast.BinOp(left=node,op=ast.Add(),right=ast.Constant(value=0)),
                    node)
            return node
    Rewrite().visit(tree)
    return ast.unparse(ast.fix_missing_locations(tree))

def hardcoded(ex):
    tc=ex["tests"][0]
    if "expected" in tc:
        answer=tc["expected"]
    elif ex["id"]=="tp3q1":
        answer="Année 1 : 21200 €\n"+"\n".join(
            f"Année {j} : 0 €" for j in range(2,21))
    else:
        answer="1"
    # Le pseudo-code demandé apparaît seulement comme commentaire.
    required=" ".join(tc.get("requires",[]))
    return ("# "+required+"\n" if required else "")+"print("+repr(answer)+")"

def check_file(program, filename):
    worker=r'''
import contextlib,io,json,pathlib,sys
data=json.load(sys.stdin)
out=io.StringIO()
with contextlib.redirect_stdout(out):
 try: exec(data["program"],{"__name__":"__main__"})
 except Exception as e: print(type(e).__name__+": "+str(e))
path=pathlib.Path(data["filename"])
print(json.dumps({"exists":path.is_file(),"content":path.read_text(encoding="utf-8") if path.is_file() else None,"output":out.getvalue()},ensure_ascii=False))
'''
    with tempfile.TemporaryDirectory(prefix="python-submit-audit-") as directory:
        p=subprocess.run([sys.executable,"-I","-c",worker],
                         input=json.dumps({"program":program,"filename":filename}),
                         capture_output=True,text=True,cwd=directory,timeout=5,check=True)
    return json.loads(p.stdout)

def add(rows,ex,scenario,status,detail):
    rows.append(dict(exercice=ex["id"],tp=ex["tp"],test=scenario,
                     statut=status,details=detail))

def main():
    exercises=catalogue()
    rows=[]
    regressions=[]
    for ex in exercises:
        key=ex["id"]
        solution=SOLUTIONS[key]
        scenarios=[
            ("Solution de référence",solution,True),
            ("Variante syntaxique valide",syntax_variant(solution),True),
            ("Résultat manifestement faux","print('FAUX_AUDIT')",False),
            ("Erreur Python","if :\n pass",False),
        ]
        for title,code,expected in scenarios:
            try:
                real=accepted(ex,code)
                ok=(real==expected)
                add(rows,ex,title,"OK" if ok else "ECHEC",
                    "Comportement attendu" if ok else "Solution correcte refusée ou réponse incorrecte acceptée")
                if not ok: regressions.append(f"{key} — {title}")
            except Exception as err:
                add(rows,ex,title,"ECHEC",str(err))
                regressions.append(f"{key} — {title} — {err}")
        try:
            copied=accepted(ex,hardcoded(ex))
            add(rows,ex,"Réponse codée en dur","RISQUE" if copied else "OK",
                "Résultat sans calcul accepté" if copied else "Contournement rejeté")
        except Exception as err:
            add(rows,ex,"Réponse codée en dur","ECHEC",str(err))
            regressions.append(f"{key} — réponse codée en dur — {err}")
        if key in OTHER_METHODS:
            try:
                good=accepted(ex,OTHER_METHODS[key])
                add(rows,ex,"Autre méthode correcte","OK" if good else "ALERTE",
                    "Méthode différente acceptée" if good else "Méthode valide potentiellement rejetée")
            except Exception as err:
                add(rows,ex,"Autre méthode correcte","ALERTE",str(err))
        for inputs,expected_output in BOUNDARIES.get(key,[]):
            try:
                actual=execute(solution,inputs)
                present=any(t.get("inputs",[])==inputs and t.get("expected")==expected_output
                            for t in ex["tests"])
                state="ECHEC" if actual!=expected_output else "OK" if present else "MANQUE"
                add(rows,ex,"Cas limite : "+str(inputs),state,
                    f"Attendu {expected_output!r}, obtenu {actual!r}; présent dans le site : {present}")
                if actual!=expected_output: regressions.append(f"{key} — limite {inputs}")
            except Exception as err:
                add(rows,ex,"Cas limite : "+str(inputs),"ECHEC",str(err))
                regressions.append(f"{key} — limite {inputs} — {err}")
        if key in FILES:
            filename,content=FILES[key]
            try:
                file=check_file(solution,filename)
                good=file["exists"] and file["content"]==content
                add(rows,ex,"Fichier réellement produit","OK" if good else "ECHEC",
                    filename+" : "+("contenu vérifié" if good else "absent ou incorrect"))
                if not good: regressions.append(f"{key} — fichier erroné")
                only_output=accepted(ex,"print("+repr(ex["tests"][0].get("expected",""))+")")
                add(rows,ex,"Fausse création de fichier","RISQUE" if only_output else "OK",
                    "Affichage accepté sans création de fichier" if only_output else "Absence de fichier détectée")
            except Exception as err:
                add(rows,ex,"Vérification de fichiers","ECHEC",str(err))
                regressions.append(f"{key} — fichier — {err}")
        if key in NEEDED:
            for required in NEEDED[key]:
                ast_checked = key in REQUIREMENTS
                add(rows,ex,"Construction : "+required,
                    "OK" if ast_checked else "MANQUE",
                    "Présence de la construction contrôlée par l'AST" if ast_checked
                    else "Vérification structurelle absente")
    counts=collections.Counter(r["statut"] for r in rows)
    per_tp={}
    for ex in exercises:
        per_tp[ex["tp"]]=collections.Counter(r["statut"] for r in rows if r["tp"]==ex["tp"])
    summary={"exercices":len(exercises),"scenarios":len(rows),
             "compteurs":dict(counts),"regressions":regressions,"lignes":rows}
    DATA.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    report=[
        "# Audit pédagogique avancé — Python Submit",
        "",
        f"**{len(exercises)} exercices ; {len(rows)} scénarios ; {counts['OK']} OK ; "
        f"{counts['RISQUE']} risques confirmés ; {counts['MANQUE']} contrôles manquants ; "
        f"{counts['ALERTE']} variantes à examiner ; {counts['ECHEC']} échecs.**",
        "",
        "Un scénario OK n'est pas la garantie qu'un exercice est fiable. Les",
        "contournements acceptés sont des risques à corriger, pas des réussites.",
        "",
        "Exécution Python isolée ; aucun accès aux comptes élèves ni à Supabase.",
        "",
        "## Résultats par TP",
        "| TP | Scénarios | OK | Risques | Manques | Variantes | Échecs |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for tp in sorted(per_tp,key=lambda x:int(x[2:])):
        c=per_tp[tp]
        report.append(f"| {tp} | {sum(c.values())} | {c['OK']} | {c['RISQUE']} | "
                      f"{c['MANQUE']} | {c['ALERTE']} | {c['ECHEC']} |")
    report+=["","## Anomalies et lacunes détaillées",
             "| Exercice | Statut | Contrôle | Explication |",
             "|---|---|---|---|"]
    for row in rows:
        if row["statut"]!="OK":
            report.append("| "+ " | ".join(str(row[k]).replace("|","/").replace("\n"," ")
                for k in ("exercice","statut","test","details"))+" |")
    report+=["","## Interprétation",
             "- RISQUE : une réponse sans l'algorithme ou le fichier demandé est acceptée.",
             "- MANQUE : la plateforme ne contrôle pas encore la condition ou le cas limite.",
             "- ALERTE : une méthode valide pourrait être refusée ; à examiner pédagogiquement.",
             "- ECHEC : dysfonctionnement du test de référence ou du dispositif.",
             "",
             "Le workflow peut être vert malgré des risques : seules les régressions bloquent la CI."]
    REPORT.write_text("\n".join(report)+"\n",encoding="utf-8")
    print(f"Audit V2 : {len(exercises)} exercices ; {len(rows)} scénarios ; {dict(counts)}")
    print(f"Rapports : {REPORT.name} et {DATA.name}")
    if len(exercises)!=50 or len(rows)<250 or regressions:
        print("RÉGRESSIONS:",*regressions,sep="\n- ")
        sys.exit(1)

if __name__=="__main__":
    main()
