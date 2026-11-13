#!/usr/bin/env python3
"""Élève virtuel — vérification des 50 exercices Python Submit, sans accès au cloud."""
import contextlib
import io
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "exercises.js"
REPORT = ROOT / "tests" / "rapport-exercices.md"

# Programmes de référence indépendants : une solution complète par exercice.
SOLUTIONS = {
    "tp1q1": """R=470
I=0.02
U=R*I
print(f"Tension U = {U} V")""",
    "tp1q2": """R=470
I=0.02
nom="Résistance"
print(type(R))
print(type(I))
print(type(nom))""",
    "tp1q3": """R=float(input())
I=float(input())
print(f"Tension U = {R*I} V")""",
    "tp1q4": """R=470
I=0.02
U=R*I
print(f"Puissance P = {round(U*I,4)} watts")""",
    "tp1q5": """R=470
I=0.02
U=R*I
P=U*I
print(f"R = {R} Ω | I = {I} A | U = {U} V | P = {P} W")""",
    "tp2q1": """U=float(input())
print("LED allumée" if U>2 else "LED éteinte")""",
    "tp2q2": """U=float(input())
if U<4.5: print("Tension faible")
elif U<=5.5: print("Tension nominale")
else: print("Tension élevée")""",
    "tp2q3": """for U,I in [(15,3),(10,3),(15,1)]:
    etat="Système déclenché" if U>12 and I>2 else "Système non déclenché"
    print(f"U={U} I={I} : {etat}")""",
    "tp2q4": """for A in (0,1):
    for B in (0,1):
        print(f"A={A} B={B} : {A and B}")""",
    "tp2q5": """T=float(input())
if T>22: print("Chauffage coupé")
elif T<18: print("Chauffage allumé")
else: print("Maintien")""",
    "tp3q1": """capital=20000
for annee in range(1,21):
    capital=round(capital*1.06)
    print(f"Année {annee} : {capital} €")""",
    "tp3q2": """U=100
n=0
while U>=1:
    U=U/2
    n+=1
print(n)""",
    "tp3q3": """s=0
for k in range(1,201):
    s+=k
print(s)
n=200
print(n*(n+1)//2)""",
    "tp3q4": """import random
n=0
while True:
    de1=random.randint(1,6)
    de2=random.randint(1,6)
    n+=1
    if de1==de2:
        break
print(n)""",
    "tp3q5": """for i in range(1,6):
    print("".join(f"{i*j:>4d}" for j in range(1,6)))""",
    "tp4q1": """def tension(R,I):
    return R*I
print(tension(470,0.02))""",
    "tp4q2": """def puissance(U,I):
    return U*I
print(puissance(12,2.5))""",
    "tp4q3": """def mv_vers_v(mv):
    return mv/1000
print(f"{mv_vers_v(3300)} V")""",
    "tp4q4": """def etat(U):
    if U<4.5: return "faible"
    if U<=5.5: return "nominale"
    return "élevée"
for U in (4.0,5.0,6.0):
    print(etat(U))""",
    "tp4q5": """def bilan(R,I):
    U=R*I
    P=U*I
    return f"U = {U} V | P = {P} W"
print(bilan(470,0.02))""",
    "tp5q1": """mesures=[4.8,5.1,5.0,6.2,4.9,5.2]
print(f"{len(mesures)} mesures")""",
    "tp5q2": """mesures=[4.8,5.1,5.0,6.2,4.9,5.2]
print(f"Min = {min(mesures)} V")
print(f"Max = {max(mesures)} V")""",
    "tp5q3": """mesures=[4.8,5.1,5.0,6.2,4.9,5.2]
print(f"Moyenne = {round(sum(mesures)/len(mesures),2)} V")""",
    "tp5q4": """mesures=[4.8,5.1,5.0,6.2,4.9,5.2]
print(f"{sum(x>5.5 for x in mesures)} dépassement")""",
    "tp5q5": """mesures=[4.8,5.1,5.0,6.2,4.9,5.2]
print(f"Min = {min(mesures)} V")
print(f"Max = {max(mesures)} V")
print(f"Moyenne = {round(sum(mesures)/len(mesures),2)} V")
if any(x>6 for x in mesures): print("ALERTE")""",
    "tp6q1": """trame="TEMP:21.5"
capteur,valeur=trame.split(":")
print(f"Capteur = {capteur}")
print(f"Valeur = {valeur}")""",
    "tp6q2": """trame="U:5.25"
valeur=float(trame.split(":")[1])
print(valeur*2)""",
    "tp6q3": """trame="TEMP=23.4;HUM=48"
mesures=dict(champ.split("=") for champ in trame.split(";"))
print(f"Température = {mesures['TEMP']} °C")
print(f"Humidité = {mesures['HUM']} %")""",
    "tp6q4": """capteur="U"
valeur=5.1
unite="V"
print(f"{capteur};{valeur};{unite}")""",
    "tp6q5": """trame="TEMP:28.5"
temperature=float(trame.split(":")[1])
print("ALERTE TEMP" if temperature>25 else "TEMP OK")""",
    "tp7q1": """valeurs=[5.0,5.1,7.2,4.9,6.8,5.0]
print(f"{sum(v>6 for v in valeurs)} anomalies")""",
    "tp7q2": """valeurs=[18,19,22,27,21]
print("Surchauffe détectée" if any(v>25 for v in valeurs) else "Aucune surchauffe")""",
    "tp7q3": """valeurs=[5.0,5.1,7.2,4.9]
print(f"Indice = {next(i for i,v in enumerate(valeurs) if v>6)}")""",
    "tp7q4": """for U in (3.8,5.0,5.4,6.1):
    print("faible" if U<4.5 else "OK" if U<=5.5 else "élevée")""",
    "tp7q5": """mesures=[5.0,5.2,6.4,6.8,5.1]
n=sum(v>6 for v in mesures)
print(f"Anomalies = {n}")
print("PANNE PROBABLE" if n>=2 else "SURVEILLANCE")""",
    "tp8q1": """with open("mesures.txt","w") as f:
    f.write("5.0\\n5.1\\n4.9\\n")
print("Fichier créé")""",
    "tp8q2": """with open("mesures.txt","w") as f:
    f.write("5.0\\n5.1\\n4.9\\n")
with open("mesures.txt") as f:
    print(f.read(),end="")""",
    "tp8q3": """with open("mesures.txt","w") as f:
    f.write("4.8\\n5.2\\n5.0\\n")
with open("mesures.txt") as f:
    valeurs=[float(x) for x in f]
print(f"Moyenne = {sum(valeurs)/len(valeurs)} V")""",
    "tp8q4": """with open("mesures.csv","w") as f:
    f.write("temps,tension\\n0,5.0\\n1,5.1\\n2,4.9\\n")
print("CSV prêt")""",
    "tp8q5": """with open("mesures.csv","w") as f:
    f.write("temps,tension\\n0,5.0\\n1,6.4\\n2,5.2\\n")
with open("mesures.csv") as f:
    lignes=f.read().splitlines()[1:]
n=sum(float(l.split(",")[1])>6 for l in lignes)
print(f"Alertes = {n}")""",
    "tp9q1": """mesures=[18.2,19.1,20.4,21.0,22.3]
print(f"Min = {min(mesures)}")
print(f"Max = {max(mesures)}")
print(f"Moyenne = {round(sum(mesures)/len(mesures),2)}")""",
    "tp9q2": """consigne=20
for valeur in (18,20,23,19):
    print(valeur-consigne)""",
    "tp9q3": """mesures=[4.9,5.0,5.2,6.0,5.1]
pourcent=100*sum(4.5<=m<=5.5 for m in mesures)/len(mesures)
print(f"{pourcent} %")""",
    "tp9q4": """mesures=[2,4,1,3]
for i,v in enumerate(mesures,1):
    print(f"{i}: {'#'*v}")""",
    "tp9q5": """mesures=[4.8,5.0,5.2,6.3,4.7]
print(f"Mesures = {len(mesures)}")
print(f"Moyenne = {round(sum(mesures)/len(mesures),2)} V")
print(f"Alertes = {sum(x>6 for x in mesures)}")""",
    "tp10q1": """tensions=[5.0,5.1,6.4,4.8,5.2]
temperatures=[21,22,23,29,24]
print(f"{len(tensions)} relevés")""",
    "tp10q2": """def controle_tension(U):
    return "OK" if 4.5<=U<=5.5 else "ALERTE"
for U in (5.0,6.4): print(controle_tension(U))""",
    "tp10q3": """tensions=[5.0,5.1,6.4,4.8,5.2]
temperatures=[21,22,23,29,24]
print(f"Alertes tension = {sum(not 4.5<=U<=5.5 for U in tensions)}")
print(f"Alertes température = {sum(T>25 for T in temperatures)}")""",
    "tp10q4": """with open("diagnostic.txt","w") as f:
    f.write("Tension: 1 alerte\\nTemperature: 1 alerte\\n")
print("Diagnostic enregistré")""",
    "tp10q5": """alertes=2
print("=== BILAN CIEL ===")
print(f"Alertes = {alertes}")
if alertes: print("État = MAINTENANCE REQUISE")""",
}

# Une exécution isolée dans un processus Python et un répertoire temporaire,
# sans contact réseau ni accès aux données d'élèves.
EXECUTOR = r'''
import builtins, contextlib, io, json, sys
payload=json.load(sys.stdin)
inputs=iter(payload["inputs"])
out=io.StringIO()
def virtual_input(prompt=""):
    print(prompt,end="")
    try: return next(inputs)
    except StopIteration: raise EOFError("Entrée manquante")
error=None
with contextlib.redirect_stdout(out):
    try:
        builtins.input=virtual_input
        exec(compile(payload["code"],"<virtual-student>","exec"),{"__name__":"__main__"})
    except Exception as e:
        # Comportement actuel de la page : une exception Python est imprimée.
        print(type(e).__name__+": "+str(e))
        error=str(e)
print(json.dumps({"output":out.getvalue(),"error":error},ensure_ascii=False))
'''

def controlled_dice_program(source, dice):
    """Exécute du vrai Python avec un tirage de dés déterministe."""
    rolls = repr(list(dice))
    return (
        "import random as _audit_random\n"
        "_audit_original = _audit_random.randint\n"
        f"_audit_rolls = iter({rolls})\n"
        "def _audit_randint(a,b):\n"
        "    if (a,b) != (1,6):\n"
        "        raise ValueError('Les dés doivent utiliser randint(1,6)')\n"
        "    try:\n"
        "        return next(_audit_rolls)\n"
        "    except StopIteration:\n"
        "        raise RuntimeError('Trop de tirages de dés')\n"
        "_audit_random.randint = _audit_randint\n"
        "try:\n"
        f"    exec({source!r}, {{'__name__':'__main__'}})\n"
        "finally:\n"
        "    _audit_random.randint = _audit_original\n"
    )


def execute(code, inputs, dice=None):
    if dice is not None:
        code = controlled_dice_program(code, dice)
    with tempfile.TemporaryDirectory(prefix="python-submit-agent-") as tmp:
        done = subprocess.run([sys.executable, "-I", "-c", EXECUTOR],
                              input=json.dumps({"code":code,"inputs":inputs}),
                              capture_output=True, text=True, cwd=tmp, timeout=5)
    if done.returncode:
        raise RuntimeError(done.stderr or "Le programme Python n'a pas démarré")
    return json.loads(done.stdout)["output"].strip()

def check(code, tc, actual):
    if not all(req in code for req in tc.get("requires", [])):
        return False
    if tc.get("outputRegex"):
        return re.search(tc["outputRegex"],actual) is not None
    return actual == tc.get("expected","").strip()

def catalogue():
    js = r"""
const fs=require('fs'), vm=require('vm');
const sandbox={window:{}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
process.stdout.write(JSON.stringify(sandbox.window.PYTHON_EXERCISES));
"""
    proc=subprocess.run(["node","-e",js,str(CATALOGUE)],capture_output=True,text=True,check=True)
    return json.loads(proc.stdout)

def main():
    exercises=catalogue()
    ids=[e["id"] for e in exercises]
    results=[]
    seen=set()
    for exercise in exercises:
        exid=exercise["id"]
        program=SOLUTIONS.get(exid)
        reasons=[]
        if exid in seen: reasons.append("Identifiant d'exercice dupliqué")
        seen.add(exid)
        if not program:
            reasons.append("Programme de référence manquant")
        if not exercise.get("tests"):
            reasons.append("Aucun test automatique")
        for n,tc in enumerate(exercise.get("tests",[]),1):
            if not program: break
            try:
                actual=execute(textwrap.dedent(program),tc.get("inputs",[]),tc.get("dice"))
                if not check(program,tc,actual):
                    reasons.append(f"test {n}: attendu={tc.get('expected',tc.get('outputRegex'))!r}, obtenu={actual[:100]!r}")
                if check("print('FAUX')",tc,"FAUX"):
                    reasons.append(f"test {n}: une mauvaise réponse serait acceptée")
            except Exception as e:
                reasons.append(f"test {n}: {type(e).__name__}: {e}")
        results.append((exercise,reasons))
        print(f"{'❌' if reasons else '✅'} {exid} — {exercise['title']}")
        for reason in reasons: print(f"    {reason}")

    missing=set(SOLUTIONS)-set(ids)
    if missing:
        print(f"Solutions orphelines: {sorted(missing)}")
    failures=sum(bool(errors) for _,errors in results)
    checks=sum(len(e.get("tests",[])) for e,_ in results)
    report=[
        "# Rapport de l'élève virtuel — Python Submit",
        "",
        f"**Catalogue : {len(exercises)} exercices, {checks} cas de test, {failures} exercices en anomalie.**",
        "",
        "Les réponses de référence sont exécutées en Python isolé ; les mauvaises réponses doivent être refusées.",
        "Les tests de navigateur et Supabase simulé sont réalisés séparément.",
        "",
        "| Exercice | Résultat | Détails |",
        "|---|---|---|"
    ]
    for e,errors in results:
        status="❌ Échec" if errors else "✅ Réussi"
        detail="<escape>" if False else "; ".join(x.replace("|","/").replace("\n"," ") for x in errors) or "Conforme"
        report.append(f"| {e['id']} | {status} | {detail} |")
    REPORT.write_text("\n".join(report)+"\n",encoding="utf-8")
    print(f"\nRésumé : {len(exercises)-failures}/{len(exercises)} exercices réussis ; rapport : {REPORT}")
    if len(exercises)!=50 or missing or failures:
        sys.exit(1)

if __name__=="__main__":
    main()
